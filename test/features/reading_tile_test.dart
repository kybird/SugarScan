import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/features/shared/reading_tile.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

GlucoseReading reading({String? note}) {
  return GlucoseReading.fromEntry(
    id: 'r1',
    measuredAtUtc: DateTime.utc(2026, 3, 14, 1, 30),
    tzName: 'Asia/Seoul',
    utcOffsetMinutes: 540,
    enteredValue: 137,
    enteredUnit: GlucoseUnit.mgdl,
    tag: MeasurementTag.fasting,
    source: ReadingSource.manual,
    now: DateTime.utc(2026, 3, 14, 1, 31),
    note: note,
  );
}

void main() {
  Future<void> pumpTile(WidgetTester tester, GlucoseReading value) async {
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(body: ReadingTile(reading: value, unit: GlucoseUnit.mgdl)),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));
  }

  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(milliseconds: 100));
  }

  testWidgets('메모가 있으면 부제 아래 한 줄로 보여 준다', (tester) async {
    await pumpTile(tester, reading(note: '아침 공복'));

    final note = find.text('아침 공복');
    expect(note, findsOneWidget);

    // 시각·태그·출처 부제보다 아래에 붙는다.
    final subtitle = find.textContaining('Fasting');
    expect(subtitle, findsOneWidget);
    expect(tester.getTopLeft(note).dy, greaterThan(tester.getTopLeft(subtitle).dy));

    // 길면 한 줄로 자른다.
    final noteWidget = tester.widget<Text>(note);
    expect(noteWidget.maxLines, 1);
    expect(noteWidget.overflow, TextOverflow.ellipsis);

    await unmount(tester);
  });

  // 메모 없는 기록의 높이가 변하면 목록 전체의 밀도가 흔들린다. 없으면 아예
  // 그리지 않는다 — 공백 문자열도 없는 것과 같다.
  testWidgets('메모가 없으면 그리지 않고 높이도 그대로다', (tester) async {
    await pumpTile(tester, reading());
    final plainHeight = tester.getSize(find.byType(ReadingTile)).height;

    // 값·단위·부제 세 Text 뿐이다.
    final texts = find
        .descendant(of: find.byType(ReadingTile), matching: find.byType(Text))
        .evaluate()
        .length;
    expect(texts, 3);

    await pumpTile(tester, reading(note: '   '));
    expect(
      tester.getSize(find.byType(ReadingTile)).height,
      plainHeight,
      reason: '공백 메모가 빈 줄을 남겼다',
    );

    // 메모가 붙으면 타일이 그만큼 커진다 — 없을 때의 높이가 원래 높이다.
    await pumpTile(tester, reading(note: '아침 공복'));
    expect(
      tester.getSize(find.byType(ReadingTile)).height,
      greaterThan(plainHeight),
    );

    await unmount(tester);
  });

  // 값만 읽히면 단위가 생략된다. 혈당에서 단위는 숫자의 뜻을 바꾸므로 타일
  // 전체가 "값 단위, 시각, 태그, 출처" 한 문장으로 낭독되어야 한다.
  testWidgets('스크린리더에게 값·단위·시각·태그·출처를 한 문장으로 읽는다', (tester) async {
    final handle = tester.ensureSemantics();

    await pumpTile(tester, reading());
    final timeText = DateFormat.yMMMd('en')
        .add_jm()
        .format(reading().measuredAtLocalWallClock);
    expect(
      find.bySemanticsLabel('137 mg/dL, $timeText, Fasting, Manual'),
      findsOneWidget,
    );

    // 메모는 라벨 문자열에 직접 넣지 않지만 같은 의미론 노드로 병합되어
    // 이어서 읽힌다 — 낭독에서 빠지는 보이는 내용이 없어야 한다.
    await pumpTile(tester, reading(note: '아침 공복'));
    expect(find.bySemanticsLabel(RegExp('아침 공복')), findsOneWidget);

    handle.dispose();
    await unmount(tester);
  });
}
