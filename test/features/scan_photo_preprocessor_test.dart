import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:sugarscan/features/scan/photo_preprocessor.dart';

/// 사진 전처리기의 실패 경로 — 표시가 없는 사진은 null 로 명시적으로
/// 거부해야 한다(호출자가 원본 프레임으로 넘어간다).
void main() {
  Uint8List solidPng(int w, int h, int value) {
    final image = img.Image(width: w, height: h);
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        image.setPixelRgb(x, y, value, value, value);
      }
    }
    return img.encodePng(image);
  }

  test('표시가 없는 단색 사진은 null 을 돌려준다', () {
    expect(preprocessPhotoForEngine(solidPng(320, 160, 128)), isNull);
  });

  test('너무 작은 이미지는 null 을 돌려준다', () {
    expect(preprocessPhotoForEngine(solidPng(8, 8, 0)), isNull);
  });

  test('파일이 아니면 null 을 돌려준다', () {
    expect(preprocessPhotoForEngine(Uint8List(8)), isNull);
  });

  test('JPEG 파서가 예외로 실패하는 바이트열도 null 을 돌려준다', () {
    // 실촬 벤더 파일에서 확인된 크래시(2026-08-27, Datumo 표본)의 축소 재현.
    // image 패키지 디코더는 null 이 아니라 예외를 던지고, 그대로 두면 앱 사진
    // 경로가 통째로 죽는다. 계약은 "해석 불가 = null" 이다.
    final soiOnly = Uint8List.fromList(const [0xFF, 0xD8]);
    expect(preprocessPhotoForEngine(soiOnly), isNull);
  });
}
