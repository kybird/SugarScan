import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

import 'support/seven_segment_renderer.dart';

/// 합성 렌더링으로 판독기를 끝까지 돌린다.
///
/// 실제 사진 없이도 이진화 → 샘플링 → 패턴 매칭 → 조립 전 구간을 검증할 수
/// 있다. 실촬 정확도는 여기서 알 수 없고 골든셋으로 따로 측정한다.
void main() {
  const renderer = SevenSegmentRenderer();

  OcrFrame frameOf(GrayImage image) => OcrFrame(
        bytes: image.pixels,
        format: OcrImageFormat.grayscale8,
        width: image.width,
        height: image.height,
      );

  Future<SegmentRuleEngine> engine() async {
    final e = SegmentRuleEngine();
    await e.initialize(const OcrEngineConfig());
    return e;
  }

  Future<String?> read(String displayed) async {
    final e = await engine();
    final result = await e.recognize(frameOf(renderer.render(displayed)));
    return result.best?.rawText;
  }

  group('숫자 판독', () {
    test('0부터 9까지 모든 숫자를 읽는다', () async {
      for (var d = 0; d <= 9; d++) {
        expect(await read('$d'), '$d', reason: '숫자 $d');
      }
    });

    test('두 자리 / 세 자리 / 네 자리', () async {
      expect(await read('98'), '98');
      expect(await read('102'), '102');
      expect(await read('1025'), '1025');
    });

    test('혈당 범위의 대표값들', () async {
      for (final value in ['70', '99', '126', '180', '250', '400']) {
        expect(await read(value), value);
      }
    });

    test('0 이 섞인 값을 잘못 읽지 않는다', () async {
      expect(await read('100'), '100');
      expect(await read('108'), '108');
      expect(await read('180'), '180');
    });
  });

  group('소수점', () {
    test('102.5 를 읽는다', () async {
      expect(await read('102.5'), '102.5');
    });

    test('5.6 을 읽는다', () async {
      expect(await read('5.6'), '5.6');
    });

    test('소수점 유무를 구분한다 — mmol/L 지원의 근거', () async {
      // 이 구분이 없으면 7.6 mmol/L 이 76 이 되어 10배 어긋난다.
      expect(await read('1025'), '1025');
      expect(await read('102.5'), '102.5');
    });

    test('mmol/L 범위 값들', () async {
      for (final value in ['4.5', '5.6', '7.8', '12.3']) {
        expect(await read(value), value);
      }
    });
  });

  group('LO / HI', () {
    test('LO 를 10 으로 읽지 않는다', () async {
      // O 는 0 과 획이 같다. L 을 닻으로 삼지 않으면 정확히 10 이 된다.
      expect(await read('LO'), 'LO');
    });

    test('HI 를 읽는다', () async {
      expect(await read('HI'), 'HI');
    });
  });

  group('판독 거부', () {
    test('빈 화면은 읽지 않는다', () async {
      final e = await engine();
      final result = await e.recognize(frameOf(renderer.render('')));

      expect(result.hasCandidates, isFalse);
      expect(result.failure?.kind, OcrFailureKind.noTextFound);
    });

    test('초점이 나간 프레임은 해독 전에 버린다', () async {
      // 뭉개진 세그먼트에서 나온 그럴듯한 오답이 시간 투표를 오염시킨다.
      final e = await engine();
      final blurred = blur(renderer.render('102'));
      final result = await e.recognize(frameOf(blurred));

      expect(result.hasCandidates, isFalse);
      expect(result.failure?.kind, OcrFailureKind.noTextFound);
    });

    test('initialize 전에는 notInitialized', () async {
      final result = await SegmentRuleEngine()
          .recognize(frameOf(renderer.render('102')));
      expect(result.failure?.kind, OcrFailureKind.notInitialized);
    });

    test('지원하지 않는 프레임 포맷은 거부한다', () async {
      final e = await engine();
      final image = renderer.render('102');
      final result = await e.recognize(
        OcrFrame(
          bytes: image.pixels,
          format: OcrImageFormat.yuv420,
          width: image.width,
          height: image.height,
        ),
      );
      expect(result.failure?.kind, OcrFailureKind.unsupportedFormat);
    });
  });

  group('엔진 계약', () {
    test('모델 에셋이 필요 없으므로 초기화만으로 준비된다', () async {
      final e = SegmentRuleEngine();
      expect(e.isReady, isFalse);
      await e.initialize(const OcrEngineConfig());
      expect(e.isReady, isTrue);
    });

    test('두 단위를 모두 지원한다 — 소수점을 읽기 때문', () async {
      final e = await engine();
      expect(e.descriptor.supportedUnits, hasLength(2));
    });

    test('기본 기하는 세그먼트 7개를 정의한다', () {
      expect(SegmentGeometry.standard.segments, hasLength(Seg.count));
    });

    test('네트워크를 쓰지 않는다', () async {
      final e = await engine();
      expect(e.descriptor.requiresNetwork, isFalse);
    });

    test('깨끗한 프레임에서는 신뢰도가 높게 나온다', () async {
      final e = await engine();
      final result = await e.recognize(frameOf(renderer.render('102')));
      expect(result.best!.confidence, greaterThan(0.8));
    });
  });

  group('밝기가 뒤집힌 표시(백라이트)', () {
    test('밝은 획 / 어두운 배경도 읽는다', () async {
      // 극성을 자동 판정하므로 프로파일을 바꾸지 않아도 동작해야 한다.
      const inverted = SevenSegmentRenderer(
        backgroundLevel: 30,
        strokeLevel: 230,
      );
      final e = await engine();
      final result = await e.recognize(frameOf(inverted.render('126')));

      expect(result.best?.rawText, '126');
    });
  });
}
