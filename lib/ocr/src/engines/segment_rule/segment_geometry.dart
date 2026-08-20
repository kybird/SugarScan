/// 자릿수 셀 안에서 세그먼트 하나를 샘플링할 영역. 셀 크기에 대한 비율(0~1).
class SegmentBox {
  const SegmentBox({
    required this.centerX,
    required this.centerY,
    required this.halfWidth,
    required this.halfHeight,
  });

  final double centerX;
  final double centerY;
  final double halfWidth;
  final double halfHeight;

  double get left => centerX - halfWidth;
  double get top => centerY - halfHeight;
  double get right => centerX + halfWidth;
  double get bottom => centerY + halfHeight;
}

/// 세그먼트 7개의 샘플 영역과 소수점 영역.
///
/// 점 하나가 아니라 **영역**을 재는 이유: 한 점만 보면 반사 하이라이트나 죽은
/// 픽셀 하나에 판정이 통째로 뒤집힌다. 영역 안에서 전경 픽셀 비율을 세면
/// 그런 국소 잡음이 평균에 묻힌다.
class SegmentGeometry {
  const SegmentGeometry({
    required this.segments,
    required this.decimalPoint,
  });

  /// A, B, C, D, E, F, G 순서로 정확히 7개. `Seg.ordered` 와 같은 순서를 지킨다.
  ///
  /// 개수는 생성자에서 검사하지 않는다(const 표현식에서 `length` 를 볼 수 없다).
  /// 대신 테스트로 고정한다.
  final List<SegmentBox> segments;

  /// 소수점 후보 영역. 셀 오른쪽 아래.
  final SegmentBox decimalPoint;

  /// 일반적인 7-세그먼트 LCD 비율에 맞춘 기본값.
  ///
  /// 세로 획(B·C·E·F)은 좌우 끝에서 살짝 안쪽으로 들여 잡는다. 셀 경계에
  /// 딱 붙여 잡으면 이웃 자릿수의 획이 샘플 영역에 걸쳐 들어온다.
  static const SegmentGeometry standard = SegmentGeometry(
    segments: [
      // A — 위 가로
      SegmentBox(centerX: 0.50, centerY: 0.09, halfWidth: 0.20, halfHeight: 0.06),
      // B — 우상 세로
      SegmentBox(centerX: 0.84, centerY: 0.28, halfWidth: 0.07, halfHeight: 0.13),
      // C — 우하 세로
      SegmentBox(centerX: 0.84, centerY: 0.72, halfWidth: 0.07, halfHeight: 0.13),
      // D — 아래 가로
      SegmentBox(centerX: 0.50, centerY: 0.91, halfWidth: 0.20, halfHeight: 0.06),
      // E — 좌하 세로
      SegmentBox(centerX: 0.16, centerY: 0.72, halfWidth: 0.07, halfHeight: 0.13),
      // F — 좌상 세로
      SegmentBox(centerX: 0.16, centerY: 0.28, halfWidth: 0.07, halfHeight: 0.13),
      // G — 가운데 가로
      SegmentBox(centerX: 0.50, centerY: 0.50, halfWidth: 0.20, halfHeight: 0.06),
    ],
    // 소수점은 셀 오른쪽 아래 모서리. D 세그먼트와 겹치지 않도록 더 바깥에 둔다.
    decimalPoint:
        SegmentBox(centerX: 0.95, centerY: 0.93, halfWidth: 0.05, halfHeight: 0.05),
  );
}
