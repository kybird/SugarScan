import 'dart:math' as math;
import 'dart:typed_data';

/// CRNN 리더 출력(CTC logits)의 greedy 디코드 — 순수 계산.
///
/// 알고리즘은 학습 쪽 정본(reader_crnn.decode_greedy)과 같다: 프레임별
/// argmax → 연속 중복 제거 → blank 제거. 클래스 인덱스 0~9 가 곧 숫자
/// 값이라(charset 설계) argmax 를 그대로 글자로 쓴다.
///
/// 확신도는 글자가 튀어나온 프레임의 softmax 최대 확률이다. 안정화기가
/// 평균 0.85 를 요구하므로 확신도는 확률 척도여야 한다(logit 이면 안 된다).
final class CtcReading {
  const CtcReading(this.text, this.perCharConfidence);

  final String text;
  final List<double> perCharConfidence;

  /// 후보 전체의 확신도는 **가장 약한 자리**를 따른다(sevenseg_cnn 과 같은
  /// 이유 — 혈당값은 한 자리가 틀리면 값 전체가 틀린다).
  double get confidence => perCharConfidence.isEmpty
      ? 0
      : perCharConfidence.reduce(math.min);
}

abstract final class CrnnCtc {
  static const int timeSteps = 36; // 144/4
  static const int classCount = 11; // 0~9 + blank
  static const int blankIndex = 10;

  static CtcReading greedy(Float32List logits) {
    final text = StringBuffer();
    final confidences = <double>[];
    var prev = -1;
    for (var t = 0; t < timeSteps; t++) {
      final base = t * classCount;
      var k = 0;
      var best = logits[base];
      for (var c = 1; c < classCount; c++) {
        if (logits[base + c] > best) {
          best = logits[base + c];
          k = c;
        }
      }
      if (k != prev && k != blankIndex) {
        // softmax 최대 확률. 분자는 exp(best−best)=1 이므로 분수만으로 끝난다.
        var denominator = 0.0;
        for (var c = 0; c < classCount; c++) {
          denominator += math.exp(logits[base + c] - best);
        }
        text.write(k);
        confidences.add(1 / denominator);
      }
      prev = k;
    }
    return CtcReading(text.toString(), confidences);
  }
}
