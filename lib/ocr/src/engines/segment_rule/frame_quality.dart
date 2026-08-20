import 'gray_image.dart';

class FrameQuality {
  const FrameQuality({
    required this.blurScore,
    required this.rejected,
    this.reason,
  });

  /// 라플라시안 응답의 분산. 클수록 또렷하다.
  final double blurScore;

  final bool rejected;
  final String? reason;
}

/// 해독 전에 프레임을 거른다.
///
/// 흐릿한 프레임을 해독하면 세그먼트 경계가 뭉개져 그럴듯한 오답이 나오고,
/// 그 오답이 시간 투표에 섞여 들어가 전체를 오염시킨다. 읽지 않고 버리는
/// 편이 항상 낫다 — 다음 프레임은 곧바로 온다.
abstract final class FrameQualityGate {
  /// 이 값 미만이면 초점이 맞지 않은 것으로 본다.
  ///
  /// 라플라시안 분산의 절대 기준은 해상도와 대비에 따라 달라지므로, 실촬
  /// 골든셋을 모은 뒤 재보정해야 하는 값이다(현재는 보수적 초기값).
  static const double minBlurScore = 60;

  static FrameQuality evaluate(
    GrayImage image, {
    double blurThreshold = minBlurScore,
  }) {
    final score = laplacianVariance(image);
    if (score < blurThreshold) {
      return FrameQuality(
        blurScore: score,
        rejected: true,
        reason: '초점이 흐립니다 (${score.toStringAsFixed(1)})',
      );
    }
    return FrameQuality(blurScore: score, rejected: false);
  }

  /// 3×3 라플라시안 커널 응답의 분산.
  ///
  /// ```
  ///  0  1  0
  ///  1 -4  1
  ///  0  1  0
  /// ```
  static double laplacianVariance(GrayImage image) {
    if (image.width < 3 || image.height < 3) return 0;

    var sum = 0.0;
    var sumSquares = 0.0;
    var count = 0;

    for (var y = 1; y < image.height - 1; y++) {
      for (var x = 1; x < image.width - 1; x++) {
        final response = image.at(x, y - 1) +
            image.at(x, y + 1) +
            image.at(x - 1, y) +
            image.at(x + 1, y) -
            4 * image.at(x, y);
        sum += response;
        sumSquares += response * response;
        count++;
      }
    }

    if (count == 0) return 0;
    final mean = sum / count;
    return (sumSquares / count) - (mean * mean);
  }
}
