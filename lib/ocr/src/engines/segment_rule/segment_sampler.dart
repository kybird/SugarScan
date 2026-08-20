import '../../engine/ocr_frame.dart';
import 'lcd_binarizer.dart';
import 'segment_geometry.dart';
import 'segment_patterns.dart';

/// 셀 하나에서 읽어낸 원시 측정값.
class CellSample {
  const CellSample({
    required this.bits,
    required this.segmentRatios,
    required this.decimalRatio,
    required this.margin,
  });

  /// A~G 비트열. [Seg] 의 순서를 따른다.
  final int bits;

  /// 세그먼트별 전경 픽셀 비율(0~1).
  final List<double> segmentRatios;

  final double decimalRatio;

  /// 0~1. 가장 애매했던 세그먼트가 판정 경계에서 얼마나 떨어져 있었는지.
  ///
  /// 평균이 아니라 **최솟값**을 쓴다. 세그먼트 하나만 경계에 걸쳐 있어도
  /// 그 자리 숫자 전체가 바뀔 수 있으므로, 가장 약한 고리가 곧 이 셀의
  /// 신뢰도다.
  final double margin;
}

abstract final class SegmentSampler {
  /// 세그먼트를 켜진 것으로 볼 전경 비율.
  static const double onRatio = 0.5;

  /// 소수점으로 볼 전경 비율.
  ///
  /// 세그먼트보다 낮게 잡는다. 소수점은 작고 둥글어서 사각형 샘플 영역을
  /// 다 채우지 못하는 것이 정상이다.
  static const double decimalOnRatio = 0.35;

  static CellSample sample(
    BinaryLcd lcd,
    NormalizedRect cell,
    SegmentGeometry geometry,
  ) {
    final cellLeft = cell.left * lcd.width;
    final cellTop = cell.top * lcd.height;
    final cellWidth = cell.width * lcd.width;
    final cellHeight = cell.height * lcd.height;

    var bits = 0;
    var minMargin = 1.0;
    final ratios = <double>[];

    for (var i = 0; i < Seg.count; i++) {
      final ratio = _foregroundRatio(
        lcd,
        geometry.segments[i],
        cellLeft,
        cellTop,
        cellWidth,
        cellHeight,
      );
      ratios.add(ratio);

      if (ratio >= onRatio) bits |= Seg.ordered[i];

      // 경계(onRatio)에서 얼마나 떨어졌는지를 0~1 로 정규화.
      final distance = (ratio - onRatio).abs();
      final normalized = (distance / onRatio).clamp(0.0, 1.0);
      if (normalized < minMargin) minMargin = normalized;
    }

    final decimalRatio = _foregroundRatio(
      lcd,
      geometry.decimalPoint,
      cellLeft,
      cellTop,
      cellWidth,
      cellHeight,
    );

    return CellSample(
      bits: bits,
      segmentRatios: ratios,
      decimalRatio: decimalRatio,
      margin: minMargin,
    );
  }

  static bool hasDecimalPoint(CellSample sample) =>
      sample.decimalRatio >= decimalOnRatio;

  static double _foregroundRatio(
    BinaryLcd lcd,
    SegmentBox box,
    double cellLeft,
    double cellTop,
    double cellWidth,
    double cellHeight,
  ) {
    final left = (cellLeft + box.left * cellWidth).round();
    final top = (cellTop + box.top * cellHeight).round();
    final right = (cellLeft + box.right * cellWidth).round();
    final bottom = (cellTop + box.bottom * cellHeight).round();

    final x0 = left.clamp(0, lcd.width - 1);
    final y0 = top.clamp(0, lcd.height - 1);
    final x1 = right.clamp(x0 + 1, lcd.width);
    final y1 = bottom.clamp(y0 + 1, lcd.height);

    var on = 0;
    var total = 0;
    for (var y = y0; y < y1; y++) {
      final rowStart = y * lcd.width;
      for (var x = x0; x < x1; x++) {
        total++;
        if (lcd.foreground[rowStart + x] == 1) on++;
      }
    }
    return total == 0 ? 0 : on / total;
  }
}
