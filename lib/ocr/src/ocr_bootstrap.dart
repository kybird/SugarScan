import 'engine/ocr_engine_registry.dart';
import 'engines/bandnet_crnn/band_detector.dart';
import 'engines/bandnet_crnn/bandnet_crnn_engine.dart';
import 'engines/bandnet_crnn/onnx_runtime_deploy_model.dart';
import 'engines/segment_rule/segment_rule_engine.dart';
import 'engines/sevenseg_cnn/seven_seg_cnn_engine.dart';
import 'engines/sevenseg_cnn/tflite_digit_classifier.dart';
import 'scanner/glucose_scanner.dart';

/// 엔진 구현을 레지스트리에 등록하는 **유일한** 지점.
///
/// 이 함수 밖에서는 어떤 코드도 `engines/…` 를 import 하지 않는다. 앱은 물론
/// 모듈 안의 스캐너조차 구체 엔진을 모른다.
///
/// OCR 은 전부 단말에서 돈다. 서버 기반 인식 경로는 두지 않으며,
/// 정확도 비교 실험이 필요하면 앱이 아니라 PC 측 `tools/ocr_bench` 에서 한다.
GlucoseScanner buildGlucoseScanner() {
  final registry = OcrEngineRegistry();

  // 학습 파이프라인 배포판(2026-10-10 프리징: BandNet ftk5_g0.06 × CRNN
  // rftk5_foldall). **등록 순서가 곧 기본 우선순위다** — mg/dL 사용자는 이
  // 엔진부터 고른다. 모델 애셋이 없는 빌드에서는 isReady 가 거짓이 되고
  // 스캐너가 ScanUnavailable(modelUnavailable) 을 내 사용자를 수동 입력으로
  // 안내한다("모델이 없는 경우가 정상 경로다" 원칙).
  // 소수점 클래스가 없어 mmol/L 는 못 읽는다 — mmol/L 사용자는 아래 규칙
  // 엔진이 잡는다.
  final deploy = BandNetCrnnEngine(
    detectorLoader: () => OnnxRuntimeModel.tryLoad(
      BandNetCrnnEngine.detectorAssetPath,
      inputName: 'image',
      inputShape: const [1, 1, BandDetector.inputSize, BandDetector.inputSize],
    ),
    readerLoader: () => OnnxRuntimeModel.tryLoad(
      BandNetCrnnEngine.readerAssetPath,
      inputName: 'crop',
      inputShape: const [1, 1, 96, 144],
    ),
  );
  registry.register(deploy.descriptor, () => deploy);

  // 규칙 기반 판독기 — 모델·런타임 없이 항상 동작하는 폴백. 소수점을 읽어
  // mmol/L 도 지원한다.
  final rule = SegmentRuleEngine();
  registry.register(rule.descriptor, SegmentRuleEngine.new);

  // 7-세그먼트 자릿수 분류 CNN (Kazuhito00/7segment-display-reader, Apache-2.0).
  // 모델 에셋이 없으면 initialize() 단계에서 조용히 실패하고, 스캐너가
  // ScanUnavailable(modelUnavailable) 을 낸다 — 앱은 수동 입력으로 안내한다.
  final cnn = SevenSegCnnEngine(classifierLoader: TfliteDigitClassifier.tryLoad);
  registry.register(cnn.descriptor, () => cnn);

  return GlucoseScanner(registry: registry);
}
