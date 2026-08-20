import '../../../domain/models/glucose_unit.dart';

/// 혈당계가 값 대신 범위 초과를 표시한 경우.
enum ScanRejectionReason {
  /// `HI` — 측정 상한을 넘었다.
  meterHigh,

  /// `LO` — 측정 하한 아래다.
  meterLow,
}

enum ScanUnavailableReason {
  /// `start()` 를 호출하지 않았다.
  notStarted,

  /// 사용할 수 있는 엔진이 없다.
  noEngine,

  /// 사용자의 표시 단위를 읽을 수 있는 엔진이 없다.
  ///
  /// 예: 소수점 클래스가 없는 모델뿐인데 사용자가 mmol/L 을 쓰는 경우.
  /// 잘못 읽느니 스캔을 포기하고 수동 입력으로 보낸다.
  unitNotSupported,

  /// 모델을 불러오지 못했다. 이 기기에서는 스캔이 불가능하다.
  modelUnavailable,

  /// 엔진이 복구 불가능한 오류를 냈다.
  engineError,
}

/// OCR 모듈이 앱에 돌려주는 **유일한** 타입.
///
/// 앱은 이 결과를 다시 판정하지 않는다. 보정·검증·프레임 간 합의는 모두 모듈
/// 안에서 끝났고, [ScanConfirmed] 가 나왔다는 것은 곧 "쓸 수 있는 값"이라는 뜻이다.
sealed class ScanOutcome {
  const ScanOutcome();
}

/// 아직 스캔을 시작하지 않았다.
final class ScanIdle extends ScanOutcome {
  const ScanIdle();
}

/// 읽는 중. 아직 확정 조건을 못 채웠다.
final class ScanScanning extends ScanOutcome {
  const ScanScanning({required this.progress, this.previewValue});

  /// 0.0 ~ 1.0. 확정까지 얼마나 왔는지. 테두리 애니메이션에 쓴다.
  final double progress;

  /// 지금 읽히고 있는 값. **저장하면 안 된다.** 흔들리는 중이라는 신호를
  /// 사용자에게 보여주기 위한 표시용이다.
  final String? previewValue;
}

/// 확정. 앱은 이 값을 그대로 쓴다.
final class ScanConfirmed extends ScanOutcome {
  const ScanConfirmed({
    required this.value,
    required this.unit,
    required this.confidence,
    required this.engineId,
    required this.rawText,
    required this.frameCount,
  });

  /// [unit] 기준으로 이미 보정·검증까지 끝난 값.
  final double value;
  final GlucoseUnit unit;

  /// 확정에 사용된 프레임들의 평균 확신도.
  final double confidence;

  /// 어느 엔진이 읽었는지. 기록에 남겨 나중에 오인식을 역추적한다.
  final String engineId;

  /// 엔진이 읽은 원문. 분석용이며 서버로 보내지 않는다.
  final String rawText;

  final int frameCount;

  /// 저장 정본. 앱은 단위 변환을 신경 쓸 필요가 없다.
  double get valueMgdl => unit.toMgdl(value);
}

/// 혈당계가 숫자를 표시하지 않았다. 오류가 아니라 측정 결과의 한 종류다.
final class ScanRejected extends ScanOutcome {
  const ScanRejected(this.reason);
  final ScanRejectionReason reason;
}

/// 이 기기·상태에서는 스캔할 수 없다. 앱은 수동 입력으로 안내한다.
final class ScanUnavailable extends ScanOutcome {
  const ScanUnavailable(this.reason);
  final ScanUnavailableReason reason;
}
