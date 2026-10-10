import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

/// 배포 전처리(letterbox·bilinear)의 규약 고정 — 골든 벡터 대조.
///
/// 골든은 Python 참조 구현(train_band.letterbox · cv2.resize INTER_LINEAR)이
/// 만들었고 `assets_dev/train/export_deploy_onnx.py` 가 재생성한다. cv2 의
/// uint8 리사이즈는 고정소수 보간이라 Dart 부동소수 판과 픽셀당 최대 1 의
/// 차이가 난다 — 허용 오차 1/255 는 그 규약 차다(1/255 미만의 입력 차이는
/// 검출·판독 결과를 바꾸지 않는다).
void main() {
  final goldens = jsonDecode(
    File('test/ocr/support/deploy_golden_vectors.json').readAsStringSync(),
  ) as Map<String, dynamic>;

  group('letterbox', () {
    for (final (i, case_) in
        (goldens['letterbox'] as List).cast<Map<String, dynamic>>().indexed) {
      test('합성 케이스 $i (${case_['in_w']}×${case_['in_h']} → ${case_['size']})',
          () {
        final input = _decode(case_['in'] as String);
        final expected = _decode(case_['out'] as String);
        final size = case_['size'] as int;

        final result = DeployPreprocess.letterbox(
          input,
          case_['in_w'] as int,
          case_['in_h'] as int,
          size,
        );

        // 스케일·오프셋은 정확히 일치해야 한다 — 어긋나면 상자 좌표가
        // 원본 좌표계로 돌아올 때 통째로 어긋난다.
        expect(result.scale, case_['r'] as double);
        expect(result.dx, case_['dx'] as int);
        expect(result.dy, case_['dy'] as int);

        expect(result.pixels.length, size * size);
        var maxDiff = 0.0;
        for (var y = 0; y < size; y++) {
          for (var x = 0; x < size; x++) {
            final golden = expected[y * size + x] / 255;
            final diff = (result.pixels[y * size + x] - golden).abs();
            if (diff > maxDiff) maxDiff = diff;
          }
        }
        // 1e-6 은 Float32 저장 정밀도(~3e-8) 여유분이다.
        expect(maxDiff, lessThanOrEqualTo(1 / 255 + 1e-6),
            reason: '픽셀당 최대 편차가 1/255 을 넘었다');
      });
    }
  });

  group('resizeBilinear (리더 크롭)', () {
    for (final (i, case_) in (goldens['crop_resize'] as List)
        .cast<Map<String, dynamic>>()
        .indexed) {
      test('합성 케이스 $i (${case_['in_w']}×${case_['in_h']} → '
          '${case_['out_w']}×${case_['out_h']})', () {
        final input = _decode(case_['in'] as String);
        final expected = _decode(case_['out'] as String);

        final result = DeployPreprocess.resizeBilinear(
          input,
          case_['in_w'] as int,
          case_['in_h'] as int,
          case_['out_w'] as int,
          case_['out_h'] as int,
        );

        expect(result.length, expected.length);
        var maxDiff = 0;
        for (var i = 0; i < expected.length; i++) {
          final diff = (result[i] - expected[i]).abs();
          if (diff > maxDiff) maxDiff = diff;
        }
        expect(maxDiff, lessThanOrEqualTo(1),
            reason: '픽셀당 최대 편차가 1 을 넘었다');
      });
    }
  });

  test('readerInput 은 /255−0.5 정규화다', () {
    final out = DeployPreprocess.readerInput(Uint8List.fromList([0, 114, 255]));
    expect(out[0], closeTo(-0.5, 1e-6));
    expect(out[1], closeTo(114 / 255 - 0.5, 1e-6));
    expect(out[2], closeTo(0.5, 1e-6));
  });
}

Uint8List _decode(String b64) =>
    Uint8List.fromList(base64Decode(b64));
