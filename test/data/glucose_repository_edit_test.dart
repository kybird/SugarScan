import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/local/tables.dart';
import 'package:sugarscan/data/repositories/glucose_repository.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';

void main() {
  late AppDatabase db;
  late GlucoseRepository repository;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    repository = GlucoseRepository(
      database: db,
      resolveTzName: () async => 'Asia/Seoul',
    );
  });

  tearDown(() => db.close());

  Future<GlucoseReading> add({
    double value = 137,
    GlucoseUnit unit = GlucoseUnit.mgdl,
    String? note,
  }) {
    return repository.add(
      value: value,
      unit: unit,
      tag: MeasurementTag.fasting,
      source: ReadingSource.manual,
      note: note,
    );
  }

  Future<GlucoseReadingRow> row(String id) {
    return (db.select(db.glucoseReadingRows)..where((t) => t.id.equals(id)))
        .getSingle();
  }

  Future<int> outboxCount() async =>
      (await db.select(db.syncOutboxRows).get()).length;

  group('되돌리기', () {
    test('삭제한 기록을 되살린다', () async {
      final reading = await add();
      await repository.delete(reading.id);
      expect((await row(reading.id)).deletedAt, isNotNull);

      await repository.restore(reading.id);

      final restored = await row(reading.id);
      expect(restored.deletedAt, isNull);
      expect(await repository.recent(), hasLength(1));
    });

    // 이미 서버로 삭제가 전파됐을 수 있다. 되살렸다는 사실도 똑같이 전파되어야
    // 다른 기기에서 살아난다.
    test('되살리기도 아웃박스를 거친다', () async {
      final reading = await add();
      final afterAdd = await outboxCount();

      await repository.delete(reading.id);
      await repository.restore(reading.id);

      expect(await outboxCount(), afterAdd + 2);
      expect((await row(reading.id)).syncState, SyncState.pending);
    });

    test('되살려도 원래 값은 그대로다', () async {
      final reading = await add(value: 7.6, unit: GlucoseUnit.mmoll);
      await repository.delete(reading.id);
      await repository.restore(reading.id);

      final restored = await row(reading.id);
      expect(restored.enteredValue, 7.6);
      expect(restored.enteredUnit, GlucoseUnit.mmoll);
    });
  });

  group('수정', () {
    test('값과 단위를 함께 바꾸면 정본도 다시 계산된다', () async {
      final reading = await add(value: 137);

      await repository.update(
        reading.id,
        value: 7.6,
        unit: GlucoseUnit.mmoll,
      );

      final updated = await row(reading.id);
      expect(updated.enteredValue, 7.6);
      expect(updated.enteredUnit, GlucoseUnit.mmoll);
      expect(updated.valueMgdl, closeTo(136.94, 0.01));
    });

    // 같은 숫자가 두 단위에서 정반대 의미가 된다. 단위만 다시 지정하는 것은
    // 변환이 아니라 재해석이고, 그 결과가 정본에 반영되어야 한다.
    test('단위만 다시 지정하면 같은 숫자가 다른 값이 된다', () async {
      final reading = await add(value: 40, unit: GlucoseUnit.mgdl);
      expect((await row(reading.id)).valueMgdl, 40);

      await repository.update(reading.id, value: 40, unit: GlucoseUnit.mmoll);

      // 40 mg/dL(중증 저혈당) → 40 mmol/L(중증 고혈당). 뒤집힌다.
      expect((await row(reading.id)).valueMgdl, closeTo(720.7, 0.1));
    });

    test('태그만 바꾸면 값은 건드리지 않는다', () async {
      final reading = await add(value: 137);

      await repository.update(reading.id, tag: MeasurementTag.bedtime);

      final updated = await row(reading.id);
      expect(updated.tag, MeasurementTag.bedtime);
      expect(updated.enteredValue, 137);
      expect(updated.valueMgdl, 137);
    });

    test('수정하면 pending 으로 돌아가고 아웃박스에 실린다', () async {
      final reading = await add();
      final afterAdd = await outboxCount();

      await repository.update(reading.id, tag: MeasurementTag.bedtime);

      expect((await row(reading.id)).syncState, SyncState.pending);
      expect(await outboxCount(), afterAdd + 1);
    });
  });

  group('메모', () {
    // null 과 빈 문자열을 같게 두면 메모를 한 번 남긴 뒤로는 지울 방법이 없다.
    test('null 은 바꾸지 않는다', () async {
      final reading = await add(note: '아침 공복');

      await repository.update(reading.id, tag: MeasurementTag.bedtime);

      expect((await row(reading.id)).note, '아침 공복');
    });

    test('빈 문자열은 지운다', () async {
      final reading = await add(note: '아침 공복');

      await repository.update(reading.id, note: '');

      expect((await row(reading.id)).note, isNull);
    });

    test('공백만 있어도 지운다', () async {
      final reading = await add(note: '아침 공복');

      await repository.update(reading.id, note: '   ');

      expect((await row(reading.id)).note, isNull);
    });

    test('새 메모를 남긴다', () async {
      final reading = await add();

      await repository.update(reading.id, note: '운동 직후');

      expect((await row(reading.id)).note, '운동 직후');
    });
  });
}
