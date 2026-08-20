import '../../engine/ocr_frame.dart';
import 'segment_geometry.dart';

/// 혈당계 한 기종의 표시 레이아웃.
///
/// 알고리즘과 기종별 좌표를 분리한다. 기종이 늘어날 때 코드가 아니라 데이터가
/// 늘어나야 하고, 새 기종 지원이 "숫자 몇 개 추가"로 끝나야 한다.
class MeterProfile {
  const MeterProfile({
    required this.id,
    required this.digitCells,
    this.geometry = SegmentGeometry.standard,
    this.forceDarkOnLight,
  });

  final String id;

  /// 왼쪽부터 오른쪽 순서. 좌표는 ROI 에 대한 비율(0~1)이다.
  ///
  /// 원근 보정 이후의 정규화 좌표를 쓴다. 픽셀 좌표로 두면 해상도가 바뀔
  /// 때마다 프로파일을 다시 만들어야 한다.
  final List<NormalizedRect> digitCells;

  final SegmentGeometry geometry;

  /// 극성을 강제한다. null 이면 이진화기가 면적으로 자동 판정한다.
  /// 배경보다 획이 넓은 특이한 표시에서만 지정한다.
  final bool? forceDarkOnLight;

  int get digitCount => digitCells.length;

  /// 자릿수를 균등 배치한 기본 프로파일.
  ///
  /// 기종 프로파일이 아직 없을 때의 출발점이자, 사용자가 가이드 박스에 화면을
  /// 맞춰 주는 경우의 기본값이다.
  factory MeterProfile.uniform({
    String id = 'uniform',
    int digitCount = 4,
    double gapRatio = 0.03,
    SegmentGeometry geometry = SegmentGeometry.standard,
  }) {
    assert(digitCount > 0);
    assert(gapRatio >= 0 && gapRatio < 1);

    // 셀 사이 간격을 두는 이유: 셀을 딱 붙여 나누면 이웃 자릿수의 세로 획이
    // 샘플 영역 가장자리에 걸쳐 들어와 B·E 판정을 흔든다.
    final totalGap = gapRatio * (digitCount - 1);
    final cellWidth = (1.0 - totalGap) / digitCount;

    return MeterProfile(
      id: id,
      geometry: geometry,
      digitCells: [
        for (var i = 0; i < digitCount; i++)
          NormalizedRect(
            left: i * (cellWidth + gapRatio),
            top: 0,
            width: cellWidth,
            height: 1,
          ),
      ],
    );
  }
}
