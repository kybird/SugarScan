import 'dart:typed_data';

/// 배포 모델 전처리 — 학습·평가 파이프라인(train_band.letterbox ·
/// cv2.resize INTER_LINEAR)과 같은 규약의 순수 Dart 판.
///
/// 이 규약은 골든 벡터(test/ocr/support/deploy_golden_vectors.json,
/// 생성: `assets_dev/train/export_deploy_onnx.py`)이 고정한다. cv2 의
/// uint8 리사이즈는 고정소수(5비트) 보간이라 부동소수 판과 픽셀당 최대 1 의
/// 차가 난다 — 학습 경로와 1/255 미만의 차이며 검출·판독에 무시 가능하다.
abstract final class DeployPreprocess {
  /// 레터박스 채움값. 학습(train_band.PAD)과 평가 경로가 같은 값을 쓴다.
  static const int padValue = 114;

  /// 긴 변을 [size] 에 맞춰 축소하고 나머지를 [padValue] 로 채운 뒤
  /// 0~1 로 정규화한다. 검출기 입력(640×640)을 만든다.
  ///
  /// 반환값의 scale·dx·dy 는 검출 상자를 원본 좌표로 되돌리는 데 그대로
  /// 쓴다(`BandDetector.decode`).
  static ({
    Float32List pixels,
    double scale,
    int dx,
    int dy,
  }) letterbox(
    Uint8List gray,
    int width,
    int height,
    int size,
  ) {
    final scale =
        size / height < size / width ? size / height : size / width;
    final nh = _pythonRound(height * scale);
    final nw = _pythonRound(width * scale);
    final dy = (size - nh) ~/ 2;
    final dx = (size - nw) ~/ 2;

    final resized = resizeBilinear(gray, width, height, nw, nh);
    final pixels = Float32List(size * size);
    // 전부 패드로 깔고 이미지 영역(nh×nw)만 덮어쓴다.
    final pad = padValue / 255;
    for (var i = 0; i < pixels.length; i++) {
      pixels[i] = pad;
    }
    var o = 0;
    for (var y = 0; y < nh; y++) {
      final row = (dy + y) * size + dx;
      for (var x = 0; x < nw; x++) {
        pixels[row + x] = resized[o++] / 255;
      }
    }
    return (pixels: pixels, scale: scale, dx: dx, dy: dy);
  }

  /// 리더 입력(144×96)을 만든다 — 크롭을 그대로 늘리고 /255−0.5 정규화.
  ///
  /// 상자 종횡비가 흩어져 있어 늘리는 것 자체가 리더가 견뎌야 할 변형이다
  /// (reader_crnn.BandCrops 규약).
  static Float32List readerInput(Uint8List crop) {
    final out = Float32List(crop.length);
    for (var i = 0; i < crop.length; i++) {
      out[i] = crop[i] / 255 - 0.5;
    }
    return out;
  }

  /// 흑백 버퍼를 밀어 [dstWidth]×[dstHeight] 으로 늘린다(쌍선형).
  ///
  /// cv2.INTER_LINEAR 과 같은 반픽셀 중심 좌표((d+0.5)·scale−0.5)와
  /// 가장자리 복제를 쓴다.
  static Uint8List resizeBilinear(
    Uint8List src,
    int srcWidth,
    int srcHeight,
    int dstWidth,
    int dstHeight,
  ) {
    final out = Uint8List(dstWidth * dstHeight);
    final scaleX = srcWidth / dstWidth;
    final scaleY = srcHeight / dstHeight;
    for (var y = 0; y < dstHeight; y++) {
      final sy = _tap((y + 0.5) * scaleY - 0.5, srcHeight);
      for (var x = 0; x < dstWidth; x++) {
        final sx = _tap((x + 0.5) * scaleX - 0.5, srcWidth);
        final v =
            src[sy.near * srcWidth + sx.near] * sx.inv * sy.inv +
                src[sy.near * srcWidth + sx.far] * sx.frac * sy.inv +
                src[sy.far * srcWidth + sx.near] * sx.inv * sy.frac +
                src[sy.far * srcWidth + sx.far] * sx.frac * sy.frac;
        out[y * dstWidth + x] = v.round().clamp(0, 255);
      }
    }
    return out;
  }

  /// 보간 축 하나: 시작 인접 픽셀·반대편 픽셀·가중치. near/far 는 축의
  /// 앞·뒤 인덱스다(x축이든 y축이든 같은 구조).
  static ({int near, int far, double frac, double inv}) _tap(
    double coordinate,
    int sourceSize,
  ) {
    if (sourceSize == 1) {
      return (near: 0, far: 0, frac: 0, inv: 1);
    }
    var near = coordinate.floor();
    var frac = coordinate - near;
    if (near < 0) {
      near = 0;
      frac = 0;
    } else if (near >= sourceSize - 1) {
      near = sourceSize - 2;
      frac = 1;
    }
    return (near: near, far: near + 1, frac: frac, inv: 1 - frac);
  }

  /// Python round 와 같은 반올림(절반은 짝수로). letterbox 의 치수 계산이
  /// 학습 파이프라인(int(round(h·r))) 과 어긋나면 패딩 오프셋이 밀린다.
  static int _pythonRound(double x) {
    final floor = x.floorToDouble();
    final diff = x - floor;
    if (diff > 0.5) return floor.toInt() + 1;
    if (diff < 0.5) return floor.toInt();
    return floor.toInt() % 2 == 0 ? floor.toInt() : floor.toInt() + 1;
  }
}
