import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/repositories/glucose_repository.dart';
import 'package:sugarscan/data/sync/outbox_repository.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';

/// "대기 n건"은 **기록** 수여야 한다.
///
/// 아웃박스 행을 세면 한 기록을 세 번 고쳤을 때 "대기 3건"으로 보이지만 실제로
/// 올라가는 것은 한 건이다. 시도 한도에 닿아 멈춘 행도 빼야 한다 — 그쪽은
/// [SyncStatusBlocked] 가 따로 알리는데 여기서도 세면 같은 것을 두 번 센다.
void main() {
  late AppDatabase db;
  late GlucoseRepository repository;
  late OutboxRepository outbox;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
    repository = GlucoseRepository(
      database: db,
      resolveTzName: () async => 'Asia/Seoul',
    );
    outbox = OutboxRepository(database: db);
  });

  tearDown(() => db.close());

  Future<GlucoseReading> add({double value = 137}) => repository.add(
        value: value,
        unit: GlucoseUnit.mgdl,
        tag: MeasurementTag.fasting,
        source: ReadingSource.manual,
      );

  // StreamProvider 의 `.future` 는 구독자가 있어야 값을 흘린다. listen 없이
  // read 만 하면 영원히 대기한다 — 이 함정에 한 번 빠졌다.
  Future<int> count() async {
    final container = ProviderContainer(
      overrides: [databaseProvider.overrideWithValue(db)],
    );
    addTearDown(container.dispose);
    container.listen(pendingSyncCountProvider, (_, _) {});
    return container.read(pendingSyncCountProvider.future);
  }

  test('한 기록을 여러 번 고쳐도 한 건으로 센다', () async {
    final reading = await add();
    await repository.update(reading.id, value: 150);
    await repository.update(reading.id, value: 160);

    final rows = await db.select(db.syncOutboxRows).get();
    expect(rows, hasLength(3), reason: '아웃박스 행 자체는 셋이다');
    expect(await count(), 1);
  });

  test('기록이 둘이면 두 건이다', () async {
    await add();
    await add(value: 90);

    expect(await count(), 2);
  });

  test('한도에 닿아 멈춘 항목은 대기로 세지 않는다', () async {
    final reading = await add();
    final pending = await outbox.pending(limit: 10, maxAttempts: 6);

    // 기본 한도(6)까지 실패시킨다.
    for (var i = 0; i < 6; i++) {
      await outbox.markFailed(pending, '서버 거부');
    }

    expect(await outbox.blockedCount(maxAttempts: 6), greaterThan(0));
    expect(await count(), 0, reason: '막힌 것은 Blocked 가 따로 알린다');
    expect(reading.id, isNotEmpty);
  });

  test('보낼 것이 없으면 0 이다', () async {
    expect(await count(), 0);
  });
}
