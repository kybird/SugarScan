import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/app.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/local/database.dart';
import 'package:sugarscan/data/repositories/settings_repository.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';

void main() {
  late AppDatabase db;

  setUp(() async {
    db = AppDatabase(NativeDatabase.memory());
    // 표시 단위 확인 게이트가 앱 전체를 막는다. 대부분의 테스트는 그 뒤를
    // 보려는 것이므로 미리 확인된 상태로 시작한다.
    await SettingsRepository(database: db).confirmUnit(GlucoseUnit.mgdl);
  });
  tearDown(() => db.close());

  /// 실제 DB 파일 대신 메모리 DB 를 물린다. 프로바이더가 주입 가능해야
  /// 화면 테스트가 플랫폼 플러그인 없이 돌아간다.
  Widget app() => ProviderScope(
        overrides: [databaseProvider.overrideWithValue(db)],
        child: const SugarScanApp(),
      );

  /// `pumpAndSettle` 을 쓰지 않는다.
  ///
  /// 이 앱에는 무한히 도는 진행 표시기가 여럿 있다(카메라 준비, 스트림 첫
  /// 방출 대기). 정착을 기다리면 테스트가 영원히 멈춘다. 대신 정해진 만큼만
  /// 시계를 넘긴다.
  Future<void> settle(WidgetTester tester) async {
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));
  }

  /// 테스트 본문 안에서 위젯 트리를 내린다.
  ///
  /// Drift 의 스트림 쿼리는 구독이 끊길 때 정리 타이머를 하나 남긴다. 트리가
  /// 테스트 종료 후에 해제되면 그 타이머가 미처리로 남아 테스트가 실패한다.
  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    // 인자 없는 pump() 는 시계를 전혀 진전시키지 않아 Duration.zero 타이머가
    // 실행되지 않는다. 아주 짧게라도 시계를 넘겨야 정리 타이머가 소진된다.
    await tester.pump(const Duration(milliseconds: 100));
  }

  testWidgets('단위를 확인하기 전에는 앱의 나머지가 막힌다', (tester) async {
    // 단위 확인 전에 기록이 저장되면 10~50 구간에서 저혈당이 고혈당으로
    // 뒤집혀 남는다. 게이트가 그 경로를 원천 차단한다.
    final fresh = AppDatabase(NativeDatabase.memory());
    addTearDown(fresh.close);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [databaseProvider.overrideWithValue(fresh)],
        child: const SugarScanApp(),
      ),
    );
    await settle(tester);

    expect(find.textContaining('Which unit'), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
    expect(find.byType(FloatingActionButton), findsNothing);

    await unmount(tester);
  });

  testWidgets('단위를 고르면 게이트가 열린다', (tester) async {
    final fresh = AppDatabase(NativeDatabase.memory());
    addTearDown(fresh.close);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [databaseProvider.overrideWithValue(fresh)],
        child: const SugarScanApp(),
      ),
    );
    await settle(tester);

    await tester.tap(find.text('Continue'));
    await settle(tester);

    expect(find.byType(NavigationBar), findsOneWidget);

    await unmount(tester);
  });

  testWidgets('앱이 뜨고 4개 탭과 스캔 진입점이 보인다', (tester) async {
    await tester.pumpWidget(app());
    await settle(tester);

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationDestination), findsNWidgets(4));
    expect(find.byType(FloatingActionButton), findsOneWidget);

    await unmount(tester);
  });

  testWidgets('의료 면책 문구가 홈에 노출된다', (tester) async {
    await tester.pumpWidget(app());
    await settle(tester);

    // 규제 대응상 상시 노출이 요구되는 문구다. 화면 개편으로 사라지면
    // 이 테스트가 먼저 깨져야 한다.
    expect(find.textContaining('healthcare professional'), findsOneWidget);

    await unmount(tester);
  });

  testWidgets('기록이 없으면 빈 상태를 안내한다', (tester) async {
    await tester.pumpWidget(app());
    await settle(tester);

    expect(find.textContaining('No readings yet'), findsWidgets);

    await unmount(tester);
  });

  testWidgets('설정에서 표시 단위를 바꿀 수 있다', (tester) async {
    await tester.pumpWidget(app());
    await settle(tester);

    await tester.tap(find.text('Settings'));
    await settle(tester);

    expect(find.text('mg/dL'), findsWidgets);
    expect(find.text('mmol/L'), findsWidgets);

    await unmount(tester);
  });

  testWidgets('기록 탭으로 이동한다', (tester) async {
    await tester.pumpWidget(app());
    await settle(tester);

    await tester.tap(find.text('History'));
    await settle(tester);

    expect(find.widgetWithText(AppBar, 'History'), findsOneWidget);

    await unmount(tester);
  });

  testWidgets('카메라를 쓸 수 없어도 수동 입력 경로는 남는다', (tester) async {
    await tester.pumpWidget(app());
    await settle(tester);

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pump();
    // 카메라 준비 타임아웃이 지나가도록 시계를 넘긴다.
    await tester.pump(const Duration(seconds: 8));

    // 카메라가 응답하지 않으면 도는 표시기를 걷어내고 스캔 불가를 알린다.
    expect(find.byType(CircularProgressIndicator), findsNothing);
    // OCR 이 어떤 상태든 사용자는 항상 기록을 남길 수 있어야 한다.
    expect(find.text('Enter manually'), findsOneWidget);

    await unmount(tester);
  });
}
