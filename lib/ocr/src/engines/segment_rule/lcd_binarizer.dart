import 'dart:typed_data';

import 'gray_image.dart';

/// 이진화 결과.
class BinaryLcd {
  const BinaryLcd({
    required this.foreground,
    required this.width,
    required this.height,
    required this.threshold,
    required this.darkOnLight,
    required this.separability,
    required this.foregroundRatio,
  });

  /// 1 = 켜진 세그먼트(전경), 0 = 배경.
  final Uint8List foreground;

  final int width;
  final int height;

  /// Otsu 가 고른 임계값.
  final int threshold;

  /// true 면 어두운 획 / 밝은 배경(반사형 LCD). false 면 백라이트 표시.
  final bool darkOnLight;

  /// 0~1. 전경과 배경이 얼마나 잘 갈라졌는지(정규화된 클래스 간 분산).
  ///
  /// 낮으면 애초에 두 덩어리로 나뉘지 않는 화면이라는 뜻이다. 이 값이 낮은
  /// 프레임을 그대로 해독하면 잡음에서 그럴듯한 숫자가 만들어진다.
  final double separability;

  /// 전경 픽셀 비율. 극단값이면 화면 전체가 날아갔거나 새까맣다는 신호다.
  final double foregroundRatio;

  bool isForeground(int x, int y) => foreground[y * width + x] == 1;
}

/// LCD 를 전경/배경으로 가른다.
///
/// 전역 고정 임계값(예: 128)을 쓰지 않는 이유: 휴대폰 카메라는 자동 노출로
/// 밝기를 계속 바꾼다. 같은 화면이 프레임마다 다른 밝기로 들어오므로 고정
/// 임계값은 첫 프레임에서만 맞는다. Otsu 는 매 프레임 히스토그램에서 임계값을
/// 다시 고르므로 노출이 흔들려도 같은 결과를 준다.
abstract final class LcdBinarizer {
  /// 전경으로 인정할 최대 면적 비율.
  ///
  /// 세그먼트는 화면의 일부만 차지한다. 절반을 넘으면 전경과 배경을 뒤집어
  /// 잡았다는 뜻이므로 극성 판정에 쓴다.
  static const double maxPlausibleForegroundRatio = 0.5;

  static BinaryLcd binarize(GrayImage image, {bool? forceDarkOnLight}) {
    final histogram = Int32List(256);
    for (final value in image.pixels) {
      histogram[value]++;
    }

    final total = image.length;
    final threshold = _otsu(histogram, total);
    final separability = _separability(histogram, total, threshold);

    // 임계값보다 어두운 픽셀 수. 세그먼트는 화면의 소수 면적이므로,
    // 적은 쪽을 전경으로 본다 — 반사형 LCD 든 백라이트 표시든 이 규칙 하나로
    // 극성이 자동으로 잡힌다.
    var darkCount = 0;
    for (var i = 0; i <= threshold; i++) {
      darkCount += histogram[i];
    }
    final darkOnLight = forceDarkOnLight ?? (darkCount <= total - darkCount);

    final foreground = Uint8List(total);
    var foregroundCount = 0;
    for (var i = 0; i < total; i++) {
      final isDark = image.pixels[i] <= threshold;
      final on = darkOnLight ? isDark : !isDark;
      if (on) {
        foreground[i] = 1;
        foregroundCount++;
      }
    }

    return BinaryLcd(
      foreground: foreground,
      width: image.width,
      height: image.height,
      threshold: threshold,
      darkOnLight: darkOnLight,
      separability: separability,
      foregroundRatio: total == 0 ? 0 : foregroundCount / total,
    );
  }

  /// Otsu 임계값. 클래스 간 분산을 최대로 만드는 경계를 고른다.
  static int _otsu(Int32List histogram, int total) {
    if (total == 0) return 127;

    var sum = 0.0;
    for (var i = 0; i < 256; i++) {
      sum += i * histogram[i];
    }

    var sumBackground = 0.0;
    var weightBackground = 0;
    var maxVariance = -1.0;
    var best = 127;

    for (var t = 0; t < 256; t++) {
      weightBackground += histogram[t];
      if (weightBackground == 0) continue;
      final weightForeground = total - weightBackground;
      if (weightForeground == 0) break;

      sumBackground += t * histogram[t];
      final meanBackground = sumBackground / weightBackground;
      final meanForeground = (sum - sumBackground) / weightForeground;
      final delta = meanBackground - meanForeground;
      final variance = weightBackground * weightForeground * delta * delta;

      if (variance > maxVariance) {
        maxVariance = variance;
        best = t;
      }
    }
    return best;
  }

  /// 0~1 로 정규화한 클래스 간 분산.
  static double _separability(Int32List histogram, int total, int threshold) {
    if (total == 0) return 0;

    var mean = 0.0;
    for (var i = 0; i < 256; i++) {
      mean += i * histogram[i];
    }
    mean /= total;

    var variance = 0.0;
    for (var i = 0; i < 256; i++) {
      final delta = i - mean;
      variance += delta * delta * histogram[i];
    }
    variance /= total;
    if (variance <= 0) return 0;

    var weightBackground = 0;
    var sumBackground = 0.0;
    for (var i = 0; i <= threshold; i++) {
      weightBackground += histogram[i];
      sumBackground += i * histogram[i];
    }
    final weightForeground = total - weightBackground;
    if (weightBackground == 0 || weightForeground == 0) return 0;

    final meanBackground = sumBackground / weightBackground;
    final meanForeground = (mean * total - sumBackground) / weightForeground;
    final delta = meanBackground - meanForeground;
    final between =
        (weightBackground / total) * (weightForeground / total) * delta * delta;

    return (between / variance).clamp(0.0, 1.0);
  }
}
