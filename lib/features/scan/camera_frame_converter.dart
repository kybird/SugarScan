import 'dart:typed_data';

import '../../ocr/ocr.dart';

/// 카메라 프레임을 OCR 모듈이 받는 [OcrFrame] 으로 바꾼다.
///
/// 카메라 플러그인 타입에 의존하지 않는 순수 함수만 모아 둔다. 여기가 로우
/// 스트라이드·회전처럼 조용히 틀리기 쉬운 계산이 사는 곳이라, 실기기 없이
/// 검증할 수 있어야 한다. 플러그인 타입과의 접합은 `camera_image_adapter.dart`
/// 가 맡는다.
abstract final class CameraFrameConverter {
  /// YUV420 / NV21 프레임의 **Y 평면만** 꺼내 그레이스케일 프레임을 만든다.
  ///
  /// Y 평면은 그 자체가 휘도다. 색을 버리는 손실 변환이 아니라, 7-세그먼트
  /// 판독이 필요로 하는 바로 그 값을 공짜로 얻는 것이다. UV 평면은 읽지도
  /// 않으므로 프레임당 복사량이 3분의 1로 줄어든다.
  ///
  /// [bytesPerRow] 는 카메라가 정렬을 위해 넣은 패딩을 포함한 실제 행 길이다.
  /// 이 값을 무시하고 `width` 로 읽으면 행이 조금씩 밀려 화면이 비스듬히
  /// 기울어 보이고, 세그먼트 샘플 영역이 통째로 어긋난다.
  static OcrFrame? fromLumaPlane({
    required Uint8List plane,
    required int width,
    required int height,
    required int bytesPerRow,
    int rotationDegrees = 0,
    NormalizedRect? roi,
  }) {
    final luma = _extractLuma(plane, width, height, bytesPerRow);
    if (luma == null) return null;

    final rotated = rotateGrayscale(luma, width, height, rotationDegrees);
    if (rotated == null) return null;

    return OcrFrame(
      bytes: rotated.bytes,
      format: OcrImageFormat.grayscale8,
      width: rotated.width,
      height: rotated.height,
      // 이미 똑바로 세워서 넘긴다. 엔진마다 회전을 다시 구현하게 두면
      // 엔진을 추가할 때마다 같은 버그를 다시 만든다.
      roi: roi,
    );
  }

  /// iOS 카메라의 BGRA8888 프레임을 그레이스케일로 바꾼다.
  static OcrFrame? fromBgra8888({
    required Uint8List plane,
    required int width,
    required int height,
    required int bytesPerRow,
    int rotationDegrees = 0,
    NormalizedRect? roi,
  }) {
    if (width <= 0 || height <= 0) return null;
    final required = (height - 1) * bytesPerRow + width * 4;
    if (plane.length < required) return null;

    final luma = Uint8List(width * height);
    var out = 0;
    for (var y = 0; y < height; y++) {
      var i = y * bytesPerRow;
      for (var x = 0; x < width; x++) {
        final b = plane[i];
        final g = plane[i + 1];
        final r = plane[i + 2];
        // ITU-R BT.601 휘도.
        luma[out++] = (0.114 * b + 0.587 * g + 0.299 * r).round().clamp(0, 255);
        i += 4;
      }
    }

    final rotated = rotateGrayscale(luma, width, height, rotationDegrees);
    if (rotated == null) return null;

    return OcrFrame(
      bytes: rotated.bytes,
      format: OcrImageFormat.grayscale8,
      width: rotated.width,
      height: rotated.height,
      roi: roi,
    );
  }

  static Uint8List? _extractLuma(
    Uint8List plane,
    int width,
    int height,
    int bytesPerRow,
  ) {
    if (width <= 0 || height <= 0 || bytesPerRow < width) return null;
    final required = (height - 1) * bytesPerRow + width;
    if (plane.length < required) return null;

    // 패딩이 없으면 복사 없이 잘라 쓴다.
    if (bytesPerRow == width) {
      return Uint8List.sublistView(plane, 0, width * height);
    }

    final out = Uint8List(width * height);
    for (var row = 0; row < height; row++) {
      out.setRange(row * width, row * width + width, plane, row * bytesPerRow);
    }
    return out;
  }

  /// 그레이스케일 버퍼를 시계 방향으로 회전한다. 0/90/180/270 만 받는다.
  static ({Uint8List bytes, int width, int height})? rotateGrayscale(
    Uint8List src,
    int width,
    int height,
    int degrees,
  ) {
    if (src.length < width * height) return null;

    final normalized = ((degrees % 360) + 360) % 360;
    switch (normalized) {
      case 0:
        return (bytes: src, width: width, height: height);

      case 90:
        final out = Uint8List(width * height);
        for (var y = 0; y < height; y++) {
          final rowStart = y * width;
          for (var x = 0; x < width; x++) {
            out[x * height + (height - 1 - y)] = src[rowStart + x];
          }
        }
        return (bytes: out, width: height, height: width);

      case 180:
        final out = Uint8List(width * height);
        final last = width * height - 1;
        for (var i = 0; i <= last; i++) {
          out[last - i] = src[i];
        }
        return (bytes: out, width: width, height: height);

      case 270:
        final out = Uint8List(width * height);
        for (var y = 0; y < height; y++) {
          final rowStart = y * width;
          for (var x = 0; x < width; x++) {
            out[(width - 1 - x) * height + y] = src[rowStart + x];
          }
        }
        return (bytes: out, width: height, height: width);

      default:
        return null;
    }
  }
}
