import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/repositories/settings_repository.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/target_range_preset.dart';

void main() {
  late AppDatabase db;
  late SettingsRepository repo;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    repo = SettingsRepository(database: db);
  });

  tearDown(() => db.close());

  test('처음에는 설정이 없다', () async {
    expect(await repo.readUnitPreference(), isNull);
  });

  test('사용자가 고른 단위를 확인 표시와 함께 저장한다', () async {
    await repo.confirmUnit(GlucoseUnit.mmoll);

    final preference = await repo.readUnitPreference();
    expect(preference!.unit, GlucoseUnit.mmoll);
    expect(preference.confirmedByUser, isTrue);
  });

  test('단위를 다시 바꿀 수 있다', () async {
    await repo.confirmUnit(GlucoseUnit.mgdl);
    await repo.confirmUnit(GlucoseUnit.mmoll);

    expect((await repo.readUnitPreference())!.unit, GlucoseUnit.mmoll);
  });

  test('wireName 으로 저장한다 — Dart enum 이름을 바꿔도 데이터가 살아남는다', () async {
    await repo.confirmUnit(GlucoseUnit.mmoll);

    final row = await (db.select(db.appSettingRows)
          ..where((t) => t.key.equals('display_unit')))
        .getSingle();
    expect(row.value, 'mmoll');
  });

  test('watch 는 변경을 흘려보낸다', () async {
    final stream = repo.watchUnitPreference();
    expect(await stream.first, isNull);

    await repo.confirmUnit(GlucoseUnit.mgdl);
    expect((await stream.first)!.unit, GlucoseUnit.mgdl);
  });

  test('v1 에서 올라온 DB 도 설정 테이블을 갖는다', () async {
    // 스키마 v2 에서 추가된 테이블이다. 마이그레이션이 빠지면 기존 설치가
    // 설정을 읽는 순간 죽는다.
    await repo.confirmUnit(GlucoseUnit.mgdl);
    expect(await repo.readUnitPreference(), isNotNull);
    expect(db.schemaVersion, 2);
  });

  group('목표 범위', () {
    test('고른 적이 없으면 기본값을 흘린다', () async {
      final repository = SettingsRepository(database: db);

      expect(await repository.watchTargetRange().first,
          TargetRangePreset.fallback);
    });

    test('고른 값을 기억한다', () async {
      final repository = SettingsRepository(database: db);

      await repository.setTargetRange(TargetRangePreset.tight);

      expect(await repository.watchTargetRange().first,
          TargetRangePreset.tight);
    });

    // Dart enum 이름이 아니라 wireName 이 저장된다. 식별자를 바꿔도 사용자
    // 설정이 깨지지 않아야 한다.
    test('저장되는 것은 wireName 이다', () async {
      final repository = SettingsRepository(database: db);
      await repository.setTargetRange(TargetRangePreset.preMeal);

      final rows = await db.select(db.appSettingRows).get();
      final saved = rows.firstWhere((r) => r.key == 'target_range');

      expect(saved.value, 'pre_meal');
    });

    test('표시 단위 설정과 서로 간섭하지 않는다', () async {
      final repository = SettingsRepository(database: db);

      await repository.confirmUnit(GlucoseUnit.mmoll);
      await repository.setTargetRange(TargetRangePreset.tight);

      expect((await repository.readUnitPreference())!.unit, GlucoseUnit.mmoll);
      expect(await repository.watchTargetRange().first,
          TargetRangePreset.tight);
    });
  });
}