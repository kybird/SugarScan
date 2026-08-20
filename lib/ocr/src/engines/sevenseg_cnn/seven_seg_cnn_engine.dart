import 'dart:typed_data';

import 'package:image/image.dart' as img;

import '../../../../domain/models/glucose_unit.dart';
import '../../engine/ocr_engine.dart';
import '../../engine/ocr_frame.dart';
import '../../engine/ocr_result.dart';
import 'cell_splitter.dart';
import 'digit_classifier.dart';

/// 7-세그먼트 자릿수 분류 CNN 엔진.
///
/// 모델 출처: Kazuhito00/7segment-display-reader (Apache-2.0).
/// 96×96 RGB 입력, 클래스 0~9 + "표시 없음". ROI 를 자릿수만큼 등분해 셀별로
/// 분류하고 결과를 이어 붙인다.
///
/// **mg/dL 전용이다.** 이 모델에는 소수점 클래스가 없어서 mmol/L 을 읽으면
/// `7.6` 이 `76` 이 된다. 10배 어긋난 값이 정상 범위 안에 들어앉기 때문에
/// 검증기도 안정화기도 이 오류를 잡지 못한다. 그래서 [descriptor] 가
/// mg/dL 만 지원한다고 선언하고, 스캐너가 시작 시점에 거른다.
class SevenSegCnnEngine implements OcrEngine {
  SevenSegCnnEngine({
    required Future<DigitClassifier?> Function() classifierLoader,
    this.digitCount = 3,
  })  : _loadClassifier = classifierLoader,
        assert(digitCount > 0);

  static const String engineId = 'sevenseg_cnn_v1';

  /// 모델 로딩은 [initialize] 에서 일어난다. 생성자를 동기로 유지해야
  /// 레지스트리가 엔진을 평범한 팩토리로 다룰 수 있다.
  final Future<DigitClassifier?> Function() _loadClassifier;

  DigitClassifier? _classifier;

  /// 읽을 자릿수. 혈당계 mg/dL 표시는 보통 최대 3자리다.
  /// 앞자리가 비어 있어도(`  95`) 모델의 "표시 없음" 클래스가 걸러낸다.
  final int digitCount;

  bool _initialized = false;

  @override
  final OcrEngineDescriptor descriptor = const OcrEngineDescriptor(
    id: engineId,
    displayName: '7-segment CNN (TFLite)',
    kind: OcrEngineKind.tflite,
    acceptedFormats: {
      OcrImageFormat.png,
      OcrImageFormat.jpeg,
      OcrImageFormat.bgra8888,
      OcrImageFormat.grayscale8,
    },
    // 소수점을 못 읽는다. 아래 클래스 주석 참조.
    supportedUnits: {GlucoseUnit.mgdl},
    targetLatencyMs: 120,
  );

  @override
  Future<void> initialize(OcrEngineConfig config) async {
    _classifier ??= await _loadClassifier();
    _initialized = true;
  }

  /// 모델 에셋이 없으면 초기화는 성공해도 인식은 할 수 없다.
  @override
  bool get isReady => _initialized && _classifier != null;

