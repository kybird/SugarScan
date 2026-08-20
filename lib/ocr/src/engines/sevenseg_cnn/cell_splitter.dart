/// ROI 안에서 자릿수 하나가 차지하는 가로 구간.
class DigitCell {
  const DigitCell({required this.left, required this.width});

  final int left;
  final int width;

  int get right => left + width;

  @override
  String toString() => 'DigitCell($left, w=$width)';
}

/// ROI 를 자릿수만큼 등분한다.
///
/// 참조 구현(Kazuhito00/7segment-display-reader)과 같은 방식이다. 세그먼트
/// 사이 여백을 찾아 자르는 투영(projection) 방식이 더 똑똑해 보이지만, 혈당계는
/// 자릿수가 고정된 고정폭 LCD 라 등분이 더 안정적이다. 투영 방식은 `1` 처럼
/// 폭이 좁은 숫자나 흐려진 세그먼트에서 경계를 잘못 잡는다.
///
/// 앞자리 공백(`  95`)은 자르지 않고 그대로 넘긴다. 모델에 "표시 없음" 클래스가
/// 있어서 빈 셀을 스스로 걸러내기 때문이다.
List<DigitCell> splitIntoCells(int roiWidth, int digitCount) {
  if (roiWidth <= 0 || digitCount <= 0) return const [];
  if (digitCount > roiWidth) return const [];

  final base = roiWidth ~/ digitCount;
  // 나누어떨어지지 않는 픽셀은 앞쪽 셀부터 1픽셀씩 나눠 갖는다.
  // 마지막 셀에 몰아주면 그 자리만 계속 넓어져 인식이 치우친다.
  final remainder = roiWidth % digitCount;

  final cells = <DigitCell>[];
  var cursor = 0;
  for (var i = 0; i < digitCount; i++) {
    final width = base + (i < remainder ? 1 : 0);
    cells.add(DigitCell(left: cursor, width: width));
    cursor += width;
  }
  return cells;
}
