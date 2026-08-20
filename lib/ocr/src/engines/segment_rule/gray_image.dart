import 'dart:typed_data';

/// 8비트 그레이스케일 이미지.
///
/// 알고리즘 핵심부가 `package:image` 같은 외부 타입에 묶이지 않게 하려고 둔
/// 최소 표현이다. 덕분에 이진화·샘플링·품질 판정을 이미지 라이브러리 없이
/// 유닛테스트할 수 있다.
class GrayImage {
  GrayImage({
    required this.pixels,
    required this.width,
    required this.height,
  }) : assert(pixels.length == width * height);

  GrayImage.filled(this.width, this.height, [int value = 0])
      : pixels = Uint8List(width * height)..fillRange(0, width * height, value);

  final Uint8List pixels;
  final int width;
  final int height;

  int get length => pixels.length;

  int at(int x, int y) => pixels[y * width + x];

  void set(int x, int y, int value) => pixels[y * width + x] = value;

  /// 좌표를 이미지 안으로 잘라 낸 부분 이미지를 만든다.
  GrayImage crop(int left, int top, int cropWidth, int cropHeight) {
    final l = left.clamp(0, width - 1);
    final t = top.clamp(0, height - 1);
    final w = cropWidth.clamp(1, width - l);
    final h = cropHeight.clamp(1, height - t);

    final out = Uint8List(w * h);
    for (var y = 0; y < h; y++) {
      final srcStart = (t + y) * width + l;
      out.setRange(y * w, y * w + w, pixels, srcStart);
    }
    return GrayImage(pixels: out, width: w, height: h);
  }
}
