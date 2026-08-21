import 'package:fl_chart/fl_chart.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/repositories/glucose_repository.dart';
import 'package:sugarscan/data/repositories/settings_repository.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/domain/models/target_range_preset.dart';
import 'package:sugarscan/features/stats/stats_screen.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

void main() {
  late AppDatabase db;
  late GlucoseRepository repository;

  setUp(() async {
    // 호스트에서 진짜 SQLite 를 돌린다. 통계 화면은 저장소 위에 서 있으므로
    // 가짜 저장소로 덮으면 정작 검증하려는 경로가 빠진다.
    db = AppDatabase(NativeDatabase.memory());
    repository = GlucoseRepository(
      database: db,
      resolveTzName: () async => 'Asia/Seoul',
    );
    await SettingsRepository(database: db).confirmUnit(GlucoseUnit.mgdl);
  });

  tearDown(() => db.close());

  Future<void> add(double value, {MeasurementTag? tag, DateTime? at}) {
    return repository.add(
      value: value,
      unit: GlucoseUnit.mgdl,
      tag: tag ?? MeasurementTag.random,
      source: ReadingSource.manual,
      measuredAt: at,
    );
  }

  Future<void> pumpStats(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [databaseProvider.overrideWithValue(db)],
        child: const MaterialApp(
          localizationsDelegates: [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: StatsScreen(),
        ),
      ),
    );

    // `pumpAndSettle` 을 쓰지 않는다. 정해진 만큼만 시계를 넘긴다.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 300));
  }

  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(milliseconds: 100));
  }

  // 0건과 "평균 0" 은 전혀 다른 이야기다. 숫자 0 을 그리면 사용자는 그것을
  // 측정 결과로 읽는다.
  testWidgets('기록이 없으면 숫자를 그리지 않는다', (tester) async {
    await pumpStats(tester);

    expect(find.text('No readings in this period'), findsOneWidget);
    expect(find.text('Average'), findsNothing);

    await unmount(tester);
  });

  testWidgets('평균과 건수를 보여 준다', (tester) async {
    await add(100);
    await add(140);
    await add(180);

    await pumpStats(tester);

    expect(find.text('Average'), findsOneWidget);
    expect(find.text('140'), findsWidgets);
    expect(find.text('3 readings'), findsOneWidget);

    await unmount(tester);
  });

  // 요약을 카드 넷으로 쪼개면 세로로 쌓이면서 그래프가 첫 화면 밖으로 밀려난다.
  // 숫자를 보러 온 사람이 스크롤부터 해야 하는 화면이 된다.
  testWidgets('그래프가 스크롤 없이 첫 화면에 들어온다', (tester) async {
    for (var i = 0; i < 5; i++) {
      await add(100 + i * 20);
    }

    await pumpStats(tester);

    final chart = find.byType(LineChart);
    expect(chart, findsOneWidget);

    final top = tester.getTopLeft(chart).dy;
    final viewportHeight = tester.view.physicalSize.height /
        tester.view.devicePixelRatio;
    expect(
      top,
      lessThan(viewportHeight),
      reason: '그래프 상단이 화면 아래로 밀려났다',
    );

    await unmount(tester);
  });

  testWidgets('최저·최고·편차를 함께 보여 준다', (tester) async {
    await add(100);
    await add(180);

    await pumpStats(tester);

    expect(find.text('Low'), findsOneWidget);
    expect(find.text('High'), findsOneWidget);
    expect(find.text('SD'), findsOneWidget);
    expect(find.text('100'), findsWidgets);
    expect(find.text('180'), findsWidgets);

    await unmount(tester);
  });

  testWidgets('목표 범위 안 비율을 백분율로 보여 준다', (tester) async {
    await add(100); // 범위 안
    await add(300); // 범위 밖

    await pumpStats(tester);

    expect(find.text('50%'), findsOneWidget);

    await unmount(tester);
  });

  // CGM 의 TIR 과 혼동하면 임상적으로 잘못 읽힌다. 문구가 사라지면 안 된다.
  testWidgets('건수 기준이라는 단서를 항상 붙인다', (tester) async {
    await add(100);

    await pumpStats(tester);

    expect(find.textContaining('Counts readings, not time'), findsOneWidget);

    await unmount(tester);
  });

  testWidgets('태그별 평균은 기록이 있는 태그만 나온다', (tester) async {
    await add(100, tag: MeasurementTag.fasting);
    await add(140, tag: MeasurementTag.fasting);

    await pumpStats(tester);

    // 태그 목록은 ListView 아래쪽이라 뷰포트 밖이다. 스크롤하지 않으면
    // 요소가 만들어지지 않아 "없다"로 잘못 통과한다.
    await tester.scrollUntilVisible(find.text('Average by tag'), 200);
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Fasting'), findsOneWidget);
    // 기록이 없는 태그를 0 으로 채우지 않는다.
    expect(find.text('Bedtime'), findsNothing);

    await unmount(tester);
  });

  testWidgets('기간을 좁히면 바깥 기록이 빠진다', (tester) async {
    final now = DateTime.now();
    await add(100, at: now);
    await add(300, at: now.subtract(const Duration(days: 20)));

    await pumpStats(tester);

    // 기본 창은 14일이라 20일 전 기록은 안 들어온다.
    expect(find.text('1 readings'), findsOneWidget);

    // 30일로 넓히면 들어온다.
    await tester.tap(find.text('30 days'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('2 readings'), findsOneWidget);

    await unmount(tester);
  });

  // 목표 범위를 바꾸면 같은 기록이 다르게 집계된다. 화면이 설정을 실제로
  // 따라가는지가 이 기능의 전부다.
  testWidgets('고른 목표 범위가 비율과 표기에 반영된다', (tester) async {
    await add(100); // 어느 범위든 안
    await add(160); // 관찰(70–180) 안, 좁은 범위(70–140) 밖

    await pumpStats(tester);
    expect(find.text('100%'), findsOneWidget);
    expect(find.textContaining('70–180'), findsOneWidget);
    await unmount(tester);

    await SettingsRepository(database: db)
        .setTargetRange(TargetRangePreset.tight);

    await pumpStats(tester);
    expect(find.text('50%'), findsOneWidget);
    expect(find.textContaining('70–140'), findsOneWidget);
    await unmount(tester);
  });

  // 정본은 mg/dL 이고 표시할 때만 옮긴다. 화면이 정본을 그대로 그리면
  // mmol/L 사용자에게 137 이 보인다.
  testWidgets('표시 단위가 mmol/L 이면 그 단위로 보여 준다', (tester) async {
    await SettingsRepository(database: db).confirmUnit(GlucoseUnit.mmoll);
    await add(137);

    await pumpStats(tester);

    expect(find.text('7.6'), findsWidgets);
    expect(find.text('137'), findsNothing);

    await unmount(tester);
  });

  // 스크린리더 사용자에게도 요약 카드가 통계 한 문장으로 읽혀야 한다.
  // 라벨은 보이는 내용과 같게 — 판정 문구가 섞이면 안 된다.
  testWidgets('요약 카드가 스크린리더용 라벨을 갖는다', (tester) async {
    final handle = tester.ensureSemantics();

    await add(100);
    await add(140);

    await pumpStats(tester);

    expect(
      find.bySemanticsLabel(RegExp('Average 120 mg/dL, 2 readings')),
      findsOneWidget,
    );
    expect(
      find.bySemanticsLabel(RegExp('Within target range 100%')),
      findsOneWidget,
    );

    handle.dispose();
    await unmount(tester);
  });
}
