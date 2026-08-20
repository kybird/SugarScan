// 의존성 필드를 private 으로 유지한다. Dart 는 private 이름의 named parameter 를
// 허용하지 않으므로 initializing formal(`this._registry`)을 쓸 수 없다.
// ignore_for_file: prefer_initializing_formals

import '../../../core/result.dart';
import '../../../domain/models/glucose_unit.dart';
import '../../../domain/services/glucose_validator.dart';
import '../correction/reading_normalizer.dart';
import '../correction/reading_stabilizer.dart';
import '../engine/ocr_engine.dart';
import '../engine/ocr_engine_registry.dart';
import '../engine/ocr_frame.dart';
import '../engine/ocr_result.dart';
import '../pipeline/frame_throttler.dart';
import 'scan_outcome.dart';

/// OCR 모듈의 파사드. **앱이 접촉하는 유일한 지점이다.**
///
/// 엔진 선택, 유량 제어, 글자 보정, 값 검증, 프레임 간 합의가 전부 이 안에서
/// 끝난다. 앱은 [ScanConfirmed] 를 받으면 그 값을 그대로 쓰면 되고, 엔진이
/// ONNX 든 ML Kit 이든 알 필요가 없다.
///
/// 계약:
/// - [offer] 는 **절대 예외를 던지지 않는다.** 라이브 프레임 루프에서 예외가
///   새어 나가면 스캔 화면 전체가 죽는다.
/// - 네트워크를 쓰지 않는다. 레지스트리가 네트워크 엔진 등록을 막는다.
class GlucoseScanner {
  GlucoseScanner({
    required OcrEngineRegistry registry,
    ReadingNormalizer normalizer = const ReadingNormalizer(),
    GlucoseValidator validator = const GlucoseValidator(),
    ReadingStabilizer? stabilizer,
  })  : _registry = registry,
        _normalizer = normalizer,
        _validator = validator,
        _stabilizer = stabilizer ?? ReadingStabilizer();

  final OcrEngineRegistry _registry;
  final ReadingNormalizer _normalizer;
  final GlucoseValidator _validator;
  final ReadingStabilizer _stabilizer;
  final FrameThrottler _throttler = FrameThrottler();

  GlucoseUnit? _unit;
  ScanOutcome _last = const ScanIdle();

  ScanOutcome get lastOutcome => _last;

  /// 현재 활성 엔진 id. 기록에 남길 때만 쓴다.
  String? get activeEngineId => _registry.activeId;

  /// 스캔을 시작한다. [unit] 은 값 검증 기준이 되므로 사용자의 표시 단위를 넘긴다.
  Future<ScanOutcome> start({
    required GlucoseUnit unit,
    String? engineId,
    OcrEngineConfig? config,
  }) async {
    _unit = unit;
    _stabilizer.reset();
    _throttler.reset();

    try {
      final OcrEngine? engine;
      if (engineId != null) {
        engine = await _registry.activate(engineId, config: config);
      } else {
        // 사용자의 표시 단위를 읽을 수 있는 엔진만 후보로 삼는다.
        engine = await _registry.activateFirstWhere(
          (descriptor) => descriptor.supportedUnits.contains(unit),
          config: config,
        );
      }

      if (engine == null) {
        return _emit(
          _registry.isEmpty
              ? const ScanUnavailable(ScanUnavailableReason.noEngine)
              : const ScanUnavailable(ScanUnavailableReason.unitNotSupported),
        );
      }
      if (!engine.descriptor.supportedUnits.contains(unit)) {
        await _registry.deactivate();
        return _emit(
          const ScanUnavailable(ScanUnavailableReason.unitNotSupported),
        );
      }
      // 모델 에셋이 없는 빌드처럼 "엔진은 있지만 쓸 수 없는" 상태를 첫 프레임이
      // 아니라 여기서 잡는다. 사용자가 반응 없는 스캐너를 들여다보게 두지 않는다.
      if (!engine.isReady) {
        return _emit(
          const ScanUnavailable(ScanUnavailableReason.modelUnavailable),
        );
      }
    } on Object {
      return _emit(const ScanUnavailable(ScanUnavailableReason.engineError));
    }

    return _emit(const ScanScanning(progress: 0));
  }

