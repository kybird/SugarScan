import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/features/scan/camera_frame_converter.dart';
import 'package:sugarscan/ocr/ocr.dart';

void main() {
  /// 값이 곧 위치인 버퍼. 어긋나면 어디로 갔는지 바로 드러난다.
  Uint8List ramp(int width, int height, {int? bytesPerRow, int padValue = 0}) {
    final stride = bytesPerRow ?? width;
    final out = Uint8List(stride * height)..fillRange(0, stride * height, padValue);
    for (var y = 0; y < height; y++) {
      for (var x = 0; x < width; x++) {
        out[y * stride + x] = (y * width + x) % 251;
      }
    }
    return out;
  }

  group('Y 평면 추출', () {
    test('패딩이 없으면 그대로 쓴다', () {
      final frame = CameraFrameConverter.fromLumaPlane(
        plane: ramp(4, 3),
        width: 4,
        height: 3,
        bytesPerRow: 4,
      )!;

      expect(frame.format, OcrImageFormat.grayscale8);
      expect(frame.width, 4);
      expect(frame.height, 3);
      expect(frame.bytes, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
    });

    test('로우 스트라이드 패딩을 잘라 낸다', () {
      // 이걸 놓치면 행이 조금씩 밀려 화면이 비스듬히 기울어 보이고,
      // 세그먼트 샘플 영역이 통째로 어긋난다.
      final frame = CameraFrameConverter.fromLumaPlane(
        plane: ramp(4, 3, bytesPerRow: 7, padValue: 255),
        width: 4,
        height: 3,
        bytesPerRow: 7,
      )!;

      expect(frame.bytes, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
      expect(frame.bytes.contains(255), isFalse, reason: '패딩이 섞여 들어갔다');
    });

    test('버퍼가 모자라면 null 을 돌려준다', () {
      expect(
        CameraFrameConverter.fromLumaPlane(
          plane: Uint8List(10),
          width: 4,
          height: 3,
          bytesPerRow: 4,
        ),
        isNull,
      );
    });

    test('스트라이드가 폭보다 작으면 거부한다', () {
      expect(
        CameraFrameConverter.fromLumaPlane(
          plane: Uint8List(100),
          width: 10,
          height: 5,
          bytesPerRow: 8,
        ),
        isNull,
      );
    });

    test('ROI 를 그대로 전달한다', () {
      final frame = CameraFrameConverter.fromLumaPlane(
        plane: ramp(4, 3),
        width: 4,
        height: 3,
        bytesPerRow: 4,
        roi: NormalizedRect.defaultGuideBox,
      )!;

      expect(frame.roi, isNotNull);
      expect(frame.roi!.left, NormalizedRect.defaultGuideBox.left);
    });
  });

  group('회전', () {
    // 2×3 (가로 2, 세로 3)
    //   0 1
    //   2 3
    //   4 5
    final src = Uint8List.fromList([0, 1, 2, 3, 4, 5]);

    test('0도는 원본을 그대로 돌려준다', () {
      final r = CameraFrameConverter.rotateGrayscale(src, 2, 3, 0)!;
      expect(r.width, 2);
      expect(r.height, 3);
      expect(identical(r.bytes, src), isTrue, reason: '불필요한 복사');
    });

    test('90도 시계 방향', () {
      //   4 2 0
      //   5 3 1
      final r = CameraFrameConverter.rotateGrayscale(src, 2, 3, 90)!;
      expect(r.width, 3);
      expect(r.height, 2);
      expect(r.bytes, [4, 2, 0, 5, 3, 1]);
    });

    test('180도', () {
      final r = CameraFrameConverter.rotateGrayscale(src, 2, 3, 180)!;
      expect(r.width, 2);
      expect(r.height, 3);
      expect(r.bytes, [5, 4, 3, 2, 1, 0]);
    });

    test('270도 시계 방향', () {
      //   1 3 5
      //   0 2 4
      final r = CameraFrameConverter.rotateGrayscale(src, 2, 3, 270)!;
      expect(r.width, 3);
      expect(r.height, 2);
      expect(r.bytes, [1, 3, 5, 0, 2, 4]);
    });

    test('90도를 네 번 돌리면 원본으로 돌아온다', () {
      var bytes = src;
      var w = 2;
      var h = 3;
      for (var i = 0; i < 4; i++) {
        final r = CameraFrameConverter.rotateGrayscale(bytes, w, h, 90)!;
        bytes = r.bytes;
        w = r.width;
        h = r.height;
      }
      expect(w, 2);
      expect(h, 3);
      expect(bytes, src);
    });

    test('음수와 360도 이상도 정규화한다', () {
      final a = CameraFrameConverter.rotateGrayscale(src, 2, 3, -90)!;
      final b = CameraFrameConverter.rotateGrayscale(src, 2, 3, 270)!;
      expect(a.bytes, b.bytes);

      final c = CameraFrameConverter.rotateGrayscale(src, 2, 3, 450)!;
      final d = CameraFrameConverter.rotateGrayscale(src, 2, 3, 90)!;
      expect(c.bytes, d.bytes);
    });

    test('90의 배수가 아니면 거부한다', () {
      expect(CameraFrameConverter.rotateGrayscale(src, 2, 3, 45), isNull);
    });

    test('회전은 프레임 크기에 반영된다', () {
      final frame = CameraFrameConverter.fromLumaPlane(
        plane: ramp(4, 3),
        width: 4,
        height: 3,
        bytesPerRow: 4,
        rotationDegrees: 90,
      )!;

      expect(frame.width, 3);
      expect(frame.height, 4);
    });
  });

  group('BGRA8888', () {
    test('휘도로 변환한다', () {
      // 흰색 / 검정 / 빨강 / 초록 네 픽셀.
      final plane = Uint8List.fromList([
        255, 255, 255, 255, //
        0, 0, 0, 255, //
        0, 0, 255, 255, // R
        0, 255, 0, 255, // G
      ]);

      final frame = CameraFrameConverter.fromBgra8888(
        plane: plane,
        width: 4,
        height: 1,
        bytesPerRow: 16,
      )!;

      expect(frame.bytes[0], 255);
      expect(frame.bytes[1], 0);
      expect(frame.bytes[2], (0.299 * 255).round());
      expect(frame.bytes[3], (0.587 * 255).round());
    });

    test('로우 스트라이드 패딩을 건너뛴다', () {
      final plane = Uint8List(2 * 12)..fillRange(0, 24, 7);
      // 각 행의 앞 4바이트(픽셀 1개)만 유효하고 나머지는 패딩.
      for (var y = 0; y < 2; y++) {
        plane[y * 12] = 255;
        plane[y * 12 + 1] = 255;
        plane[y * 12 + 2] = 255;
      }

      final frame = CameraFrameConverter.fromBgra8888(
        plane: plane,
        width: 1,
        height: 2,
        bytesPerRow: 12,
      )!;

      expect(frame.bytes, [255, 255]);
    });

    test('버퍼가 모자라면 null', () {
      expect(
        CameraFrameConverter.fromBgra8888(
          plane: Uint8List(8),
          width: 4,
          height: 1,
          bytesPerRow: 16,
        ),
        isNull,
      );
    });
  });
}
