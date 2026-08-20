import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'providers.dart';

/// 동기화를 촉발한다. 화면을 그리지 않고 자식을 그대로 통과시킨다.
///
/// 촉발 지점을 한곳에 모아 둔 이유: 흩어 두면 어떤 경로에서는 동기화가 영영
/// 안 걸리는 조합이 생기고, 그런 건 "가끔 안 올라간다"로만 보여서 재현이 어렵다.
///
/// 게이트 바깥에 둔다. 로그인 화면이나 단위 확인 화면에 머무는 동안에도
/// 이미 쌓인 것은 올라가야 한다.
class SyncRunner extends ConsumerStatefulWidget {
  const SyncRunner({super.key, required this.child});

  final Widget child;

  @override
  ConsumerState<SyncRunner> createState() => _SyncRunnerState();
}

class _SyncRunnerState extends ConsumerState<SyncRunner> {
  late final AppLifecycleListener _lifecycle;

  @override
  void initState() {
    super.initState();

    // 앱 시작. 로그인 전이면 엔진이 notSignedIn 으로 돌아 나오므로 여기서
    // 조건을 따로 걸지 않는다.
    WidgetsBinding.instance.addPostFrameCallback((_) => _schedule());

    // 포그라운드 복귀. 백그라운드에 있는 동안 네트워크가 돌아왔을 수 있다.
    _lifecycle = AppLifecycleListener(onResume: _schedule);
  }

  @override
  void dispose() {
    _lifecycle.dispose();
    super.dispose();
  }

  void _schedule() {
    if (mounted) ref.read(syncSchedulerProvider).schedule();
  }

  @override
  Widget build(BuildContext context) {
    // 로그인 직후. 로그인 전에 쌓아 둔 기록이 여기서 한꺼번에 올라간다.
    ref.listen(signedInProvider, (previous, next) {
      if (next.value == true && previous?.value != true) _schedule();
    });

    // 기록을 저장/수정/삭제할 때마다 큐가 늘어난다. 스케줄러가 디바운스하므로
    // 연달아 저장해도 서버에는 한 번만 붙는다.
    ref.listen(pendingSyncCountProvider, (previous, next) {
      if ((next.value ?? 0) > 0) _schedule();
    });

    return widget.child;
  }
}
