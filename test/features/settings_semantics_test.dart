import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/features/settings/settings_screen.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

/// G10 — 설정 화면의 라디오 그룹 라벨. 화면에 보이는 섹션 제목과 같은
/// 문구가 그룹 노드에 붙고, 제목 텍스트 노드는 중복 낭독에서 빠진다.
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

  testWidgets('단위·목표 범위 그룹이 보이는 제목을 라벨로 갖는다',
      (tester) async {
    final handle = tester.ensureSemantics();

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

    // 그룹 라벨은 화면에 보이는 제목 그대로 — 새 l10n 키가 없다.
    expect(find.bySemanticsLabel(RegExp('Display unit')), findsOneWidget);

    // 목표 범위 섹션은 화면 아래쪽 — 뷰포트 밖 자식은 만들어지지 않는다.
    await tester.drag(find.byType(ListView), const Offset(0, -1200));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.bySemanticsLabel(RegExp('Target range')), findsOneWidget);
    // 라디오 선택 상태는 네이티브 낭독에 맡긴다 — 여기서 덮지 않는다.

    handle.dispose();
    await unmount(tester);
  });
}
