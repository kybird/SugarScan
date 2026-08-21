// 가짜 세션 필드를 private 으로 유지한다. Dart 는 private 이름의 named
// parameter 를 허용하지 않아 initializing formal 을 쓸 수 없다.
// ignore_for_file: prefer_initializing_formals

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/local/tables.dart';
import 'package:sugarscan/data/remote/auth_repository.dart';
import 'package:sugarscan/data/repositories/glucose_repository.dart';
import 'package:sugarscan/data/sync/outbox_repository.dart';
import 'package:sugarscan/data/sync/reading_api.dart';
import 'package:sugarscan/data/sync/sync_cursor_store.dart';
import 'package:sugarscan/data/sync/sync_engine.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';

/// 세션만 흉내 낸다. 나머지 동작은 실제 [AuthRepository] 그대로다.
class _FakeAuth extends AuthRepository {
  _FakeAuth({String? userId})
      : _userId = userId,
        super(client: null, idTokenProvider: null);

  final String? _userId;

  @override
  String? get currentUserId => _userId;

  @override
  bool get canSignIn => true;
}

/// 메모리 상의 서버. 무엇이 어떤 순서로 오갔는지 기록한다.
class _FakeApi implements ReadingApi {
  final List<GlucoseReading> rows = [];
  final List<String> calls = [];
  final List<DateTime?> fetchedSince = [];
  final List<List<String>> upsertedIds = [];

  Object? failUpsert;
  Object? failFetch;

  @override
  Future<void> upsert(List<GlucoseReading> readings, String userId) async {
    calls.add('upsert');
    if (failUpsert != null) throw failUpsert!;

    upsertedIds.add([for (final r in readings) r.id]);
    for (final reading in readings) {
      rows.removeWhere((r) => r.id == reading.id);
      rows.add(reading);
    }
  }

  @override
  Future<List<GlucoseReading>> fetchUpdatedSince(
    DateTime? since, {
    required int limit,
    required int offset,
  }) async {
    calls.add('fetch');
    if (failFetch != null) throw failFetch!;

    fetchedSince.add(since);
    final matching = rows
        .where((r) => since == null || !r.updatedAt.isBefore(since))
        .toList()
      ..sort((a, b) {
        final byTime = a.updatedAt.compareTo(b.updatedAt);
        return byTime != 0 ? byTime : a.id.compareTo(b.id);
      });

    if (offset >= matching.length) return [];
    return matching.skip(offset).take(limit).toList();
  }
}

GlucoseReading _serverReading({
  required String id,
  double enteredValue = 200,
  required DateTime updatedAt,
  DateTime? deletedAt,
  String? note,
}) {
  return GlucoseReading(
    id: id,
    measuredAtUtc: DateTime.utc(2026, 3, 14, 1, 30),
    tzName: 'Asia/Seoul',
    utcOffsetMinutes: 540,
    valueMgdl: enteredValue,
    enteredUnit: GlucoseUnit.mgdl,
    enteredValue: enteredValue,
    tag: MeasurementTag.postMeal,
    source: ReadingSource.manual,
    createdAt: DateTime.utc(2026, 3, 14, 1, 31),
    updatedAt: updatedAt,
    deletedAt: deletedAt,
    note: note,
  );
}

