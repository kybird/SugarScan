import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

/// 검출기 디코드 — band_net.decode · eval_e2e_bandnet.py 게이트와 같은
/// 수식인지 합성 맵으로 검증한다(실모델과의 정합은 export_deploy_onnx.py
/// 파리티가 전량 2,504장으로 증명했다).
void main() {
  // 격자 40×40, 셀 (gx=20, gy=10) 하나만 뜨겁게 켠다.
  const hotIndex = 10 * 40 + 20; // 420

  ({Float32List obj, Float32List reg}) maps({
    double hotLogit = 2.1972246, // sigmoid ≈ 0.9
    double l = 50,
    double t = 50,
    double r = 100,
    double b = 100,
  }) {
    final obj = Float32List(1600);
    obj.fillRange(0, obj.length, -6.0);
    obj[hotIndex] = hotLogit;
    final reg = Float32List(6400);
    reg[hotIndex] = l;
    reg[1600 + hotIndex] = t;
    reg[3200 + hotIndex] = r;
    reg[4800 + hotIndex] = b;
    return (obj: obj, reg: reg);
  }

  test('뜨거운 셀의 ltrb 거리를 상자로 되돌리고 원본 좌표로 매핑한다', () {
    final m = maps();
    // 1280×960 을 640 으로 축소: scale 0.5, nh 480, dy 80, dx 0.
    final box = BandDetector.decode(
      m.obj,
      m.reg,
      scale: 0.5,
      dx: 0,
      dy: 80,
      imageWidth: 1280,
      imageHeight: 960,
    )!;

    expect(box, isNotNull);
    expect(box.score, closeTo(0.9, 1e-3));
    // 레터박스 좌표: (328−50, 168−50, 328+100, 168+100) = (278, 118, 428, 268)
    expect(box.left, closeTo((278 - 0) / 0.5, 1e-3));
    expect(box.top, closeTo((118 - 80) / 0.5, 1e-3));
    expect(box.right, closeTo((428 - 0) / 0.5, 1e-3));
    expect(box.bottom, closeTo((268 - 80) / 0.5, 1e-3));
  });

  test('확신 게이트(0.25) 아래면 null', () {
    final m = maps(hotLogit: -2.5); // sigmoid ≈ 0.076
    expect(
      BandDetector.decode(m.obj, m.reg,
          scale: 0.5, dx: 0, dy: 80, imageWidth: 1280, imageHeight: 960),
      isNull,
    );
  });

  test('면적 게이트(화면의 2%) 아래면 null', () {
    // 상자를 아주 작게 — 칸 반경 몇 픽셀짜리 거리만 둔다.
    final m = maps(l: 2, t: 2, r: 3, b: 3);
    expect(
      BandDetector.decode(m.obj, m.reg,
          scale: 0.5, dx: 0, dy: 80, imageWidth: 1280, imageHeight: 960),
      isNull,
    );
  });

  test('cropRect 는 학습 경로의 반올림을 따른다', () {
    final box = BandBox(
      score: 0.9,
      left: -3.2,
      top: 0,
      right: 8.5,
      bottom: 100.7,
    );
    // int(−3.2)→0(int() 는 0 쪽으로 자름), round(8.5)→8(절반은 짝수로),
    // round(100.7)→101.
    final rect = BandDetector.cropRect(box, 200, 200)!;
    expect(rect, (x0: 0, y0: 0, x1: 8, y1: 101));
  });

  test('cropRect 는 4px 미만 크롭을 거절한다', () {
    final box = BandBox(score: 0.9, left: 10, top: 10, right: 13, bottom: 40);
    expect(BandDetector.cropRect(box, 200, 200), isNull);
  });
}
