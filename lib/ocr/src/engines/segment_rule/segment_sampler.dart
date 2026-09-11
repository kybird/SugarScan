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

  /// 셀 하나를 샘플링한다.
  ///
  /// [normalizeToInk] 가 true 면 세그먼트 기하의 기준을 셀 전체가 아니라
  /// **셀 안 전경(잉크)의 경계 상자**로 옮긴다 — 셀 세로 범위가 숫자가 아니라
  /// ROI 전체 높이일 때 A·D 박스가 여백을 재 `0`→`H`·`8`→`H` 를 낸다는
  /// G15 의 발견에 대한 대응이다. 경계 상자 높이가 셀 높이의 40% 미만이거나
  /// 폭이 95% 초과면 정규화하지 않고 셀 기준 그대로 둔다(숫자가 아니거나
  /// 이웃 자릿수가 걸쳐 든 것). **기본값은 false 다** — 켜는 결정은 사람이
  /// 한다(G19).
  static CellSample sample(
    BinaryLcd lcd,
    NormalizedRect cell,
    SegmentGeometry geometry, {
    bool normalizeToInk = false,
  }) {
    var cellLeft = cell.left * lcd.width;
    var cellTop = cell.top * lcd.height;
    var cellWidth = cell.width * lcd.width;
    var cellHeight = cell.height * lcd.height;

    if (normalizeToInk) {
      final ink = _inkBounds(lcd, cellLeft, cellTop, cellWidth, cellHeight);
      if (ink != null) {
        final w = ink.$3;
        final h = ink.$4;
        // G19 규칙 — 두 걸러냄이 있다. 높이 40% 미만은 숫자가 아닐 가능성이
        // 높고(스펙 지정값), 폭 95% 초과는 이웃 자릿수가 걸쳐 든 것이다.
        // 둘 다 해당하지 않을 때만 기하의 기준을 셀에서 잉크 경계 상자로 옮긴다.
        if (h >= 0.40 * cellHeight && w <= 0.95 * cellWidth) {
          cellLeft = ink.$1 - 0.02 * w;
          cellTop = ink.$2 - 0.02 * h;
          cellWidth = w * 1.04;
          cellHeight = h * 1.04;
        }
      }
    }

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

  /// 셀 픽셀 영역 안의 전경 픽셀 경계 상자. (left, top, width, height).
  ///
  /// 전경이 한 픽셀도 없으면 null — 호출부는 기존 경로(셀 전체 기준)로
  /// 떨어진다. 잉크 정규화([sample] 의 `normalizeToInk`)의 입력으로만 쓴다.
  static (double, double, double, double)? _inkBounds(
    BinaryLcd lcd,
    double cellLeft,
    double cellTop,
    double cellWidth,
    double cellHeight,
  ) {
    final x0 = cellLeft.round().clamp(0, lcd.width - 1);
    final y0 = cellTop.round().clamp(0, lcd.height - 1);
    final x1 = (cellLeft + cellWidth).round().clamp(x0 + 1, lcd.width);
    final y1 = (cellTop + cellHeight).round().clamp(y0 + 1, lcd.height);

    var minX = -1;
    var minY = -1;
    var maxX = -1;
    var maxY = -1;
    for (var y = y0; y < y1; y++) {
      final rowStart = y * lcd.width;
      for (var x = x0; x < x1; x++) {
        if (lcd.foreground[rowStart + x] == 1) {
          if (minX < 0 || x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (minY < 0) minY = y;
          if (y > maxY) maxY = y;
        }
      }
    }
    if (minX < 0) return null;
    return (minX.toDouble(), minY.toDouble(),
        (maxX - minX + 1).toDouble(), (maxY - minY + 1).toDouble());
  }

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
