import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/app.dart';

void main() {
  testWidgets('앱이 뜨고 4개 탭과 스캔 진입점이 보인다', (tester) async {
    await tester.pumpWidget(const SugarScanApp());
    await tester.pumpAndSettle();

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationDestination), findsNWidgets(4));
    expect(find.byType(FloatingActionButton), findsOneWidget);
  });

  testWidgets('의료 면책 문구가 홈에 노출된다', (tester) async {
    await tester.pumpWidget(const SugarScanApp());
    await tester.pumpAndSettle();

    // 규제 대응상 상시 노출이 요구되는 문구다. 화면 개편으로 사라지면
    // 이 테스트가 먼저 깨져야 한다.
    expect(
      find.textContaining('healthcare professional'),
      findsOneWidget,
    );
  });

  testWidgets('카메라를 쓸 수 없어도 수동 입력 경로는 남는다', (tester) async {
    await tester.pumpWidget(const SugarScanApp());
    await tester.pumpAndSettle();

    await tester.tap(find.byType(FloatingActionButton));
    // pumpAndSettle 을 쓰지 않는다. 카메라가 없는 테스트 환경에서는 초기화
    // 진행 표시기가 계속 돌아 영원히 정착하지 않는다. 대신 준비 타임아웃이
    // 지나가도록 시계를 넘긴다.
    await tester.pump();
    await tester.pump(const Duration(seconds: 8));

    // 카메라가 응답하지 않으면 도는 표시기를 걷어내고 스캔 불가를 알린다.
    expect(find.byType(CircularProgressIndicator), findsNothing);
    // OCR 이 어떤 상태든 사용자는 항상 기록을 남길 수 있어야 한다.
    expect(find.text('Enter manually'), findsOneWidget);
  });
}
