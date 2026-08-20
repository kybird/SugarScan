// ignore_for_file: prefer_initializing_formals

import 'dart:async';

import 'sync_engine.dart';

/// 동기화를 언제 돌릴지 결정한다.
///
/// 엔진은 "한 회차를 어떻게 도는가"만 안다. 언제 도는지는 여기가 정한다.
/// 촉발 지점이 여럿(앱 시작, 로그인, 네트워크 복귀, 기록 저장)이라 그 결정을
/// 한곳에 모아 두지 않으면 같은 회차가 여러 번 겹쳐 돈다.
class SyncScheduler {
  SyncScheduler({
    required Future<SyncReport> Function() run,
    Duration debounce = const Duration(seconds: 2),
  })  : _run0 = run,
        _debounce = debounce;

  /// 한 회차를 도는 함수. 보통 `syncEngine.syncOnce`.
  ///
  /// 엔진 전체가 아니라 함수만 받는다. 스케줄러가 아는 것은 "돌린다"뿐이고,
  /// 그 이상을 알면 테스트가 엔진을 통째로 흉내 내야 한다.
  final Future<SyncReport> Function() _run0;
  final Duration _debounce;

  Timer? _timer;
  Future<SyncReport>? _running;

  /// 다시 돌아야 한다는 요청이 실행 중에 들어왔는지.
  bool _rerun = false;

  bool _disposed = false;

  final _reports = StreamController<SyncReport>.broadcast();

  /// 마지막 회차 결과. 화면이 "대기 중 n건" 같은 것을 보여줄 때 쓴다.
  Stream<SyncReport> get reports => _reports.stream;

  SyncReport? _last;
  SyncReport? get lastReport => _last;

  /// 잠시 뒤 한 번 돌린다. 짧은 사이에 여러 번 불러도 한 번만 돈다.
  ///
  /// 기록을 연달아 세 건 저장하면 촉발도 세 번 온다. 그때마다 서버로 붙으면
  /// 배치의 의미가 없다.
  void schedule() {
    if (_disposed) return;

    _timer?.cancel();
    _timer = Timer(_debounce, () => unawaited(now()));
  }

  /// 지금 한 회차 돌린다.
  ///
  /// 이미 도는 중이면 **새로 시작하지 않고** 끝나기를 기다린 뒤 한 번 더 돈다.
  /// 두 회차가 겹치면 같은 아웃박스 항목을 두 번 보내고, 뒤늦게 끝난 쪽이
  /// 이미 지워진 큐를 다시 지우려 든다.
  Future<SyncReport> now() {
    if (_disposed) {
      return Future.value(const SyncReport(outcome: SyncOutcome.failed));
    }

    final running = _running;
    if (running != null) {
      _rerun = true;
      return running;
    }

    final future = _run();
    _running = future;
    return future;
  }

  Future<SyncReport> _run() async {
    try {
      var report = await _run0();

      // 실행 중에 들어온 요청을 흘리지 않는다. 방금 저장한 기록이 다음 촉발이
      // 올 때까지 안 올라가는 상태를 만들지 않기 위해서다.
      while (_rerun && !_disposed) {
        _rerun = false;
        report = await _run0();
      }

      _last = report;
      if (!_disposed) _reports.add(report);
      return report;
    } finally {
      _running = null;
      _rerun = false;
    }
  }

  void dispose() {
    _disposed = true;
    _timer?.cancel();
    _reports.close();
  }
}
