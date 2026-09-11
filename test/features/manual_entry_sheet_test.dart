import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/features/scan/manual_entry_sheet.dart';
import 'package:sugarscan/features/scan/scan_entry.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

/// G14 — 직접 입력 시트. 카메라가 막혀도 기록은 남을 수 있어야 한다는
/// 규칙의 최전선이다. 화면 코드는 고치지 않는다.
void main() {
  ScanEntry? result;

  setUp(() => result = null);

  Future<void> openSheet(WidgetTester tester, GlucoseUnit unit) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () async {
                  result = await showManualEntrySheet(context, unit: unit);
                },
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
  }

  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(milliseconds: 100));
  }

  Future<void> save(WidgetTester tester) async {
    // 시트는 기본 뷰포트보다 길다 — 화면 밖 좌표를 치면 저장이 안 되는데
    // "저장 안 됨"으로 잘못 통과한다(W12 교훈).
    await tester.ensureVisible(find.byType(FilledButton));
    await tester.pump();
    await tester.tap(find.byType(FilledButton));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets('범위 밖 값은 저장되지 않고 안내를 보여 준다', (tester) async {
    await openSheet(tester, GlucoseUnit.mgdl);

    // 세 자리여야 모양 검사(1~3자리)를 지나 범위 검사에 닿는다.
    await tester.enterText(find.byType(TextField), '999');
    await tester.pump();
    await save(tester);

    // 시트는 닫히지 않고, 결과도 없다.
    expect(result, isNull);
    expect(
      find.text('That is outside what a meter can show'),
      findsOneWidget,
    );

    // 같은 자리에서 고쳐 넣으면 저장된다 — 경고가 경로를 막는 게 아니다.
    await tester.enterText(find.byType(TextField), '120');
    await tester.pump();
    await save(tester);

    expect(result, isNotNull);
    expect(result!.value, 120);
    expect(result!.unit, GlucoseUnit.mgdl);
    expect(result!.source, ReadingSource.manual);

    await unmount(tester);
  });

  testWidgets('쉼표 소수점(7,6)은 받아들여진다', (tester) async {
    await openSheet(tester, GlucoseUnit.mmoll);

    await tester.enterText(find.byType(TextField), '7,6');
    await tester.pump();
    await save(tester);

    // 스위스 사용자가 7,6 을 넣었으면 7.6 로 해석돼야 한다.
    expect(result, isNotNull);
    expect(result!.value, closeTo(7.6, 1e-9));
    expect(result!.unit, GlucoseUnit.mmoll);

    await unmount(tester);
  });

  testWidgets('고른 태그가 결과에 반영된다', (tester) async {
    await openSheet(tester, GlucoseUnit.mgdl);

    await tester.ensureVisible(find.text('After meal'));
    await tester.pump();
    await tester.tap(find.text('After meal'));
    await tester.pump();

    await tester.enterText(find.byType(TextField), '102');
    await tester.pump();
    await save(tester);

    expect(result, isNotNull);
    expect(result!.tag, MeasurementTag.postMeal);

    await unmount(tester);
  });
}
