import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/repositories/glucose_repository.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';

void main() {
  late AppDatabase db;
  late GlucoseRepository repo;
  late DateTime now;
  var idCounter = 0;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    now = DateTime.utc(2026, 3, 15, 9, 30);
    idCounter = 0;
    repo = GlucoseRepository(
      database: db,
      resolveTzName: () async => 'Asia/Seoul',
      clock: () => now,
      idGenerator: () => 'id-${++idCounter}',
    );
  });

  tearDown(() => db.close());

  Future<GlucoseReading> addMgdl(
    double value, {
    MeasurementTag? tag,
    DateTime? at,
  }) =>
      repo.add(
        value: value,
        unit: GlucoseUnit.mgdl,
        tag: tag ?? MeasurementTag.random,
        source: ReadingSource.manual,
        measuredAt: at,
      );

  group('저장', () {
    test('기록을 남기고 다시 읽어 온다', () async {
      final saved = await addMgdl(138);

      final loaded = await repo.byId(saved.id);
      expect(loaded, isNotNull);
      expect(loaded!.valueMgdl, 138);
      expect(loaded.tzName, 'Asia/Seoul');
      expect(loaded.source, ReadingSource.manual);
    });

    test('mmol/L 입력은 정본으로 변환해 저장하되 원본도 남긴다', () async {
      final saved = await repo.add(
        value: 7.6,
        unit: GlucoseUnit.mmoll,
        tag: MeasurementTag.postMeal,
        source: ReadingSource.ocr,
      );

      final loaded = (await repo.byId(saved.id))!;
      expect(loaded.valueMgdl, closeTo(136.94, 0.01));
      expect(loaded.enteredValue, 7.6);
      expect(loaded.enteredUnit, GlucoseUnit.mmoll);

      // 입력했던 단위로 보면 왕복 오차 없이 원본 그대로여야 한다.
      expect(loaded.valueIn(GlucoseUnit.mmoll), 7.6);
    });

    test('UTC 로 넣은 시각이 UTC 로 돌아온다', () async {
      // 정수 타임스탬프로 저장하면 읽을 때 로컬 시각이 되어 정본 규칙이 깨진다.
      final saved = await addMgdl(100, at: DateTime.utc(2026, 3, 15, 1, 2, 3));
      final loaded = (await repo.byId(saved.id))!;

      expect(loaded.measuredAtUtc.isUtc, isTrue);
      expect(loaded.measuredAtUtc, DateTime.utc(2026, 3, 15, 1, 2, 3));
    });

    test('OCR 메타데이터를 함께 남긴다', () async {
      final saved = await repo.add(
        value: 138,
        unit: GlucoseUnit.mgdl,
        tag: MeasurementTag.fasting,
        source: ReadingSource.ocr,
        ocrEngineId: 'segment_rule_v1',
        ocrConfidence: 0.93,
        ocrRawText: '138',
        adjustedByUser: true,
      );

      final loaded = (await repo.byId(saved.id))!;
      expect(loaded.ocrEngineId, 'segment_rule_v1');
      expect(loaded.ocrConfidence, closeTo(0.93, 0.001));
      // 어느 기종에서 엔진이 틀리는지 알려주는 지표라 유실되면 안 된다.
      expect(loaded.adjustedByUser, isTrue);
    });
  });

  group('아웃박스', () {
    test('저장과 같은 트랜잭션에서 보낼 목록에 오른다', () async {
      expect(await repo.pendingSyncCount(), 0);
      await addMgdl(138);
      expect(await repo.pendingSyncCount(), 1);
    });

    test('삭제도 보낼 목록에 오른다', () async {
      final saved = await addMgdl(138);
      await repo.delete(saved.id);

      // 저장 1건 + 삭제 1건.
      expect(await repo.pendingSyncCount(), 2);
    });

    test('수정도 보낼 목록에 오른다', () async {
      final saved = await addMgdl(138);
      await repo.update(saved.id, tag: MeasurementTag.postMeal);
      expect(await repo.pendingSyncCount(), 2);
    });
  });

  group('삭제', () {
    test('소프트 삭제한 기록은 목록에서 빠진다', () async {
      final saved = await addMgdl(138);
      await repo.delete(saved.id);

      expect(await repo.recent(), isEmpty);
    });

    test('행 자체는 남는다 — 다른 기기에도 삭제를 전달해야 한다', () async {
      final saved = await addMgdl(138);
      await repo.delete(saved.id);

      final loaded = await repo.byId(saved.id);
      expect(loaded, isNotNull);
      expect(loaded!.isDeleted, isTrue);
    });
  });

  group('수정', () {
    test('태그를 바꾼다', () async {
      final saved = await addMgdl(138, tag: MeasurementTag.random);
      await repo.update(saved.id, tag: MeasurementTag.fasting);

      expect((await repo.byId(saved.id))!.tag, MeasurementTag.fasting);
    });

    test('값을 바꾸면 정본도 함께 바뀐다', () async {
      final saved = await repo.add(
        value: 7.6,
        unit: GlucoseUnit.mmoll,
        tag: MeasurementTag.random,
        source: ReadingSource.manual,
      );
      await repo.update(saved.id, value: 5.0, unit: GlucoseUnit.mmoll);

      final loaded = (await repo.byId(saved.id))!;
      expect(loaded.enteredValue, 5.0);
      expect(loaded.valueMgdl, closeTo(90.09, 0.01));
    });
  });

  group('조회', () {
    test('최근 순으로 정렬한다', () async {
      await addMgdl(100, at: DateTime.utc(2026, 3, 13));
      await addMgdl(200, at: DateTime.utc(2026, 3, 15));
      await addMgdl(150, at: DateTime.utc(2026, 3, 14));

      final list = await repo.recent();
      expect(list.map((r) => r.valueMgdl), [200, 150, 100]);
    });

    test('limit 을 지킨다', () async {
      for (var i = 0; i < 5; i++) {
        await addMgdl(100 + i.toDouble(), at: DateTime.utc(2026, 3, 10 + i));
      }
      expect(await repo.recent(limit: 2), hasLength(2));
    });

    test('기간 조회는 경계를 포함한다', () async {
      await addMgdl(100, at: DateTime.utc(2026, 3, 10));
      await addMgdl(200, at: DateTime.utc(2026, 3, 15));
      await addMgdl(300, at: DateTime.utc(2026, 3, 20));

      final list = await repo.between(
        DateTime.utc(2026, 3, 10),
        DateTime.utc(2026, 3, 15),
      );
      expect(list.map((r) => r.valueMgdl), [200, 100]);
    });

    test('watchRecent 는 변경을 흘려보낸다', () async {
      final stream = repo.watchRecent();
      final first = await stream.first;
      expect(first, isEmpty);

      await addMgdl(138);
      final next = await stream.first;
      expect(next, hasLength(1));
    });
  });
}
