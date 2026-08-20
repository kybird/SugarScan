import '../../../domain/models/glucose_unit.dart';
import 'ocr_frame.dart';
import 'ocr_result.dart';

enum OcrEngineKind { onnx, mlkit, tesseract, tflite, rule, fake }

/// 엔진의 자기 소개. 스캐너와 개발자 설정 화면이 이 정보만 보고 엔진을 다룬다.
class OcrEngineDescriptor {
  const OcrEngineDescriptor({
    required this.id,
    required this.displayName,
    required this.kind,
    required this.acceptedFormats,
    this.supportedUnits = const {GlucoseUnit.mgdl, GlucoseUnit.mmoll},
    this.supportsLiveStream = true,
    this.requiresNetwork = false,
    this.targetLatencyMs = 400,
  });

  /// 안정적인 식별자. 기록에 남아 나중에 "어느 엔진이 읽은 값인지" 추적한다.
  final String id;

  final String displayName;
  final OcrEngineKind kind;
  final Set<OcrImageFormat> acceptedFormats;

  /// 이 엔진이 안전하게 읽을 수 있는 표시 단위.
  ///
  /// 모델이 소수점을 클래스로 갖지 않으면 mmol/L 을 읽을 수 없다. 그런 엔진에
  /// mmol/L 을 물리면 `7.6` 이 `76` 이 되어 10배 어긋난 값이 정상 범위 안에
  /// 들어앉는다 — 검증도 안정화도 이 오류를 잡지 못한다. 그래서 단위 지원
  /// 여부를 엔진이 **선언**하게 하고, 스캐너가 시작 시점에 거른다.
  final Set<GlucoseUnit> supportedUnits;

  /// 라이브 프레임 스트림에 물릴 수 있는지. false 면 단발 촬영에만 쓴다.
  final bool supportsLiveStream;

  /// 이 엔진이 네트워크를 필요로 하는지.
  ///
  /// true 면 레지스트리가 **항상** 등록을 거부한다. OCR 은 단말에서만 돌아가며,
  /// 그 원칙을 문서가 아니라 코드로 강제한다. 서버 기반 비교 실험이 필요하면
  /// 앱이 아니라 PC 측 벤치마크 도구(`tools/ocr_bench`)에서 한다.
  final bool requiresNetwork;

  final int targetLatencyMs;
}

class OcrEngineConfig {
  const OcrEngineConfig({this.modelAssetPath, this.extras = const {}});

  final String? modelAssetPath;
  final Map<String, Object?> extras;
}

/// 모든 OCR 엔진이 구현하는 유일한 계약.
///
/// `interface` 한정자로 서브클래싱을 막고 구현만 허용한다. 엔진이 스캐너의 보정
/// 로직을 상속으로 우회하는 것을 컴파일 타임에 차단하기 위한 것이다.
///
/// **이 타입은 모듈 내부에 머문다.** 앱은 엔진을 직접 보지 않는다.
abstract interface class OcrEngine {
  OcrEngineDescriptor get descriptor;

  /// 모델 로딩 등 비용이 큰 준비 작업. 여러 번 호출해도 안전해야 한다.
  Future<void> initialize(OcrEngineConfig config);

  /// [initialize] 이후 실제로 인식을 수행할 수 있는 상태인지.
  ///
  /// 모델 에셋이 없는 빌드처럼 "엔진 객체는 만들어졌지만 쓸 수는 없는" 상태가
  /// 존재한다. 이걸 첫 프레임에서야 알게 되면 사용자는 반응 없는 스캐너를
  /// 들여다보게 되므로, 스캐너가 시작 시점에 확인해 곧바로 수동 입력으로 안내한다.
  bool get isReady;

  /// 프레임 하나를 읽는다. 예외를 던지지 말고 [OcrResult.failed] 로 돌려준다.
  Future<OcrResult> recognize(OcrFrame frame);

  Future<void> dispose();
}
