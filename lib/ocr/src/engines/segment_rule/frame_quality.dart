import 'dart:typed_data';

import 'gray_image.dart';

class FrameQuality {
  const FrameQuality({
    required this.blurScore,
    required this.rejected,
    this.glareScore,
    this.reason,
  });

  /// 라플라시안 응답의 분산. 클수록 또렷하다.
  final double blurScore;

  /// 포화 픽셀 최대 클러스터의 ROI 면적 비율. 클수록 반사광이 크다.
  final double? glareScore;

  final bool rejected;

  final String? reason;
}

/// 해독 전에 프레임을 거른다.
///
/// 흐릿한 프레임을 해독하면 세그먼트 경계가 뭉개져 그럴듯한 오답이 나오고,
/// 그 오답이 시간 투표에 섞여 들어가 전체를 오염시킨다. 읽지 않고 버리는
/// 편이 항상 낫다 — 다음 프레임은 곧바로 온다. 반사광도 같은 이유로 거른다:
/// 포화된 하이라이트는 획을 지워놓고도 나머지 획만으로 그럴듯한 숫자를
/// 만들 수 있다(8 → 6 같은 형태).
abstract final class FrameQualityGate {
  /// 이 값 미만이면 초점이 맞지 않은 것으로 본다.
  ///
  /// 라플라시안 분산의 절대 기준은 해상도와 대비에 따라 달라지므로, 실촬
  /// 골든셋을 모은 뒤 재보정해야 하는 값이다(현재는 보수적 초기값).
  static const double minBlurScore = 60;

  /// 포화 클러스터가 ROI 의 이 비율(0~1)을 넘으면 반사광으로 거른다.
  ///
  /// 숫자 한 자를 덮는 스페큘러 블롭이 전형적으로 ROI 의 수 % 를 차지한다는
  /// 관측에서 보수적으로 잡은 초기값이다. 밝은 백라이트 LCD 를 정상 프레임으로
  /// 놓아 주는 쪽(오탐 낮춤)이 반대급부보다 안전하다 — 놓친 프레임은 프레임
  /// 합의가 다시 잡을 기회가 있지만, 정상 프레임을 거절하면 스캔이 멈춘다.
  /// minBlurScore 와 마찬가지로 골든셋 확보 후 재보정 대상이다.
  static const double maxGlareClusterRatio = 0.02;

  /// 포화로 보는 밝기. 249 이하의 밝은 표시는 정상적인 백라이트로 둔다.
  static const int saturatedAt = 250;

  static FrameQuality evaluate(
    GrayImage image, {
    double blurThreshold = minBlurScore,
    double glareThreshold = maxGlareClusterRatio,
  }) {
    final score = laplacianVariance(image);
    if (score < blurThreshold) {
      return FrameQuality(
        blurScore: score,
        rejected: true,
        reason: '초점이 흐립니다 (${score.toStringAsFixed(1)})',
      );
    }

    final glare = largestSaturatedClusterRatio(image);
    if (glare > glareThreshold) {
      return FrameQuality(
        blurScore: score,
        glareScore: glare,
        rejected: true,
        reason: '반사광이 표시를 가립니다 (${(100 * glare).toStringAsFixed(1)}%)',
      );
    }
    return FrameQuality(
      blurScore: score,
      glareScore: glare,
      rejected: false,
    );
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

  /// 포화 픽셀(≥ [saturatedAt])의 4-연결 클러스터 중 가장 큰 것의 ROI 면적 비율.
  ///
  /// 점 하나짜리 노이즈와 달리, 반사광은 덩어리로 붙는다 — 그래서 개수가
  /// 아니라 **최대 클러스터 크기**를 잰다. 밝은 픽셀이 흩어져만 있으면(백라이트
  /// 그레인) 클러스터는 자라지 않는다.
  static double largestSaturatedClusterRatio(
    GrayImage image, {
    int saturatedAt = FrameQualityGate.saturatedAt,
  }) {
    if (image.width == 0 || image.height == 0) return 0;

    final visited = Uint8List(image.length);
    final stack = <int>[];
    var largest = 0;

    void push(int index) {
      if (visited[index] == 0 && image.pixels[index] >= saturatedAt) {
        visited[index] = 1;
        stack.add(index);
      }
    }

    for (var start = 0; start < image.length; start++) {
      if (visited[start] != 0 || image.pixels[start] < saturatedAt) continue;
      visited[start] = 1;
      stack.add(start);

      var size = 0;
      while (stack.isNotEmpty) {
        final i = stack.removeLast();
        size++;
        final x = i % image.width;
        if (x > 0) push(i - 1);
        if (x < image.width - 1) push(i + 1);
        if (i >= image.width) push(i - image.width);
        if (i + image.width < image.length) push(i + image.width);
      }
      if (size > largest) largest = size;
    }

    return largest / image.length;
  }
}
