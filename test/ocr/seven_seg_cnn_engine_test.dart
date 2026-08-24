import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/ocr/testing.dart';

/// 모델 파일 없이 엔진의 조립 로직을 검증한다.
///
/// TFLite 런타임은 [DigitClassifier] 인터페이스 뒤에 있으므로, 셀 분할 →
/// 자릿수 결합 → 신뢰도 산출까지를 실제 모델 없이 그대로 돌려볼 수 있다.
class _FakeClassifier implements DigitClassifier {
  _FakeClassifier(this.predictions);

  final List<DigitPrediction> predictions;

  final List<int> receivedCellLengths = [];
  int callCount = 0;
  bool disposed = false;

  @override
  int get inputSize => 96;

  @override
  int get blankClassIndex => 10;

  @override
  Future<List<DigitPrediction>> classify(List<Float32List> cells) async {
    callCount++;
    receivedCellLengths
      ..clear()
      ..addAll(cells.map((c) => c.length));
    return predictions;
  }

  @override
  Future<void> dispose() async => disposed = true;
}

DigitPrediction digit(int value, [double confidence = 0.99]) =>
    DigitPrediction(classIndex: value, confidence: confidence);

const blank = DigitPrediction(classIndex: 10, confidence: 0.98);

Uint8List pngFrame({int width = 300, int height = 100}) {
  final image = img.Image(width: width, height: height);
  img.fill(image, color: img.ColorRgb8(20, 20, 20));
  return Uint8List.fromList(img.encodePng(image));
}

OcrFrame frame({
  OcrImageFormat format = OcrImageFormat.png,
  NormalizedRect? roi,
}) =>
    OcrFrame(
      bytes: pngFrame(),
      format: format,
      width: 300,
      height: 100,
      roi: roi,
    );

Future<SevenSegCnnEngine> engineWith(
  DigitClassifier? classifier, {
  int digitCount = 3,
}) async {
  final engine = SevenSegCnnEngine(
    classifierLoader: () async => classifier,
    digitCount: digitCount,
  );
  await engine.initialize(const OcrEngineConfig());
  return engine;
}

void main() {
  group('자릿수 결합', () {
    test('앞자리 공백은 "표시 없음" 클래스로 걸러진다', () async {
      // 혈당계는 95 를 "  95" 처럼 앞자리를 비워 표시한다.
      final classifier = _FakeClassifier([blank, digit(9), digit(5)]);
      final engine = await engineWith(classifier);

      final result = await engine.recognize(frame());

      expect(result.best?.rawText, '95');
      expect(classifier.callCount, 1);
    });

    test('세 자리도 그대로 읽는다', () async {
      final engine =
          await engineWith(_FakeClassifier([digit(1), digit(3), digit(8)]));

      expect((await engine.recognize(frame())).best?.rawText, '138');
    });

    test('전부 표시 없음이면 읽지 못한 것으로 처리한다', () async {
      final engine = await engineWith(_FakeClassifier([blank, blank, blank]));

      final result = await engine.recognize(frame());
      expect(result.hasCandidates, isFalse);
      expect(result.failure?.kind, OcrFailureKind.noTextFound);
    });
  });

  group('신뢰도', () {
    test('가장 약한 자리를 전체 신뢰도로 삼는다', () async {
      // 평균을 쓰면 한 자리가 흔들려도 나머지가 가려 준다. 혈당값은 자리
      // 하나가 틀리면 값 자체가 달라지므로(95 vs 195) 최솟값을 쓴다.
      final engine = await engineWith(_FakeClassifier([
        digit(1, 0.99),
        digit(3, 0.55),
        digit(8, 0.99),
      ]));

      final result = await engine.recognize(frame());
      expect(result.best?.confidence, closeTo(0.55, 0.001));
    });

    test('자릿수별 신뢰도를 함께 돌려준다', () async {
      final engine = await engineWith(_FakeClassifier([
        blank,
        digit(9, 0.90),
        digit(5, 0.80),
      ]));

      final result = await engine.recognize(frame());
      expect(result.best?.perCharConfidence, [0.90, 0.80]);
    });
  });

  group('셀 분할', () {
    test('자릿수만큼 셀을 만들고 모델 입력 크기에 맞춘다', () async {
      final classifier = _FakeClassifier([blank, digit(9), digit(5)]);
      final engine = await engineWith(classifier);

      await engine.recognize(frame());

      expect(classifier.receivedCellLengths, hasLength(3));
      // 96 × 96 × 3(RGB)
      expect(classifier.receivedCellLengths.every((l) => l == 96 * 96 * 3),
          isTrue);
    });

    test('ROI 가 지정되면 그 영역만 자른다', () async {
      final classifier = _FakeClassifier([digit(9), digit(5)]);
      final engine = await engineWith(classifier, digitCount: 2);

      final result = await engine.recognize(
        frame(roi: NormalizedRect.defaultGuideBox),
      );

      expect(result.best?.rawText, '95');
      expect(classifier.receivedCellLengths, hasLength(2));
    });
  });

  group('실패 경로', () {
    test('initialize 전에는 notInitialized', () async {
      final engine = SevenSegCnnEngine(
        classifierLoader: () async => _FakeClassifier(const []),
      );

      final result = await engine.recognize(frame());
      expect(result.failure?.kind, OcrFailureKind.notInitialized);
    });

    test('모델을 못 불러오면 modelUnavailable', () async {
      // 에셋이 없는 빌드에서도 앱은 정상적으로 떠야 한다.
      final engine = await engineWith(null);

      final result = await engine.recognize(frame());
      expect(result.failure?.kind, OcrFailureKind.modelUnavailable);
    });

    test('지원하지 않는 프레임 포맷은 거부한다', () async {
      final engine = await engineWith(_FakeClassifier([digit(9)]));

      final result =
          await engine.recognize(frame(format: OcrImageFormat.yuv420));
      expect(result.failure?.kind, OcrFailureKind.unsupportedFormat);
    });

    test('dispose 하면 분류기도 함께 정리된다', () async {
      final classifier = _FakeClassifier([digit(9)]);
      final engine = await engineWith(classifier);

      await engine.dispose();
      expect(classifier.disposed, isTrue);
      expect((await engine.recognize(frame())).failure?.kind,
          OcrFailureKind.notInitialized);
    });
  });

  test('이 모델은 mg/dL 만 지원한다고 선언한다', () async {
    // 소수점 클래스가 없어서 mmol/L 의 7.6 을 76 으로 읽는다.
    final engine = await engineWith(_FakeClassifier([digit(7), digit(6)]));

    expect(engine.descriptor.supportedUnits, {GlucoseUnit.mgdl});
    expect(engine.descriptor.supportedUnits.contains(GlucoseUnit.mmoll),
        isFalse);
  });
}
