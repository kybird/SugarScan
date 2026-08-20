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

  /// 혈당계 LCD 의 가로:세로 비율에 맞춘 기본 가이드 박스.
  ///
  /// 사용자가 이 박스에 화면을 맞춰 주기 때문에 텍스트 검출기(CRAFT)를 생략할
  /// 수 있고, 그만큼 추론 비용이 절반 이하로 떨어진다.
  static const NormalizedRect defaultGuideBox = NormalizedRect(
    left: 0.10,
    top: 0.40,
    width: 0.80,
    height: 0.20,
  );
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