  @override
  Future<OcrResult> recognize(OcrFrame frame) async {
    final stopwatch = Stopwatch()..start();

    if (!_initialized) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: const OcrFailure(OcrFailureKind.notInitialized),
      );
    }
    final classifier = _classifier;
    if (classifier == null) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: const OcrFailure(
          OcrFailureKind.modelUnavailable,
          '7seg_classifier.tflite 를 불러오지 못했습니다.',
        ),
      );
    }
    if (!descriptor.acceptedFormats.contains(frame.format)) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: OcrFailure(
          OcrFailureKind.unsupportedFormat,
          '${frame.format.name} 은(는) 아직 지원하지 않습니다.',
        ),
      );
    }

    final decoded = _decode(frame);
    if (decoded == null) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: const OcrFailure(
          OcrFailureKind.unknown,
          '프레임을 디코딩하지 못했습니다.',
        ),
      );
    }

    final roi = _cropRoi(decoded, frame.roi);
    final cells = splitIntoCells(roi.width, digitCount);
    if (cells.isEmpty) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: const OcrFailure(OcrFailureKind.noTextFound, 'ROI 가 너무 작습니다.'),
      );
    }

    final size = classifier.inputSize;
    final inputs = [
      for (final cell in cells)
        _toNormalizedRgb(
          img.copyResize(
            img.copyCrop(
              roi,
              x: cell.left,
              y: 0,
              width: cell.width,
              height: roi.height,
            ),
            width: size,
            height: size,
          ),
          size,
        ),
    ];

    final predictions = await classifier.classify(inputs);
    stopwatch.stop();

    return _assemble(predictions, classifier.blankClassIndex, stopwatch.elapsed);
  }

  /// 셀별 예측을 하나의 후보로 합친다.
  OcrResult _assemble(
    List<DigitPrediction> predictions,
    int blankClassIndex,
    Duration latency,
  ) {
    final buffer = StringBuffer();
    var minConfidence = 1.0;
    var digitsFound = 0;

    for (final prediction in predictions) {
      // "표시 없음"은 건너뛴다. 앞자리 공백을 이렇게 흡수한다.
      if (!prediction.isDigit || prediction.classIndex >= blankClassIndex) {
        continue;
      }
      buffer.write(prediction.classIndex);
      digitsFound++;
      if (prediction.confidence < minConfidence) {
        minConfidence = prediction.confidence;
      }
    }

    if (digitsFound == 0) {
      return OcrResult.failed(
        engineId: engineId,
        latency: latency,
        failure: const OcrFailure(OcrFailureKind.noTextFound),
      );
    }

    return OcrResult(
      engineId: engineId,
      candidates: [
        OcrCandidate(
          rawText: buffer.toString(),
          // 자릿수 전체의 신뢰도는 **가장 약한 자리**를 따른다. 평균을 쓰면
          // 한 자리가 흔들려도 나머지가 가려 주는데, 혈당값은 자리 하나가
          // 틀리면 값 자체가 달라진다(95 vs 195).
          confidence: minConfidence,
          perCharConfidence: [
            for (final p in predictions)
              if (p.isDigit) p.confidence,
          ],
        ),
      ],
      latency: latency,
    );
  }

  img.Image? _decode(OcrFrame frame) {
    try {
      return switch (frame.format) {
        OcrImageFormat.png ||
        OcrImageFormat.jpeg =>
          img.decodeImage(frame.bytes),
        OcrImageFormat.bgra8888 => img.Image.fromBytes(
            width: frame.width,
            height: frame.height,
            bytes: frame.bytes.buffer,
            numChannels: 4,
            order: img.ChannelOrder.bgra,
          ),
        OcrImageFormat.grayscale8 => img.Image.fromBytes(
            width: frame.width,
            height: frame.height,
            bytes: frame.bytes.buffer,
            numChannels: 1,
          ),
        _ => null,
      };
    } on Object {
      return null;
    }
  }

  img.Image _cropRoi(img.Image source, NormalizedRect? roi) {
    if (roi == null) return source;

    // 정규화 좌표를 픽셀로 환산하고 이미지 경계 안으로 자른다.
    final left = (roi.left * source.width).round().clamp(0, source.width - 1);
    final top = (roi.top * source.height).round().clamp(0, source.height - 1);
    final width =
        (roi.width * source.width).round().clamp(1, source.width - left);
    final height =
        (roi.height * source.height).round().clamp(1, source.height - top);

    return img.copyCrop(source, x: left, y: top, width: width, height: height);
  }

  /// 참조 구현과 동일한 전처리: RGB 순서, float32, 0~1 정규화.
  Float32List _toNormalizedRgb(img.Image cell, int size) {
    final buffer = Float32List(size * size * 3);
    var i = 0;
    for (var y = 0; y < size; y++) {
      for (var x = 0; x < size; x++) {
        final pixel = cell.getPixel(x, y);
        buffer[i++] = pixel.r / 255.0;
        buffer[i++] = pixel.g / 255.0;
        buffer[i++] = pixel.b / 255.0;
      }
    }
    return buffer;
  }

  @override
  Future<void> dispose() async {
    _initialized = false;
    await _classifier?.dispose();
    _classifier = null;
  }
}