void main() {
  late AppDatabase db;
  late GlucoseRepository readings;
  late OutboxRepository outbox;
  late SyncCursorStore cursor;
  late _FakeApi api;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    readings = GlucoseRepository(
      database: db,
      resolveTzName: () async => 'Asia/Seoul',
      // 시계를 고정한다. 실제 시각을 쓰면 로컬 기록의 updatedAt 이 테스트가
      // 정한 서버 시각보다 늘 미래라, 커서가 서버 변경을 통째로 걸러 낸다.
      clock: () => DateTime.utc(2026, 3, 14, 1, 31),
    );
    outbox = OutboxRepository(database: db);
    cursor = SyncCursorStore(database: db);
    api = _FakeApi();
  });

  tearDown(() => db.close());

  SyncEngine engine({
    String? userId = 'user-1',
    Future<bool> Function()? isOnline,
    int batchSize = 200,
    int maxAttempts = 6,
  }) {
    return SyncEngine(
      database: db,
      api: api,
      auth: _FakeAuth(userId: userId),
      cursor: cursor,
      outbox: outbox,
      isOnline: isOnline,
      batchSize: batchSize,
      maxAttempts: maxAttempts,
    );
  }

  Future<GlucoseReading> addLocal({
    double value = 137,
    String? ocrRawText,
  }) {
    return readings.add(
      value: value,
      unit: GlucoseUnit.mgdl,
      tag: MeasurementTag.fasting,
      source: ReadingSource.ocr,
      ocrRawText: ocrRawText,
    );
  }

  Future<int> outboxCount() async {
    final rows = await db.select(db.syncOutboxRows).get();
    return rows.length;
  }

  Future<GlucoseReadingRow> localRow(String id) {
    return (db.select(db.glucoseReadingRows)..where((t) => t.id.equals(id)))
        .getSingle();
  }

  group('보내기', () {
    test('쌓인 기록을 올리고 큐를 비운다', () async {
      final reading = await addLocal();

      final report = await engine().syncOnce();

      expect(report.outcome, SyncOutcome.ok);
      expect(report.pushed, 1);
      expect(api.rows.single.id, reading.id);
      expect(await outboxCount(), 0);
      expect((await localRow(reading.id)).syncState, SyncState.synced);
    });

    test('같은 기록을 세 번 고쳐도 한 번만 올라간다', () async {
      final reading = await addLocal();
      await readings.update(reading.id, value: 150, unit: GlucoseUnit.mgdl);
      await readings.update(reading.id, value: 160, unit: GlucoseUnit.mgdl);

      // 아웃박스에는 세 줄이 쌓였다.
      expect(await outboxCount(), 3);

      final report = await engine().syncOnce();

      // 서버로 가는 것은 현재 상태 하나뿐이다. 중간 단계를 재생할 이유가 없다.
      expect(report.pushed, 1);
      expect(api.upsertedIds.single, [reading.id]);
      expect(api.rows.single.enteredValue, 160);
      expect(await outboxCount(), 0);
    });

    // 오프라인으로 쌓였다가 나중에 한꺼번에 올라가도 측정 시각은 그대로여야
    // 한다. 여기가 밀리면 기록이 엉뚱한 날짜와 구간에 가서 붙는다.
    test('밀렸다 올라가도 측정 시각이 바뀌지 않는다', () async {
      // 실제 저장 경로처럼 로컬 시각을 넘긴다. 저장소가 이 값에서 UTC 오프셋을
      // 뽑아 쓰므로, UTC DateTime 을 넘기면 오프셋이 0 으로 잡혀 상황이 달라진다.
      final measured = DateTime(2026, 3, 10, 22, 15);
      final reading = await readings.add(
        value: 137,
        unit: GlucoseUnit.mgdl,
        tag: MeasurementTag.bedtime,
        source: ReadingSource.manual,
        measuredAt: measured,
      );
      final wallClockHour =
          (await readings.byId(reading.id))!.measuredAtLocalWallClock.hour;

      // 한동안 오프라인. 그동안 아무것도 못 보낸다.
      await engine(isOnline: () async => false).syncOnce();
      expect(api.rows, isEmpty);

      // 네트워크 복구.
      await engine().syncOnce();

      expect(api.rows.single.id, reading.id);
      expect(api.rows.single.measuredAtUtc, measured.toUtc());
      // 사용자가 그때 시계에서 본 시각이 그대로여야 한다. 여기가 밀리면
      // 기록이 엉뚱한 날짜와 구간에 가서 붙는다.
      expect(api.rows.single.measuredAtLocalWallClock.hour, wallClockHour);
      expect(wallClockHour, 22);
    });

    test('수정해도 측정 시각은 그대로다', () async {
      final measured = DateTime(2026, 3, 10, 22, 15);
      final reading = await readings.add(
        value: 137,
        unit: GlucoseUnit.mgdl,
        tag: MeasurementTag.bedtime,
        source: ReadingSource.manual,
        measuredAt: measured,
      );
      await engine().syncOnce();

      await readings.update(reading.id, value: 150, unit: GlucoseUnit.mgdl);
      await engine().syncOnce();

      expect(api.rows.single.enteredValue, 150);
      expect(api.rows.single.measuredAtUtc, measured.toUtc());
    });

    test('소프트 삭제도 deleted_at 이 채워진 채로 올라간다', () async {
      final reading = await addLocal();
      await engine().syncOnce();
      await readings.delete(reading.id);

      await engine().syncOnce();

      expect(api.rows.single.deletedAt, isNotNull);
    });

    test('기록이 사라진 고아 큐 항목은 치운다', () async {
      final reading = await addLocal();
      await (db.delete(db.glucoseReadingRows)
            ..where((t) => t.id.equals(reading.id)))
          .go();

      final report = await engine().syncOnce();

      // 보낼 것이 없다. 그냥 두면 매 회차 실패하며 자리만 차지한다.
      expect(report.outcome, SyncOutcome.ok);
      expect(report.pushed, 0);
      expect(await outboxCount(), 0);
    });
  });

  group('실패와 재시도', () {
    test('실패하면 큐를 남기고 시도 횟수만 올린다', () async {
      await addLocal();
      api.failUpsert = StateError('서버 없음');

      final report = await engine().syncOnce();

      expect(report.outcome, SyncOutcome.failed);
      expect(await outboxCount(), 1);

      final row = await db.select(db.syncOutboxRows).getSingle();
      expect(row.attempts, 1);
      expect(row.lastError, contains('서버 없음'));
    });

    // 보낼 것을 버리는 선택지는 없다. 멈추되 남긴다.
    test('한도를 넘기면 더 시도하지 않지만 데이터는 남는다', () async {
      await addLocal();
      api.failUpsert = StateError('서버 없음');

      for (var i = 0; i < 3; i++) {
        await engine(maxAttempts: 3).syncOnce();
      }

      final report = await engine(maxAttempts: 3).syncOnce();

      expect(report.blocked, 1);
      expect(await outboxCount(), 1);
      // 네 번째 회차는 아예 집어오지 않았다.
      expect(api.calls.where((c) => c == 'upsert').length, 3);
    });

    // 되돌리는 경로가 없으면 blocked 는 막다른 길이다 — "다시 시도" 버튼을
    // 달아도 pending() 이 그 항목을 집어오지 않아 아무 일도 일어나지 않는다.
    test('다시 시도하면 막혔던 것이 올라간다', () async {
      await addLocal();
      api.failUpsert = StateError('서버 없음');
      for (var i = 0; i < 3; i++) {
        await engine(maxAttempts: 3).syncOnce();
      }
      expect((await engine(maxAttempts: 3).syncOnce()).blocked, 1);

      api.failUpsert = null;
      await outbox.retryBlocked(maxAttempts: 3);
      final report = await engine(maxAttempts: 3).syncOnce();

      expect(report.pushed, 1);
      expect(report.blocked, 0);
      expect(await outboxCount(), 0);
      expect(api.rows, hasLength(1));
    });

    // 지하철을 여섯 번 타는 것만으로 아웃박스가 영구히 막히면 안 된다.
    test('오프라인은 시도 횟수를 태우지 않는다', () async {
      await addLocal();

      final report = await engine(isOnline: () async => false).syncOnce();

      expect(report.outcome, SyncOutcome.offline);
      expect(api.calls, isEmpty);
      expect((await db.select(db.syncOutboxRows).getSingle()).attempts, 0);
    });

    test('로그인 전에는 큐만 쌓이고 아무것도 보내지 않는다', () async {
      await addLocal();

      final report = await engine(userId: null).syncOnce();

      expect(report.outcome, SyncOutcome.notSignedIn);
      expect(api.calls, isEmpty);
      expect(await outboxCount(), 1);
    });

    test('받기에 실패해도 보낸 사실은 보고한다', () async {
      await addLocal();
      api.failFetch = StateError('끊김');

      final report = await engine().syncOnce();

      expect(report.outcome, SyncOutcome.failed);
      expect(report.pushed, 1);
      expect(await outboxCount(), 0);
    });
  });

  group('받기', () {
    test('서버에만 있는 기록을 가져온다', () async {
      api.rows.add(
        _serverReading(id: 'remote-1', updatedAt: DateTime.utc(2026, 3, 14, 2)),
      );

      final report = await engine().syncOnce();

      expect(report.pulled, 1);
      final row = await localRow('remote-1');
      expect(row.enteredValue, 200);
      expect(row.syncState, SyncState.synced);
    });

    // 서버 updated_at 은 서버 시계, 로컬 updatedAt 은 단말 시계다. 크기 비교로는
    // 못 정한다. 보내지 않은 변경이 있으면 그것이 최신이다.
    test('아직 안 보낸 로컬 변경을 덮지 않는다', () async {
      final reading = await addLocal(value: 137);
      api.rows.add(
        _serverReading(
          id: reading.id,
          enteredValue: 999,
          updatedAt: DateTime.utc(2030),
        ),
      );

      // push 없이 pull 만 도는 상황을 만든다.
      api.failUpsert = StateError('보내기만 실패');
      await engine().syncOnce();

      expect((await localRow(reading.id)).enteredValue, 137);
    });

    // 서버 스키마는 로컬의 부분집합이다. 없는 열은 "지워졌다"가 아니라
    // "서버가 모른다"는 뜻이다.
    test('서버가 모르는 열은 덮어쓰지 않는다', () async {
      final reading = await addLocal(value: 137, ocrRawText: '137 mg/dL');
      await engine().syncOnce();

      // 다른 기기가 값을 고쳐 올린 상황.
      api.rows
        ..clear()
        ..add(
          _serverReading(
            id: reading.id,
            enteredValue: 155,
            updatedAt: DateTime.utc(2026, 3, 15),
          ),
        );

      await engine().syncOnce();

      final row = await localRow(reading.id);
      expect(row.enteredValue, 155, reason: '서버가 아는 값은 갱신된다');
      expect(row.ocrRawText, '137 mg/dL', reason: 'OCR 원문은 이 기기에만 있다');
    });

    test('여러 페이지를 끝까지 받는다', () async {
      for (var i = 0; i < 5; i++) {
        api.rows.add(
          _serverReading(
            id: 'remote-$i',
            updatedAt: DateTime.utc(2026, 3, 14, 2, i),
          ),
        );
      }

      final report = await engine(batchSize: 2).syncOnce();

      expect(report.pulled, 5);
    });
  });

  group('커서', () {
    test('두 번째 회차는 받은 지점부터 요청한다', () async {
      api.rows.add(
        _serverReading(id: 'remote-1', updatedAt: DateTime.utc(2026, 3, 14, 2)),
      );

      await engine().syncOnce();
      await engine().syncOnce();

      expect(api.fetchedSince.first, isNull);
      expect(api.fetchedSince[1], DateTime.utc(2026, 3, 14, 2));
    });

    // 계정이 바뀌었는데 이전 커서를 쓰면 새 사용자의 그 이전 기록을 통째로
    // 건너뛴다.
    test('사용자가 바뀌면 처음부터 다시 받는다', () async {
      api.rows.add(
        _serverReading(id: 'remote-1', updatedAt: DateTime.utc(2026, 3, 14, 2)),
      );

      await engine(userId: 'user-1').syncOnce();
      await engine(userId: 'user-2').syncOnce();

      expect(api.fetchedSince.last, isNull);
    });

    test('로그아웃하면 커서를 버린다', () async {
      await cursor.write('user-1', DateTime.utc(2026, 3, 14, 2));
      await cursor.clear();

      expect(await cursor.read('user-1'), isNull);
    });
  });

  test('보내기가 받기보다 먼저다', () async {
    await addLocal();
    await engine().syncOnce();

    // 반대 순서면 아직 안 보낸 변경 위에 서버의 옛 값이 덮이고, 그 다음 push 가
    // 그 옛 값을 서버로 되돌려 보낸다.
    expect(api.calls, ['upsert', 'fetch']);
  });
}
