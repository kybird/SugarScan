import 'engine/ocr_engine_registry.dart';
import 'engines/segment_rule/segment_rule_engine.dart';
import 'engines/sevenseg_cnn/seven_seg_cnn_engine.dart';
import 'engines/sevenseg_cnn/tflite_digit_classifier.dart';
import 'scanner/glucose_scanner.dart';

/// 엔진 구현을 레지스트리에 등록하는 **유일한** 지점.
///
/// 이 함수 밖에서는 어떤 코드도 `engines/…` 를 import 하지 않는다. 앱은 물론
/// 모듈 안의 스캐너조차 구체 엔진을 모른다.
///
/// OCR 은 전부 단말에서 돌아간다. 서버 기반 인식 경로는 두지 않으며,
/// 정확도 비교 실험이 필요하면 앱이 아니라 PC 측 `tools/ocr_bench` 에서 한다.
GlucoseScanner buildGlucoseScanner() {
  final registry = OcrEngineRegistry();

  // 규칙 기반 판독기를 기본 엔진으로 먼저 등록한다.
  // 모델 에셋도 런타임도 필요 없어 항상 동작하고, 소수점을 읽으므로 두 단위를
  // 모두 지원한다. 스캐너는 사용자의 표시 단위를 읽을 수 있는 첫 엔진을 고른다.
  final rule = SegmentRuleEngine();
  registry.register(rule.descriptor, SegmentRuleEngine.new);

  // 7-세그먼트 자릿수 분류 CNN (Kazuhito00/7segment-display-reader, Apache-2.0).
  // 모델 에셋이 없으면 initialize() 단계에서 조용히 실패하고, 스캐너가
  // ScanUnavailable(modelUnavailable) 을 낸다 — 앱은 수동 입력으로 안내한다.
  final cnn = SevenSegCnnEngine(classifierLoader: TfliteDigitClassifier.tryLoad);
  registry.register(cnn.descriptor, () => cnn);

  // W4: EasyOcrOnnxEngine (CRNN ONNX 변환본). mmol/L 을 읽으려면 소수점
  //     클래스가 있는 이 엔진이 필요하다.
  // W5: MlKitEngine (비교군)

  return GlucoseScanner(registry: registry);
}
