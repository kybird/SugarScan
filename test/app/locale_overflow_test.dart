import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/repositories/glucose_repository.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/features/dashboard/dashboard_screen.dart';
import 'package:sugarscan/features/history/history_screen.dart';
import 'package:sugarscan/features/onboarding/unit_onboarding_screen.dart';
import 'package:sugarscan/features/scan/confirm_sheet.dart';
import 'package:sugarscan/features/scan/manual_entry_sheet.dart';
import 'package:sugarscan/features/scan/scan_entry.dart';
import 'package:sugarscan/features/scan/scan_screen.dart';
import 'package:sugarscan/features/settings/settings_screen.dart';
import 'package:sugarscan/features/stats/stats_screen.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

/// G9 — 6개 언어 × 전 화면 글자 넘침 점검.
///
/// **무인 세션은 화면을 눈으로 볼 수 없다.** 대신 이 앱의 객관 신호를 쓴다 —
/// RenderFlex overflow 는 프레임워크가 FlutterError 로 보고하고 위젯 테스트는
/// 그것만으로 실패한다. 즉 **이 파일의 테스트가 통과하면 넘침이 없다**는
/// 기계적 증거가 되고, 실패하면 넘침이 있다는 보고가 된다.
///
/// 로케일은 `MaterialApp.locale` 로 고정한다(지시서가 제시한 방식 — 임시 고정,
/// 커밋되는 코드는 하네스뿐이다). 뷰포트는 일반적인 안드로이드 논리 폭
/// 390×844 하나로 잡는다(독일어가 가장 길다는 전제의 위험 폭).
///
/// 한계(보고서에도 적는다): 넘치지 않으면서 어색한 배치(잘림 없는 조악한
/// 간격 등)는 이 신호로 안 잡힌다 — 사람 눈의 몫으로 남는다.
void main() {
  // 지시서 순서: en·ko·es·pt·de·fr.
  const locales = [
    Locale('en'),
    Locale('ko'),
    Locale('es'),
    Locale('pt'),
    Locale('de'),
    Locale('fr'),
  ];

  late AppDatabase db;

  setUp(() async {
    db = AppDatabase(NativeDatabase.memory());
    final repository = GlucoseRepository(
      database: db,
      resolveTzName: () async => 'Asia/Seoul',
    );
    await repository.add(
      value: 137,
      unit: GlucoseUnit.mgdl,
      tag: MeasurementTag.fasting,
      source: ReadingSource.manual,
    );
    await repository.add(
      value: 102,
      unit: GlucoseUnit.mgdl,
      tag: MeasurementTag.postMeal,
      source: ReadingSource.ocr,
      note: 'note for layout width — 접힌 라벨의 최대 폭도 잡게 놓는다',
    );
  });

  tearDown(() => db.close());

  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(milliseconds: 100));
  }

  Widget host(Widget child, Locale locale) => ProviderScope(
        overrides: [databaseProvider.overrideWithValue(db)],
        child: MaterialApp(
          locale: locale,
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: child,
        ),
      );

  /// 화면 정의 — 이름과 띄우는 법. 시트는 버튼을 경유해 연다.
  final screens = <String, Future<void> Function(WidgetTester, Locale)>{
    '대시보드': (tester, locale) async {
      await tester.pumpWidget(host(const DashboardScreen(), locale));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));
    },
    '기록 목록': (tester, locale) async {
      await tester.pumpWidget(host(const HistoryScreen(), locale));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));
    },
    '통계': (tester, locale) async {
      await tester.pumpWidget(host(const StatsScreen(), locale));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));
      // 아래쪽 섹션(태그별 평균·면책)도 지나가 본다.
      await tester.drag(find.byType(ListView), const Offset(0, -600));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
    },
    '설정': (tester, locale) async {
      await tester.pumpWidget(host(const SettingsScreen(), locale));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.drag(find.byType(ListView), const Offset(0, -600));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
    },
    '단위 확인 온보딩': (tester, locale) async {
      await tester.pumpWidget(host(const UnitOnboardingScreen(), locale));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
    },
    '스캔(카메라 없음 경로)': (tester, locale) async {
      await tester.pumpWidget(host(const ScanScreen(), locale));
      await tester.pump();
      // 카메라 준비 타임아웃이 지나가도록 시계를 넘긴다(스모크 관용구).
      await tester.pump(const Duration(seconds: 8));
    },
    '직접 입력 시트': (tester, locale) async {
      await tester.pumpWidget(host(
        Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () =>
                    showManualEntrySheet(context, unit: GlucoseUnit.mgdl),
                child: const Text('open'),
              ),
            ),
          ),
        ),
        locale,
      ));
      await tester.tap(find.text('open'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
    },
    '저장 확인 시트': (tester, locale) async {
      await tester.pumpWidget(host(
        Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () => showConfirmSheet(
                  context,
                  entry: ScanEntry(
                    value: 137,
                    unit: GlucoseUnit.mgdl,
                    tag: MeasurementTag.fasting,
                    source: ReadingSource.ocr,
                  ),
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
        locale,
      ));
      await tester.tap(find.text('open'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
    },
  };

  for (final locale in locales) {
    for (final entry in screens.entries) {
      testWidgets('${entry.key} — ${locale.languageCode} 넘침 없음',
          (tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        await entry.value(tester, locale);

        // 여기까지 예외 없이 왔으면 넘침이 없다는 뜻이다(overflow 는
        // FlutterError 로 테스트를 실패시킨다).
        await unmount(tester);
      }, timeout: const Timeout(Duration(minutes: 2)));
    }
  }
}
