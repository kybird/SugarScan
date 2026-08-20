import 'dart:collection';

class StabilizerObservation {
  const StabilizerObservation(this.value, this.confidence);

  /// 정규화·검증을 통과한 값 문자열(예: `138`).
  final String value;
  final double confidence;
}

sealed class StabilizerOutcome {
  const StabilizerOutcome();
}

final class StabilizerPending extends StabilizerOutcome {
  const StabilizerPending({
    required this.currentValue,
    required this.consecutiveCount,
    required this.requiredCount,
  });

  final String? currentValue;
  final int consecutiveCount;
  final int requiredCount;

  double get progress =>
      requiredCount == 0 ? 0 : consecutiveCount / requiredCount;
}

final class StabilizerConfirmed extends StabilizerOutcome {
  const StabilizerConfirmed({
    required this.value,
    required this.averageConfidence,
    required this.frameCount,
  });

  final String value;
  final double averageConfidence;
  final int frameCount;
}

/// 프레임 간 합의로 단일 프레임 오인식을 걸러낸다.
///
/// 이 모듈이 앱에 값을 넘기기 전에 반드시 통과해야 하는 마지막 관문이다. 엔진이
/// 한 프레임에서 `95` 를 `195` 로 잘못 읽어도, 연속된 프레임이 같은 오답을
/// 반복하지 않는 한 확정되지 않는다. 덕분에 앱은 확정된 값을 그대로 신뢰할 수
/// 있고, 엔진 정확도가 완벽하지 않아도 제품이 성립한다.
class ReadingStabilizer {
  ReadingStabilizer({
    this.windowSize = 6,
    this.requiredConsecutive = 3,
    this.minAverageConfidence = 0.85,
  })  : assert(windowSize >= requiredConsecutive),
        assert(requiredConsecutive >= 1);

  final int windowSize;

  /// 같은 값이 연속으로 몇 번 나와야 확정할지.
  final int requiredConsecutive;

  /// 확정에 필요한 평균 확신도. 연속성만으로는 부족하다 —
  /// 엔진이 낮은 확신도로 같은 오답을 반복할 수 있다.
  final double minAverageConfidence;

  final Queue<StabilizerObservation> _window = Queue();

  int get observationCount => _window.length;

  StabilizerOutcome add(StabilizerObservation observation) {
    _window.addLast(observation);
    while (_window.length > windowSize) {
      _window.removeFirst();
    }

    if (_window.length < requiredConsecutive) {
      return StabilizerPending(
        currentValue: observation.value,
        consecutiveCount: _trailingRunLength(),
        requiredCount: requiredConsecutive,
      );
    }

    final tail = _window.toList().sublist(_window.length - requiredConsecutive);
    final allSame = tail.every((o) => o.value == tail.first.value);
    if (!allSame) {
      return StabilizerPending(
        currentValue: observation.value,
        consecutiveCount: _trailingRunLength(),
        requiredCount: requiredConsecutive,
      );
    }

    final avg =
        tail.map((o) => o.confidence).reduce((a, b) => a + b) / tail.length;
    if (avg < minAverageConfidence) {
      return StabilizerPending(
        currentValue: observation.value,
        consecutiveCount: tail.length,
        requiredCount: requiredConsecutive,
      );
    }

    return StabilizerConfirmed(
      value: tail.first.value,
      averageConfidence: avg,
      frameCount: tail.length,
    );
  }

  void reset() => _window.clear();

  int _trailingRunLength() {
    if (_window.isEmpty) return 0;
    final list = _window.toList();
    final last = list.last.value;
    var count = 0;
    for (var i = list.length - 1; i >= 0; i--) {
      if (list[i].value != last) break;
      count++;
    }
    return count;
  }
}
