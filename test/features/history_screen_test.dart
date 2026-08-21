import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/repositories/glucose_repository.dart';
import 'package:sugarscan/data/repositories/settings_repository.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/features/history/history_screen.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

void main() {
  late AppDatabase db;
  late GlucoseRepository repository;

  setUp(() async {
    db = AppDatabase(NativeDatabase.memory());
    repository = GlucoseRepository(
      database: db,
      resolveTzName: () async => 'Asia/Seoul',
    );
    await SettingsRepository(database: db).confirmUnit(GlucoseUnit.mgdl);
  });

  tearDown(() => db.close());

  Future<void> add(double value) {
    return repository.add(
      value: value,
      unit: GlucoseUnit.mgdl,
      tag: MeasurementTag.random,
      source: ReadingSource.manual,
    );
  }

  Future<void> pumpHistory(WidgetTester tester) async {
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
          home: HistoryScreen(),
        ),
      ),
    );

    // `pumpAndSettle` 을 쓰지 않는다. 정해진 만큼만 시계를 넘긴다.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 300));
  }

  /// 트리를 테스트 본문 안에서 내린다. 밖에서 해제되면 남은 타이머가
  /// 미처리로 잡힌다.
  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(milliseconds: 100));
  }

  // 되돌리기를 눌렀는데 아무 반응이 없으면, 사용자는 눌린 게 맞는지 확신하지
  // 못하고 같은 기록을 다시 입력한다. 목록이 돌아오는 것과 별개로 확인 문구가
  // 떠야 한다.
  testWidgets('삭제를 되돌리면 기록이 돌아오고 확인 문구를 띄운다', (tester) async {
    await add(137);

    await pumpHistory(tester);
    expect(find.text('137'), findsOneWidget);

    // 스와이프 삭제. Dismissible 은 endToStart — 오른쪽에서 왼쪽으로 민다.
    // 퇴장 → 높이 수축 → onDismissed → 비동기 삭제 → 스낵바 등장까지 프레임이
    // 여러 번 필요하다. 한 번에 크게 넘기면 중간 상태 전환이 건너뛰어지므로
    // 300ms 씩 여러 번 넘긴다.
    await tester.fling(find.text('137'), const Offset(-500, 0), 1000);
    await tester.pump();
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 300));
    }

    expect(find.text('137'), findsNothing);
    expect(find.text('Reading deleted'), findsOneWidget);

    await tester.tap(find.text('Undo'));
    await tester.pump();
    for (var i = 0; i < 5; i++) {
      await tester.pump(const Duration(milliseconds: 300));
    }

    expect(find.text('137'), findsOneWidget);
    expect(find.text('Reading restored'), findsOneWidget);

    // 스낵바의 자동 닫힘 타이머를 끝까지 보내고 나서 트리를 내린다. 남은
    // 타이머가 있으면 테스트가 "Timer is still pending" 으로 죽는다.
    await tester.pump(const Duration(seconds: 5));
    await tester.pump(const Duration(milliseconds: 300));

    await unmount(tester);
  });

  // 읽기 실패는 빈 목록과 다른 화면이다. 예외 원문을 그대로 보여 주면 번역되지
  // 않은 문장이 사용자에게 노출된다 — 원문은 로그로만 남는다.
  testWidgets('기록 조회가 실패하면 안내 문구를 보고 원문은 로그로 남긴다', (tester) async {
    final printed = <String>[];
    final original = debugPrint;
    debugPrint = (String? message, {int? wrapWidth}) {
      printed.add(message ?? '');
    };
    // flutter_test 는 테스트 끝에 foundation 디버그 변수가 원상태인지 검사한다.
    // addTearDown 으로 복원하면 검사보다 늦게 도니 본문 안에서 직접 되돌린다.
    try {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            databaseProvider.overrideWithValue(db),
            recentReadingsProvider.overrideWith(
              (ref) => Stream<List<GlucoseReading>>.error(
                StateError(
                    'SqliteException(11): database disk image is malformed'),
              ),
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
            home: HistoryScreen(),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.text("Couldn't load your readings."), findsOneWidget);
      // 원문은 화면에 없고 로그에 있다.
      expect(find.textContaining('SqliteException'), findsNothing);
      expect(
        printed.join('\n'),
        contains('database disk image is malformed'),
      );
      // 빈 상태 문구와 뭉개지지 않는다.
      expect(find.textContaining('No readings yet'), findsNothing);
    } finally {
      debugPrint = original;
    }

    await unmount(tester);
  });
}
