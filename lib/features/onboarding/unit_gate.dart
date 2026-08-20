import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import 'unit_onboarding_screen.dart';

/// 표시 단위가 확인되기 전에는 앱의 나머지를 막는다.
///
/// 라우터 위쪽(`MaterialApp.router` 의 `builder`)에 두어 **모든 경로**를 덮는다.
/// 대시보드에만 걸면 스캔 화면으로 직접 들어가는 경로가 뚫린다.
class UnitGate extends ConsumerWidget {
  const UnitGate({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preference = ref.watch(unitPreferenceProvider);

    return preference.when(
      loading: () => const _Splash(),
      // 설정을 못 읽는다고 앱을 못 쓰게 만들지 않는다. 확인 화면을 띄우면
      // 사용자가 답하고 다시 저장을 시도할 수 있다.
      error: (_, _) => const UnitOnboardingScreen(),
      data: (value) => value != null && value.confirmedByUser
          ? child
          : const UnitOnboardingScreen(),
    );
  }
}

class _Splash extends StatelessWidget {
  const _Splash();

  @override
  Widget build(BuildContext context) {
    return const ColoredBox(
      color: Color(0xFF101214),
      child: Center(child: CircularProgressIndicator()),
    );
  }
}
