import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import 'sign_in_screen.dart';

/// 로그인 전에는 앱의 나머지를 막는다.
///
/// 막는 경우는 하나뿐이다: 서버가 설정된 빌드에서, 세션이 없고, 이 기기에서
/// 로그인한 적도 없을 때. 판정 근거는 [authGateProvider] 에 있다.
///
/// **세션 만료로는 막지 않는다.** CLAUDE.md 의 "사용자가 기록을 남기지 못하는
/// 상태를 만들지 않는다"를 지키기 위해서다. 리프레시 토큰이 끊긴 채 비행기에
/// 탄 사람도 측정값을 남길 수 있어야 하고, 그 기록은 세션이 돌아올 때 아웃박스가
/// 실어 나른다.
class AuthGate extends ConsumerWidget {
  const AuthGate({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return switch (ref.watch(authGateProvider)) {
      AuthGateStatus.loading => const _Splash(),
      AuthGateStatus.allowed => child,
      AuthGateStatus.requireSignIn => const SignInScreen(),
    };
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
