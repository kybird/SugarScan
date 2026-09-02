/// 카메라 프레임 스트림에 추론을 물릴 때의 유량 제어.
///
/// 카메라는 30fps 로 프레임을 밀어 넣지만 추론은 프레임당 수십~수백 ms 가
/// 걸린다. 큐에 쌓기 시작하면 화면에 보이는 것보다 한참 과거의 프레임을 읽게
/// 되어 체감 지연이 오히려 커진다. 그래서 **동시에 처리 중인 프레임은 항상 1개**로
/// 두고 나머지는 버린다. 버려진 프레임은 손실이 아니다 — 바로 다음 프레임이 온다.
class FrameThrottler {
  FrameThrottler();

  bool _busy = false;
  int _dropped = 0;
  int _processed = 0;

  bool get isBusy => _busy;
  int get droppedFrames => _dropped;
  int get processedFrames => _processed;

  /// 유휴 상태면 [task] 를 실행하고 결과를 돌려준다.
  /// 이미 처리 중이면 프레임을 버리고 null 을 돌려준다.
  Future<T?> run<T>(Future<T> Function() task) async {
    if (_busy) {
      _dropped++;
      return null;
    }
    _busy = true;
    try {
      final result = await task();
      _processed++;
      return result;
    } finally {
      _busy = false;
    }
  }

  /// 통계만 되돌린다. **진행 중인 작업 잠금은 풀지 않는다.**
  ///
  /// `_busy` 를 강제로 내리면 아직 돌고 있는 추론과 새 추론이 겹쳐, 엔진이
  /// 재진입 가능한지에 제품이 의존하게 된다(TFLite 인터프리터처럼 아닌 것도
  /// 있다). 잠금은 그 작업 자신이 `finally` 에서 푼다 — 스캔을 다시 시작한
  /// 직후 몇 프레임이 버려지는 것이 옳은 동작이다.
  void reset() {
    _dropped = 0;
    _processed = 0;
  }
}
