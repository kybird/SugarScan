import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/features/history/edit_reading_sheet.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

GlucoseReading reading({
  double value = 137,
  GlucoseUnit unit = GlucoseUnit.mgdl,
  String? note,
}) {
  return GlucoseReading.fromEntry(
    id: 'r1',
    measuredAtUtc: DateTime.utc(2026, 3, 14, 1, 30),
    tzName: 'Asia/Seoul',
    utcOffsetMinutes: 540,
    enteredValue: value,
    enteredUnit: unit,
    tag: MeasurementTag.fasting,
    source: ReadingSource.manual,
    now: DateTime.utc(2026, 3, 14, 1, 31),
    note: note,
  );
}

void main() {
  ReadingEdit? result;
  var closed = false;

  setUp(() {
    result = null;
    closed = false;
  });

  /// 시트를 띄운다.
  ///
  /// `pumpAndSettle` 을 쓰지 않는다 — 이 앱 규칙이다. 정해진 만큼만 넘긴다.
  Future<void> openSheet(WidgetTester tester, GlucoseReading value) async {
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
                  result = await showEditReadingSheet(context, reading: value);
                  closed = true;
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

  /// 트리를 테스트 본문 안에서 내린다. 밖에서 해제되면 남은 타이머가
  /// 미처리로 잡힌다.
  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(milliseconds: 100));
  }

  Future<void> save(WidgetTester tester) async {
    // 시트가 기본 테스트 뷰포트보다 길다. 그냥 tap 하면 화면 밖 좌표를 쳐서
    // 아무 일도 일어나지 않고, 테스트가 "저장이 안 됐다"로 잘못 통과한다.
    await tester.ensureVisible(find.byType(FilledButton));
    await tester.pump();
    await tester.tap(find.byType(FilledButton));
    // 닫히는 애니메이션과, pop 결과를 기다리는 async 콜백의 재개까지 넘긴다.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));
  }

  Finder valueField() => find.byType(TextField).first;

  String valueText(WidgetTester tester) =>
      tester.widget<TextField>(valueField()).controller!.text;

  // 이 화면에서 가장 위험한 실수다. 표시 단위로 값을 보여 주면, mmol/L 로 넣은
  // 7.6 이 mg/dL 사용자에게 137 로 보이고 그대로 저장하는 순간 원본이 사라진다.
  testWidgets('값을 표시 단위가 아니라 기록의 입력 단위로 보여 준다', (tester) async {
    await openSheet(tester, reading(value: 7.6, unit: GlucoseUnit.mmoll));

    expect(valueText(tester), '7.6');
    expect(find.text('mmol/L'), findsWidgets);

    await unmount(tester);
  });

  testWidgets('반대 단위 환산값을 함께 보여 준다', (tester) async {
    await openSheet(tester, reading(value: 7.6, unit: GlucoseUnit.mmoll));

    // 137 mg/dL 에 해당한다는 줄. 단위를 잘못 고른 것을 사용자가 눈으로
    // 알아채게 하는 장치다.
    expect(find.textContaining('137'), findsOneWidget);

    await unmount(tester);
  });

  testWidgets('메모를 그대로 채워 준다', (tester) async {
    await openSheet(tester, reading(note: '아침 공복'));

    expect(find.text('아침 공복'), findsOneWidget);

    await unmount(tester);
  });

  testWidgets('범위를 벗어난 값은 저장되지 않는다', (tester) async {
    await openSheet(tester, reading());

    await tester.enterText(valueField(), '9999');
    await tester.pump();
    await save(tester);

    // 저장 경로와 같은 검증기다. 시트가 닫히지 않는다.
    expect(closed, isFalse);
    expect(find.byType(TextField), findsWidgets);

    await unmount(tester);
  });

  testWidgets('저장하면 입력한 값과 단위를 돌려준다', (tester) async {
    await openSheet(tester, reading(value: 137));

    await tester.enterText(valueField(), '150');
    await tester.pump();
    await save(tester);

    expect(closed, isTrue);
    expect(result!.value, 150);
    expect(result!.unit, GlucoseUnit.mgdl);
    expect(result!.tag, MeasurementTag.fasting);

    await unmount(tester);
  });

  // 저장소가 null(바꾸지 않음)과 빈 문자열(지움)을 구분한다. 시트가 null 을
  // 돌려주면 메모를 한 번 남긴 뒤로는 지울 방법이 없어진다.
  testWidgets('메모를 비우면 빈 문자열을 돌려준다', (tester) async {
    await openSheet(tester, reading(note: '아침 공복'));

    await tester.enterText(find.widgetWithText(TextField, '아침 공복'), '');
    await tester.pump();
    await save(tester);

    expect(closed, isTrue);
    expect(result!.note, '');

    await unmount(tester);
  });
}
