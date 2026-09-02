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

  /// 이 id 들은 서버에는 있지만 이 클라이언트가 해석하지 못하는 행이다.
  /// 실제 원인은 보통 버전 차이(모르는 enum wireName)다.
  final Set<String> unreadable = {};

  @override
  Future<ReadingPage> fetchUpdatedSince(
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

    if (offset >= matching.length) return const ReadingPage.empty();
    final page = matching.skip(offset).take(limit).toList();

    // 진짜 서버 구현과 같은 규칙: 못 읽은 행도 돌려준 행 수와 updated_at 에는
    // 반영된다. 그래야 페이지 경계 판정과 커서가 어긋나지 않는다.
    DateTime? newest;
    for (final r in page) {
      if (newest == null || r.updatedAt.isAfter(newest)) newest = r.updatedAt;
    }
    return ReadingPage(
      readings: [for (final r in page) if (!unreadable.contains(r.id)) r],
      fetchedRows: page.length,
      malformed: [for (final r in page) if (unreadable.contains(r.id)) r.id],
      newestSeen: newest,
    );
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

  Future<GlucoseReadingRow?> localRowOrNull(String id) {
    return (db.select(db.glucoseReadingRows)..where((t) => t.id.equals(id)))
        .getSingleOrNull();
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

  // 서버 행 하나가 해석되지 않는다고 pull 전체가 멈추면, 그 행이 고쳐질 때까지
  // 동기화가 통째로 죽는다. 가장 현실적인 시나리오는 버전 차이다 — 새 앱이
  // 새로운 enum wireName 을 쓰면 구버전 앱은 그때부터 영원히 받지 못한다.
  group('해석 못 한 행', () {
    test('버리고 나머지는 계속 받는다', () async {
      api.rows.addAll([
        _serverReading(id: 'bad', updatedAt: DateTime.utc(2026, 3, 14, 2)),
        _serverReading(id: 'good', updatedAt: DateTime.utc(2026, 3, 14, 3)),
      ]);
      api.unreadable.add('bad');

      final report = await engine().syncOnce();

      expect(report.outcome, SyncOutcome.ok, reason: 'pull 이 실패로 끝나면 안 된다');
      expect(report.pulled, 1);
      expect(report.malformed, 1);
      expect(await localRowOrNull('good'), isNotNull);
      expect(await localRowOrNull('bad'), isNull);
    });

    // 붙잡으면 다시 받아도 또 못 읽으므로 pull 이 그 자리에서 제자리를 돈다.
    test('커서를 붙잡지 않는다 — 다시 받아도 또 못 읽는다', () async {
      api.rows.add(
        _serverReading(id: 'bad', updatedAt: DateTime.utc(2026, 3, 14, 2)),
      );
      api.unreadable.add('bad');

      await engine().syncOnce();
      await engine().syncOnce();

      expect(api.fetchedSince.last, DateTime.utc(2026, 3, 14, 2));
    });

    // 버린 행을 뺀 수로 페이지를 세면 마지막 페이지로 오판해 뒷 페이지를
    // 통째로 놓친다.
    test('버린 행이 페이지 경계 판정을 흐리지 않는다', () async {
      for (var i = 0; i < 6; i++) {
        api.rows.add(
          _serverReading(
            id: 'remote-$i',
            updatedAt: DateTime.utc(2026, 3, 14, 2, i),
          ),
        );
      }
      api.unreadable.addAll({'remote-0', 'remote-1'});

      final report = await engine(batchSize: 2).syncOnce();

      expect(report.pulled, 4, reason: '읽을 수 있는 행은 전부 받아야 한다');
      expect(report.malformed, 2);
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

    // pending 이라 건너뛴 행 너머로 커서가 가면, 그 push 가 한도에 닿아 막혔을 때
    // 서버 쪽 변경이 영영 다시 오지 않는다. 조용한 분기다.
    test('pending 때문에 건너뛴 행 앞에 커서를 세운다', () async {
      final reading = await addLocal(value: 137);
      api.rows.addAll([
        _serverReading(
          id: reading.id,
          enteredValue: 999,
          updatedAt: DateTime.utc(2026, 3, 14, 5),
        ),
        _serverReading(id: 'remote-1', updatedAt: DateTime.utc(2026, 3, 14, 6)),
      ]);

      // 한 번 실패시켜 아웃박스를 한도까지 밀어 둔다. 그 뒤로는 보낼 것이
      // 없어 push 가 던지지 않고, 로컬 행은 pending 인 채로 pull 이 돈다 —
      // 보고서가 지적한 바로 그 상황이다.
      api.failUpsert = StateError('보내기 실패');
      await engine(maxAttempts: 1).syncOnce();
      api.failUpsert = null;

      await engine(maxAttempts: 1).syncOnce();
      await engine(maxAttempts: 1).syncOnce();

      expect((await localRow(reading.id)).enteredValue, 137,
          reason: '안 보낸 로컬 변경은 그대로다');
      expect(await localRowOrNull('remote-1'), isNotNull,
          reason: '건너뛴 행 뒤의 기록은 그대로 적용된다');
      expect(api.fetchedSince.last, DateTime.utc(2026, 3, 14, 5),
          reason: '건너뛴 행 앞에 커서가 서야 나중에 다시 받는다');
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
