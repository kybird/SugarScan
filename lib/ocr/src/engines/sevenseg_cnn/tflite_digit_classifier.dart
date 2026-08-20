import 'dart:math' as math;
import 'dart:typed_data';

import 'package:tflite_flutter/tflite_flutter.dart';

import 'digit_classifier.dart';

/// TFLite 런타임으로 자릿수를 분류한다.
///
/// 모델: Kazuhito00/7segment-display-reader `7seg_classifier.tflite` (Apache-2.0).
/// 입력 [1, 96, 96, 3] float32(0~1), 출력 [1, N] 클래스 점수.
///
/// 입출력 형태를 상수로 박지 않고 로딩 시점에 텐서에서 읽는다. 모델을 다른
/// 것으로 바꿔도(입력 크기나 클래스 수가 달라도) 이 클래스는 그대로 동작한다.
class TfliteDigitClassifier implements DigitClassifier {
  TfliteDigitClassifier._(
    this._interpreter, {
    required this.inputSize,
    required this.classCount,
    required this.blankClassIndex,
  });

  static const String defaultAssetPath = 'assets/models/7seg_classifier.tflite';

  final Interpreter _interpreter;

  @override
  final int inputSize;

  final int classCount;

  @override
  final int blankClassIndex;

  /// 모델을 불러온다. 에셋이 없거나 형태가 예상과 다르면 **null 을 돌려준다.**
  ///
  /// 예외를 던지지 않는 이유: 모델이 없는 빌드에서도 앱은 정상적으로 떠야 하고,
  /// 스캐너가 `ScanUnavailable` 을 내면 사용자는 수동 입력으로 안내된다.
  static Future<TfliteDigitClassifier?> tryLoad({
    String assetPath = defaultAssetPath,
  }) async {
    try {
      final interpreter = await Interpreter.fromAsset(assetPath);

      final inputShape = interpreter.getInputTensor(0).shape;
      final outputShape = interpreter.getOutputTensor(0).shape;

      // 기대 형태: [1, H, W, 3] / [1, N]
      if (inputShape.length != 4 ||
          inputShape[1] != inputShape[2] ||
          inputShape[3] != 3 ||
          outputShape.length != 2) {
        interpreter.close();
        return null;
      }

      final classCount = outputShape[1];
      return TfliteDigitClassifier._(
        interpreter,
        inputSize: inputShape[1],
        classCount: classCount,
        // 0~9 다음 인덱스부터가 "표시 없음" 계열이다.
        blankClassIndex: math.min(10, classCount - 1),
      );
    } on Object {
      return null;
    }
  }

  @override
  Future<List<DigitPrediction>> classify(List<Float32List> cells) async {
    final input = _interpreter.getInputTensor(0);
    final output = _interpreter.getOutputTensor(0);
    final expected = inputSize * inputSize * 3;

    final results = <DigitPrediction>[];
    for (final cell in cells) {
      if (cell.length != expected) {
        results.add(const DigitPrediction(classIndex: -1, confidence: 0));
        continue;
      }
      // 중첩 List 를 만들지 않고 텐서 버퍼에 직접 쓴다. 프레임마다 3자리 ×
      // 27,648개 객체를 할당하면 라이브 스캔에서 GC 압력이 그대로 지연이 된다.
      input.data = cell.buffer.asUint8List();
      _interpreter.invoke();

      final scores = _toProbabilities(
        output.data.buffer.asFloat32List(0, classCount),
      );
      results.add(_argmax(scores));
    }
    return results;
  }

  /// 모델 마지막 층이 softmax 인지 logit 인지에 관계없이 확률로 만든다.
  ///
  /// 신뢰도가 안정화기의 임계값(평균 0.85)과 직접 비교되므로, logit 을 그대로
  /// 쓰면 임계값의 의미가 모델마다 달라진다.
  List<double> _toProbabilities(List<double> raw) {
    final sum = raw.fold<double>(0, (a, b) => a + b);
    final looksLikeProbabilities =
        sum > 0.9 && sum < 1.1 && raw.every((v) => v >= 0 && v <= 1);
    if (looksLikeProbabilities) return raw;

    final max = raw.reduce(math.max);
    final exps = raw.map((v) => math.exp(v - max)).toList(growable: false);
    final expSum = exps.fold<double>(0, (a, b) => a + b);
    return [for (final e in exps) e / expSum];
  }

  DigitPrediction _argmax(List<double> scores) {
    var bestIndex = 0;
    var bestScore = scores.isEmpty ? 0.0 : scores.first;
    for (var i = 1; i < scores.length; i++) {
      if (scores[i] > bestScore) {
        bestScore = scores[i];
        bestIndex = i;
      }
    }
    return DigitPrediction(classIndex: bestIndex, confidence: bestScore);
  }

  @override
  Future<void> dispose() async {
    _interpreter.close();
  }
}
