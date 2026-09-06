import 'dart:typed_data';

/// 엔진에 전달되는 이미지 바이트 배치.
///
/// Android(YUV) 와 iOS(BGRA) 의 카메라 프레임 포맷 차이를 여기서 흡수한다.
enum OcrImageFormat { nv21, yuv420, bgra8888, grayscale8, png, jpeg }

/// 0~1 로 정규화된 관심 영역.
///
/// 픽셀 좌표가 아니라 정규화 좌표를 쓰는 이유: 프리뷰 해상도, 전처리 단계의
/// 리사이즈, 기기별 카메라 해상도가 제각각이라 픽셀 좌표는 계층을 넘는 순간
/// 의미를 잃는다.
class NormalizedRect {
  const NormalizedRect({
    required this.left,
    required this.top,
    required this.width,
    required this.height,
  });

  final double left;
  final double top;
  final double width;
  final double height;

  double get right => left + width;
  double get bottom => top + height;

  /// 7-세그먼트 숫자 한 자리의 가로:세로 비.
  ///
  /// 실측(2026-09-05, 사람이 숫자 줄만 감싼 밴드 라벨 39장): 획에 딱 맞춘
  /// 상자로 잰 자리당 비의 중앙은 **0.492** 다. 이 값은 바깥 반칸 여백이
  /// 빠져 있어 실제 셀 피치의 **하한**이다.
  ///
  /// 과소평가분을 표본에서 직접 풀 수 있었다. 2자리(0.459)와 3자리(0.499)가
  /// 갈리는 방향이 `간격/자릿수` 예측과 맞아서, 두 식을 연립하면 간격 0.24h ·
  /// 피치 **0.579** 가 나온다. 일반 7-세그 규격(0.55~0.62)과도 겹친다.
  ///
  /// 하한(0.492)이 아니라 이 값을 쓰는 이유: 박스가 실제보다 **좁으면**
  /// 사용자가 숫자를 다 못 넣어 뒤로 물러나고, 그러면 숫자에 닿는 픽셀이
  /// 줄어 판독이 나빠진다. 넓은 쪽 오차가 덜 해롭다.
  static const double digitCellAspect = 0.579;

  /// 가이드 박스가 감싸는 자릿수. `SevenSegCnnEngine.digitCount` 기본값과
  /// 같아야 한다 — 엔진이 ROI 를 이 개수로 등폭 분할하기 때문이다.
  static const int guideDigitCount = 3;

  /// 프레임 종횡비(가로/세로)에 맞춰 가이드 박스를 만든다.
  ///
  /// **정규화 상수 하나로는 못 맞춘다.** `0.80 × 0.20` 은 그 자체로 모양이
  /// 없고, 실제 비는 프레임이 정한다 — 16:9 센서(0.5625)에서 2.25:1,
  /// 4:3 센서(0.75)에서 3.00:1 이다. 어느 한쪽에 맞춘 상수는 반드시 다른
  /// 쪽에서 틀린다. 그래서 상수를 조정하지 않고 여기서 계산한다.
  ///
  /// 폭은 [width] 로 고정하고 높이를 유도한다. 반대로 하면 4:3 기기에서
  /// 박스가 화면 폭의 46% 로 좁아져 숫자에 닿는 픽셀이 그만큼 준다.
  /// 세로 중앙에 둔다.
  static NormalizedRect guideBoxFor(
    double frameAspect, {
    double width = 0.80,
    double cellAspect = digitCellAspect,
    int digits = guideDigitCount,
  }) {
    final ratio = cellAspect * digits;
    final height = (width * frameAspect / ratio).clamp(0.01, 1.0);
    return NormalizedRect(
      left: (1 - width) / 2,
      top: (1 - height) / 2,
      width: width,
      height: height,
    );
  }

  /// 프레임 비를 모를 때 쓰는 기본값 — 16:9 센서 세로.
  ///
  /// 실제 카메라 경로는 컨트롤러에서 비를 읽어 [guideBoxFor] 를 쓴다.
  /// 이 상수는 그 값을 못 구하는 경로(테스트·정지 사진)의 대타다.
  static final NormalizedRect defaultGuideBox = guideBoxFor(9 / 16);
}

class OcrFrame {
  const OcrFrame({
    required this.bytes,
    required this.format,
    required this.width,
    required this.height,
    this.rotationDegrees = 0,
    this.roi,
  });

  final Uint8List bytes;
  final OcrImageFormat format;
  final int width;
  final int height;

  /// 기기 방향 보정을 위해 시계 방향으로 회전해야 하는 각도.
  final int rotationDegrees;

  /// null 이면 전체 프레임을 대상으로 한다.
  final NormalizedRect? roi;
}
