import 'dart:typed_data';

/// 셀 하나에 대한 분류 결과.
class DigitPrediction {
  const DigitPrediction({required this.classIndex, required this.confidence});

  /// 0~9 는 숫자, [DigitClassifier.blankClassIndex] 이상은 "표시 없음".
  final int classIndex;

  final double confidence;

  bool get isDigit => classIndex >= 0 && classIndex <= 9;

  @override
  String toString() =>
      'DigitPrediction($classIndex, ${confidence.toStringAsFixed(2)})';
}

/// 96×96 셀 이미지 하나를 숫자로 분류하는 모델.
///
/// TFLite 런타임을 이 인터페이스 뒤로 숨긴다. 덕분에 엔진의 조립 로직(셀 분할,
/// 자릿수 결합, 신뢰도 산출)을 실제 모델 파일 없이 유닛테스트할 수 있고,
/// 나중에 ONNX 모델로 갈아탈 때 엔진 본체는 건드리지 않는다.
abstract interface class DigitClassifier {
  /// 모델이 기대하는 입력 한 변의 길이(픽셀). 정사각형이다.
  int get inputSize;

  /// 이 값 이상의 클래스 인덱스는 숫자가 아닌 "표시 없음"으로 본다.
  int get blankClassIndex;

  /// [cells] 는 각각 `inputSize * inputSize * 3` 길이의 RGB float32
  /// (0.0~1.0 정규화) 버퍼다. 결과는 입력과 같은 순서로 돌아온다.
  Future<List<DigitPrediction>> classify(List<Float32List> cells);

  Future<void> dispose();
}
