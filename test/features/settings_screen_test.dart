import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/target_range_preset.dart';
import 'package:sugarscan/features/settings/settings_screen.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

/// G14 — 설정 화면. 화면 코드는 고치지 않는다, 이 테스트는 표현을 고정한다.
///
/// 선택 상태는 `RadioGroup.groupValue` 에서 본다 — 타일의 groupValue 는
/// 조상에서 물려받는 값이라 화면 코드에서 넣지 않고, raw 타입
/// `find.byType(RadioListTile)` 는 제네릭 인스턴스와 맞지 않는다.
void main() {
  late AppDatabase db;

  setUp(() async {
    db = AppDatabase(NativeDatabase.memory());
  });

  tearDown(() => db.close());

  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(milliseconds: 100));
  }

  Future<void> pumpSettings(WidgetTester tester) async {
    // 원격은 기본값(RemoteDisabled) 그대로 — 서버 없는 빌드가 정상 상태다.
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
          home: SettingsScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
  }

  GlucoseUnit selectedUnit(WidgetTester tester) => tester
      .widget<RadioGroup<GlucoseUnit>>(
        find.byWidgetPredicate((w) => w is RadioGroup<GlucoseUnit>),
      )
      .groupValue!;

  TargetRangePreset selectedPreset(WidgetTester tester) => tester
      .widget<RadioGroup<TargetRangePreset>>(
        find.byWidgetPredicate((w) => w is RadioGroup<TargetRangePreset>),
      )
      .groupValue!;

  testWidgets('단위를 바꾸면 안내가 뜨고 선택이 옮겨 간다', (tester) async {
    await pumpSettings(tester);
    expect(selectedUnit(tester), GlucoseUnit.mgdl);

    await tester.tap(find.text('mmol/L'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 저장 확인 문구(스낵바). 원문 그대로.
    expect(
      find.textContaining('Display unit changed to mmol/L'),
      findsOneWidget,
    );

    // 스낵바가 사라진 뒤에도 선택은 유지된다(저장소에 적혔다).
    await tester.pump(const Duration(seconds: 4));
    await tester.pump(const Duration(milliseconds: 100));
    expect(selectedUnit(tester), GlucoseUnit.mmoll);

    await unmount(tester);
  });

  testWidgets('목표 범위를 고르면 저장된다', (tester) async {
    await pumpSettings(tester);
    // 기본값은 관찰 범위(fallback).
    expect(selectedPreset(tester), TargetRangePreset.observation);

    // 목록이 화면 아래쪽이다 — 뷰포트 밖 탭은 빈 좌표를 친다.
    await tester.ensureVisible(find.textContaining('Tight range'));
    await tester.pump();
    await tester.tap(find.textContaining('Tight range'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.textContaining('Target range set to'), findsOneWidget);

    // 스트림이 다시 흘러 라디오가 옮겨 간다 — 저장됐다는 증거.
    await tester.pump(const Duration(seconds: 4));
    await tester.pump(const Duration(milliseconds: 100));
    expect(selectedPreset(tester), TargetRangePreset.tight);

    await unmount(tester);
  });

  testWidgets('서버 미설정 빌드에서는 동기화 영역이 숨는다', (tester) async {
    await pumpSettings(tester);

    // 원격이 비활성(기본값)이면 Sync 섹션 제목 자체가 없다.
    expect(find.text('Sync'), findsNothing);
    // 계정 섹션도 로그인 상태가 아니면 숨는다.
    expect(find.textContaining('Sign out'), findsNothing);

    await unmount(tester);
  });
}
