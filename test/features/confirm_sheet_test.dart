import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/features/scan/confirm_sheet.dart';
import 'package:sugarscan/features/scan/scan_entry.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

/// G14 — 저장 전 확인 시트. **저장은 사용자의 1탭을 거친다**는 안전·규제
/// 요구사항을 고정한다. 화면 코드는 고치지 않는다.
void main() {
  ScanEntry? result;

  ScanEntry entry({double value = 137}) => ScanEntry(
        value: value,
        unit: GlucoseUnit.mgdl,
        tag: MeasurementTag.fasting,
        source: ReadingSource.ocr,
      );

  setUp(() => result = null);

  Future<void> openSheet(WidgetTester tester, ScanEntry e) async {
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
                  result = await showConfirmSheet(context, entry: e);
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
    // 시트는 기본 뷰포트보다 길다(W12).
    await tester.ensureVisible(find.byType(FilledButton));
    await tester.pump();
    await tester.tap(find.byType(FilledButton));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets('인식값이 그대로 보인다', (tester) async {
    await openSheet(tester, entry(value: 137));

    // 값이 화면에서 가장 두드러지게, 단위와 함께.
    expect(find.text('137'), findsOneWidget);
    expect(find.text('mg/dL'), findsOneWidget);

    await unmount(tester);
  });

  testWidgets('값을 고치면 adjustedByUser 가 선다', (tester) async {
    await openSheet(tester, entry(value: 137));

    await tester.ensureVisible(find.byIcon(Icons.add));
    await tester.pump();
    await tester.tap(find.byIcon(Icons.add));
    await tester.pump();

    expect(find.text('138'), findsOneWidget);

    await save(tester);
    expect(result, isNotNull);
    expect(result!.value, 138);
    expect(result!.adjustedByUser, isTrue);

    await unmount(tester);
  });

  testWidgets('저장 버튼을 누르지 않으면 아무것도 저장되지 않는다', (tester) async {
    await openSheet(tester, entry(value: 137));

    // 값을 고쳤더라도 —
    await tester.ensureVisible(find.byIcon(Icons.add));
    await tester.pump();
    await tester.tap(find.byIcon(Icons.add));
    await tester.pump();

    // 취소로 닫으면 결과는 없다. 저장은 확인 1탭 없이 일어나지 않는다.
    await tester.ensureVisible(find.text('Cancel'));
    await tester.pump();
    await tester.tap(find.text('Cancel'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(result, isNull);

    await unmount(tester);
  });

  testWidgets('저장을 누르면 고치지 않은 값도 그대로 확정된다', (tester) async {
    await openSheet(tester, entry(value: 137));
    await save(tester);

    expect(result, isNotNull);
    expect(result!.value, 137);
    // 고치지 않았으면 adjustedByUser 는 선지 않는다.
    expect(result!.adjustedByUser, isFalse);

    await unmount(tester);
  });
}