  /// 프레임 하나를 넘긴다. 추론이 이미 진행 중이면 프레임은 버려지고
  /// 직전 상태가 그대로 돌아온다 — 앱이 드롭 여부를 판단할 필요는 없다.
  Future<ScanOutcome> offer(OcrFrame frame) async {
    final unit = _unit;
    if (unit == null) {
      return _emit(const ScanUnavailable(ScanUnavailableReason.notStarted));
    }
    final engine = _registry.active;
    if (engine == null) {
      return _emit(const ScanUnavailable(ScanUnavailableReason.noEngine));
    }

    final result = await _throttler.run(() => _recognizeSafely(engine, frame));
    if (result == null) return _last;

    return _emit(_interpret(result, unit));
  }

  /// 사용자가 다시 스캔할 때 호출한다. 누적된 프레임 합의를 비운다.
  void reset() {
    _stabilizer.reset();
    _last = _unit == null ? const ScanIdle() : const ScanScanning(progress: 0);
  }

  Future<void> stop() async {
    await _registry.deactivate();
    _stabilizer.reset();
    _throttler.reset();
    _unit = null;
    _last = const ScanIdle();
  }

  /// 엔진 계약상 예외를 던지지 않아야 하지만, 앱이 이 모듈을 신뢰하는 구조인
  /// 이상 그 신뢰가 엔진 구현의 성실함에 의존해서는 안 된다.
  Future<OcrResult> _recognizeSafely(OcrEngine engine, OcrFrame frame) async {
    try {
      return await engine.recognize(frame);
    } on Object catch (error) {
      return OcrResult.failed(
        engineId: engine.descriptor.id,
        latency: Duration.zero,
        failure: OcrFailure(OcrFailureKind.unknown, error.toString()),
      );
    }
  }

  ScanOutcome _interpret(OcrResult result, GlucoseUnit unit) {
    final failure = result.failure;
    if (failure != null) {
      return switch (failure.kind) {
        OcrFailureKind.modelUnavailable =>
          const ScanUnavailable(ScanUnavailableReason.modelUnavailable),
        OcrFailureKind.notInitialized ||
        OcrFailureKind.unsupportedFormat ||
        OcrFailureKind.unknown =>
          const ScanUnavailable(ScanUnavailableReason.engineError),
        // 아무것도 못 읽은 건 라이브 스캔에서 정상이다. 계속 읽는다.
        OcrFailureKind.noTextFound => _pending(null),
      };
    }

    final candidate = result.best;
    if (candidate == null) return _pending(null);

    final normalized = _normalizer.normalize(candidate.rawText);
    switch (normalized) {
      case MeterRangeReading(:final kind):
        // 값이 아니라 상태다. 합의를 리셋해 이전 숫자와 섞이지 않게 한다.
        _stabilizer.reset();
        return ScanRejected(
          kind == MeterRangeKind.high
              ? ScanRejectionReason.meterHigh
              : ScanRejectionReason.meterLow,
        );

      case UnreadableReading():
        return _pending(null);

      case NormalizedNumber(:final text):
        final parsed = _validator.parse(text, unit);
        // 검증에 실패한 값은 안정화기에 아예 넣지 않는다. 말이 안 되는 값이
        // 연속으로 나온다고 해서 확정되어서는 안 된다.
        if (parsed is! Ok<double, GlucoseValidationFailure>) {
          return _pending(null);
        }

        final outcome = _stabilizer.add(
          StabilizerObservation(text, candidate.confidence),
        );
        return switch (outcome) {
          StabilizerConfirmed(
            :final averageConfidence,
            :final frameCount,
          ) =>
            _confirm(
              value: parsed.value,
              unit: unit,
              confidence: averageConfidence,
              engineId: result.engineId,
              rawText: candidate.rawText,
              frameCount: frameCount,
            ),
          StabilizerPending(:final progress) =>
            ScanScanning(progress: progress, previewValue: text),
        };
    }
  }

  ScanOutcome _confirm({
    required double value,
    required GlucoseUnit unit,
    required double confidence,
    required String engineId,
    required String rawText,
    required int frameCount,
  }) {
    // 확정 즉시 비운다. 같은 값이 계속 들어와 중복 확정되는 것을 막는다.
    _stabilizer.reset();
    return ScanConfirmed(
      value: value,
      unit: unit,
      confidence: confidence,
      engineId: engineId,
      rawText: rawText,
      frameCount: frameCount,
    );
  }

  ScanOutcome _pending(String? preview) {
    final current = _last;
    final progress = current is ScanScanning ? current.progress : 0.0;
    return ScanScanning(progress: progress, previewValue: preview);
  }

  ScanOutcome _emit(ScanOutcome outcome) {
    _last = outcome;
    return outcome;
  }
}
