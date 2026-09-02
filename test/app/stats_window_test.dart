import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/repositories/glucose_repository.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';

/// 통계 기간 질의의 위쪽 경계.
///
/// 이 프로바이더는 한 번 구독되면 기간이 바뀔 때까지 살아 있고, Drift 는 처음
/// 만든 질의를 그대로 다시 돌린다. 위 경계를 구독 시점의 `now` 로 고정하면
/// 그 뒤에 저장한 기록이 질의 범위 밖으로 떨어져, 방금 남긴 오늘 기록이
/// 통계에서 통째로 사라진다.
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

  test('구독한 뒤에 저장한 기록도 통계 기간에 들어온다', () async {
    final container = ProviderContainer(
      overrides: [databaseProvider.overrideWithValue(db)],
    );
    addTearDown(container.dispose);

    // 먼저 구독해 질의를 만든다 — 여기서 위 경계가 굳는다.
    final sub = container.listen(statsReadingsProvider, (_, _) {});
    await container.read(statsReadingsProvider.future);

    await repository.add(
      value: 138,
      unit: GlucoseUnit.mgdl,
      tag: MeasurementTag.fasting,
      source: ReadingSource.manual,
    );

    // 스트림이 새 결과를 흘릴 때까지 기다린다.
    final readings = await container
        .read(glucoseRepositoryProvider)
        .watchBetween(
          DateTime.now().subtract(const Duration(days: 14)),
          DateTime.now().add(const Duration(days: 1)),
        )
        .first;
    expect(readings, hasLength(1));

    final fromProvider = await sub.read().when(
          data: (List<GlucoseReading> v) async => v,
          error: (Object e, StackTrace s) async => throw e,
          loading: () async =>
              await container.read(statsReadingsProvider.future),
        );
    expect(
      fromProvider.map((r) => r.valueMgdl),
      contains(138.0),
      reason: '구독 이후 저장한 기록이 통계에서 빠지면 안 된다',
    );
  });
}
