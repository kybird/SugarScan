/// 엔진이 읽어낸 후보 하나.
///
/// **모듈 내부 타입이다.** 앱은 이 타입을 보지 않는다. 엔진은 "이게 혈당값이다"
/// 라고 판정하지 않고 읽은 글자와 확신도만 돌려주며, 보정·검증·확정은 같은
/// 모듈 안의 스캐너가 끝낸다.
class OcrCandidate {
  const OcrCandidate({
    required this.rawText,
    required this.confidence,
    this.perCharConfidence = const [],
  });

  /// 엔진이 읽은 원문. 예: `138`, `7.6 mg/dL`, `1O5`(오인식 포함).
  final String rawText;

  /// 0.0 ~ 1.0.
  final double confidence;

  /// 글자별 확신도. 어느 자리가 흔들리는지 분석할 때 쓴다.
  final List<double> perCharConfidence;

  @override
  String toString() =>
      'OcrCandidate("$rawText", ${confidence.toStringAsFixed(2)})';
}

enum OcrFailureKind {
  /// 이 엔진이 처리할 수 없는 프레임 포맷.
  unsupportedFormat,

  /// initialize() 전에 호출됨.
  notInitialized,

  /// 모델 로딩 실패. 복구 불가이므로 스캐너가 사용 불가 상태로 전환한다.
  modelUnavailable,

  /// 프레임에서 아무것도 읽지 못함. 라이브 스캔에서는 정상적인 결과다.
  noTextFound,

  unknown,
}

class OcrFailure {
  const OcrFailure(this.kind, [this.message]);

  final OcrFailureKind kind;
  final String? message;

  @override
  String toString() =>
      'OcrFailure(${kind.name}${message == null ? '' : ': $message'})';
}

class OcrResult {
  const OcrResult({
    required this.engineId,
    required this.candidates,
    required this.latency,
    this.failure,
  });

  const OcrResult.failed({
    required this.engineId,
    required this.latency,
    required OcrFailure this.failure,
  }) : candidates = const [];

  final String engineId;

  /// 확신도 내림차순.
  final List<OcrCandidate> candidates;

  final Duration latency;
  final OcrFailure? failure;

  bool get hasCandidates => candidates.isNotEmpty;
  OcrCandidate? get best => candidates.isEmpty ? null : candidates.first;
}
