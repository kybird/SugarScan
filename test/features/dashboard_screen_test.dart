import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/features/dashboard/dashboard_screen.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

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

  // 대시보드의 최근 기록 목록이 로컬 DB 읽기에 실패하면 안내 문구를 보여 준다.
  // Dart 예외 객체의 원문이 그대로 화면에 나가지 않는지가 이 테스트의 핵심이다.
  testWidgets('기록 조회가 실패하면 번역된 안내 문구만 보여 준다', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          databaseProvider.overrideWithValue(db),
          recentReadingsProvider.overrideWith(
            (ref) => Stream<List<GlucoseReading>>.error(StateError('boom')),
          ),
        ],
        child: const MaterialApp(
          localizationsDelegates: [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: DashboardScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text("Couldn't load your readings."), findsOneWidget);
    expect(find.textContaining('boom'), findsNothing);

    await unmount(tester);
  });
}
