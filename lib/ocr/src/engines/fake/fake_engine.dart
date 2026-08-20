import '../../../../domain/models/glucose_unit.dart';
import '../../engine/ocr_engine.dart';
import '../../engine/ocr_frame.dart';
import '../../engine/ocr_result.dart';

/// 미리 정한 결과를 순서대로 돌려주는 테스트용 엔진.
///
/// `lib/` 에 두는 이유: integration_test 가 실제 카메라·모델 없이 스캔 →
/// 저장 → 리포트 전 경로를 돌릴 수 있어야 하는데, 통합 테스트는 `test/` 의
/// 헬퍼를 가져다 쓸 수 없다. 공개 경로는 `package:sugarscan/ocr/testing.dart`.
class FakeOcrEngine implements OcrEngine {
  FakeOcrEngine({
    required this.script,
    this.latency = const Duration(milliseconds: 1),
    this.loop = true,
    this.failure,
    Set<GlucoseUnit> supportedUnits = const {
      GlucoseUnit.mgdl,
      GlucoseUnit.mmoll,
    },
  }) : descriptor = OcrEngineDescriptor(
          id: engineId,
          displayName: 'Fake engine (test)',
          kind: OcrEngineKind.fake,
          acceptedFormats: const {
            OcrImageFormat.grayscale8,
            OcrImageFormat.nv21,
            OcrImageFormat.bgra8888,
            OcrImageFormat.png,
          },
          supportedUnits: supportedUnits,
          targetLatencyMs: 1,
        );

  /// 프레임마다 순서대로 방출할 결과. 각 항목은 (읽은 글자, 확신도).
  final List<(String, double)> script;

  final Duration latency;

  /// script 를 다 쓰면 처음부터 반복할지. false 면 이후 noTextFound.
  final bool loop;

  /// 설정되면 항상 이 실패를 돌려준다. 엔진 오류 경로 테스트용.
  final OcrFailure? failure;

  static const String engineId = 'fake';

  int _cursor = 0;
  bool _initialized = false;

  int get callCount => _cursor;

  @override
  final OcrEngineDescriptor descriptor;

  @override
  Future<void> initialize(OcrEngineConfig config) async {
    _initialized = true;
  }

  @override
  bool get isReady => _initialized;

  @override
  Future<OcrResult> recognize(OcrFrame frame) async {
    if (!_initialized) {
      return const OcrResult.failed(
        engineId: engineId,
        latency: Duration.zero,
        failure: OcrFailure(OcrFailureKind.notInitialized),
      );
    }
    if (latency > Duration.zero) {
      await Future<void>.delayed(latency);
    }

    final forced = failure;
    if (forced != null) {
      return OcrResult.failed(
        engineId: engineId,
        latency: latency,
        failure: forced,
      );
    }

    if (script.isEmpty || (!loop && _cursor >= script.length)) {
      _cursor++;
      return OcrResult.failed(
        engineId: engineId,
        latency: latency,
        failure: const OcrFailure(OcrFailureKind.noTextFound),
      );
    }

    final (text, confidence) = script[_cursor % script.length];
    _cursor++;
    return OcrResult(
      engineId: engineId,
      candidates: [OcrCandidate(rawText: text, confidence: confidence)],
      latency: latency,
    );
  }

  @override
  Future<void> dispose() async {
    _initialized = false;
  }
}
