import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

/// 글레어 게이트 단위 테스트.
///
/// 반사광은 "포화 픽셀이 덩어리로 붙는" 현상이라 최대 클러스터 크기로 잡는다.
/// 테스트 전부 합성 이미지로 돌린다 — 실촬 임계값 재보정은 골든셋 과제다.
void main() {
  /// 라플라시안 분산이 충분히 큰 체커보드 배경(=초점 맞은 프레임).
  GrayImage sharpImage(int width, int height) {
    final img = GrayImage.filled(width, height, 128);
    for (var y = 0; y < height; y++) {
      for (var x = 0; x < width; x++) {
        img.set(x, y, (x + y) % 2 == 0 ? 200 : 56);
      }
    }
    return img;
  }

  GrayImage withBlob(
    GrayImage source,
    int left,
    int top,
    int blobWidth,
    int blobHeight,
  ) {
    final out = GrayImage(
      pixels: Uint8List.fromList(source.pixels),
      width: source.width,
      height: source.height,
    );
    for (var y = top; y < top + blobHeight; y++) {
      for (var x = left; x < left + blobWidth; x++) {
        out.set(x, y, 255);
      }
    }
    return out;
  }

  test('포화 클러스터가 임계를 넘으면 반사광으로 거절한다', () {
    // 20×20 블롭 = 100×100 ROI 의 4% > 기본 임계 2%.
    final image = withBlob(sharpImage(100, 100), 40, 40, 20, 20);
    final q = FrameQualityGate.evaluate(image);

    expect(q.rejected, isTrue);
    expect(q.reason, contains('반사광'));
    expect(q.glareScore, closeTo(0.04, 1e-9));
  });

  test('임계 이하의 작은 블롭은 통과시킨다', () {
    // 10×10 블롭 = 1% < 2%. 놓친 프레임은 프레임 합의가 다시 잡는다.
    final image = withBlob(sharpImage(100, 100), 40, 40, 10, 10);
    final q = FrameQualityGate.evaluate(image);

    expect(q.rejected, isFalse);
    expect(q.glareScore, closeTo(0.01, 1e-9));
  });

  test('흐릿한 프레임은 블러 판정이 우선한다', () {
    final uniform = GrayImage.filled(100, 100, 255);
    final q = FrameQualityGate.evaluate(uniform);

    expect(q.rejected, isTrue);
    expect(q.reason, contains('초점'));
  });

  test('흩어진 밝은 픽셀은 클러스터로 자라지 않는다', () {
    // 255/0 체커보드의 포화 픽셀은 서로 붙지 않는다 — 최대 클러스터는 1픽셀.
    final checker = GrayImage.filled(100, 100, 0);
    for (var y = 0; y < 100; y++) {
      for (var x = 0; x < 100; x++) {
        if ((x + y) % 2 == 0) checker.set(x, y, 255);
      }
    }
    final ratio =
        FrameQualityGate.largestSaturatedClusterRatio(checker);

    expect(ratio, closeTo(1 / 10000, 1e-9));
  });

  test('두 블롭이 있으면 큰 쪽만 잰다', () {
    var image = sharpImage(100, 100);
    image = withBlob(image, 0, 0, 10, 10); // 1%
    image = withBlob(image, 50, 50, 25, 25); // 6.25%

    expect(
      FrameQualityGate.largestSaturatedClusterRatio(image),
      closeTo(0.0625, 1e-9),
    );
  });

  test('임계값은 주입해서 바꿀 수 있다', () {
    // 같은 4% 블롭도 임계를 5% 로 올리면 통과한다.
    final image = withBlob(sharpImage(100, 100), 40, 40, 20, 20);
    final q = FrameQualityGate.evaluate(image, glareThreshold: 0.05);

    expect(q.rejected, isFalse);
  });
}
