import 'dart:typed_data';

import 'package:image/image.dart' as img;

import '../../../../domain/models/glucose_unit.dart';
import '../../engine/ocr_engine.dart';
import '../../engine/ocr_frame.dart';
import '../../engine/ocr_result.dart';
import 'band_detector.dart';
import 'crnn_ctc.dart';
import 'deploy_model.dart';
import 'deploy_preprocess.dart';

/// 학습 파이프라인의 배포판 — BandNet 밴드 검출기 → CRNN CTC 리더.
///
/// 체크포인트(2026-10-10 프리징): 검출기 `band_out/tone/ftk5_g0.06` ×
/// 리더 `reader_out/rftk5_foldall/best.pt`. K=5 교차검증 기대 판독률
/// 99.4%(실촉 2,504장 중 오독 15) · 검출 실패 0. 변환·파리티 자는
/// `assets_dev/train/export_deploy_onnx.py` 다.
///
/// ROI 가 있는 카메라·수동 정렬 프레임은 ROI 크롭 → 리더로 직행한다.
/// ROI 가 없는 사진은 eval_e2e_bandnet.py 와 같은
/// 단계다: grayscale → letterbox 640(패드 114, /255) → obj/reg → argmax
/// 디코드 → 게이트(확신 0.25 · 면적비 0.02) → 크롭 → 144×96(/255−0.5)
/// → CTC greedy. 앱 단의 값 검증(범위)과 프레임 합의는 스캐너가 이미
/// 하고 있어 이 엔진은 여기에 중복하지 않는다.
///
/// **mg/dL 전용이다.** charset 이 0~9 라 소수점이 없어 mmol/L 을 읽으면
/// `7.6` 이 `76` 이 된다(sevenseg_cnn 과 같은 이유로 descriptor 가 선언).
class BandNetCrnnEngine implements OcrEngine {
  BandNetCrnnEngine({
    required Future<DeployOnnxModel?> Function() detectorLoader,
    required Future<DeployOnnxModel?> Function() readerLoader,
  }) : _loadDetector = detectorLoader,
       _loadReader = readerLoader;

  static const String engineId = 'bandnet_crnn_v1';
  static const String detectorAssetPath = 'assets/models/band_detector.onnx';
  static const String readerAssetPath = 'assets/models/reader_crnn.onnx';

  final Future<DeployOnnxModel?> Function() _loadDetector;
  final Future<DeployOnnxModel?> Function() _loadReader;

  DeployOnnxModel? _detector;
  DeployOnnxModel? _reader;
  bool _initialized = false;

  @override
  final OcrEngineDescriptor descriptor = const OcrEngineDescriptor(
    id: engineId,
    displayName: 'BandNet 검출 + CRNN 리더 (ONNX)',
    kind: OcrEngineKind.onnx,
    acceptedFormats: {
      OcrImageFormat.grayscale8, // 카메라 경로(CameraFrameConverter)
      OcrImageFormat.png, // 사진 가져오기 경로
      OcrImageFormat.jpeg,
    },
    supportedUnits: {GlucoseUnit.mgdl},
    targetLatencyMs: 300,
  );

  @override
  Future<void> initialize(OcrEngineConfig config) async {
    _detector ??= await _loadDetector();
    _reader ??= await _loadReader();
    _initialized = true;
  }

  @override
  bool get isReady => _initialized && _detector != null && _reader != null;

  @override
  Future<OcrResult> recognize(OcrFrame frame) async {
    final stopwatch = Stopwatch()..start();

    if (!_initialized) {
      return _failed(
        const OcrFailure(OcrFailureKind.notInitialized),
        stopwatch,
      );
    }
    final detector = _detector;
    final reader = _reader;
    if (detector == null || reader == null) {
      return _failed(
        const OcrFailure(
          OcrFailureKind.modelUnavailable,
          '배포 모델(band_detector/reader_crnn .onnx)을 불러오지 못했습니다.',
        ),
        stopwatch,
      );
    }
    if (!descriptor.acceptedFormats.contains(frame.format)) {
      return _failed(
        OcrFailure(
          OcrFailureKind.unsupportedFormat,
          '${frame.format.name} 은(는) 아직 지원하지 않습니다.',
        ),
        stopwatch,
      );
    }

    final gray = _toGray(frame);
    if (gray == null) {
      return _failed(
        const OcrFailure(OcrFailureKind.unknown, '프레임을 디코딩하지 못했습니다.'),
        stopwatch,
      );
    }

    final ({int x0, int y0, int x1, int y1})? rect;
    final roi = frame.roi;
    if (roi != null) {
      // 가이드에 맞춘 숫자 밴드는 이미 위치가 주어졌다. 검출기를 다시
      // 거치면 ROI 밖의 숫자줄을 고르거나 면적 게이트에서 탈락할 수 있다.
      rect = _roiRect(roi, gray.width, gray.height);
    } else {
      // ① 사진 검출: ROI 가 없는 전체 프레임에서 밴드를 찾는다.
      final letterboxed = DeployPreprocess.letterbox(
        gray.bytes,
        gray.width,
        gray.height,
        BandDetector.inputSize,
      );
      final detOutputs = await _runModel(detector, letterboxed.pixels);
      if (detOutputs == null) {
        return _failed(const OcrFailure(OcrFailureKind.unknown), stopwatch);
      }
      final obj = detOutputs['obj'];
      final reg = detOutputs['reg'];
      if (obj == null ||
          reg == null ||
          obj.length != _objCells ||
          reg.length != 4 * _objCells) {
        return _failed(
          const OcrFailure(OcrFailureKind.unknown, '검출기 출력 형태가 예상과 다릅니다.'),
          stopwatch,
        );
      }

      final box = BandDetector.decode(
        obj,
        reg,
        scale: letterboxed.scale,
        dx: letterboxed.dx,
        dy: letterboxed.dy,
        imageWidth: gray.width,
        imageHeight: gray.height,
      );
      rect = box == null
          ? null
          : BandDetector.cropRect(box, gray.width, gray.height);
    }
    if (rect == null) {
      // 게이트 탈락은 라이브 스캔의 정상 상태다 — 다음 프레임을 계속 읽는다.
      return _failed(const OcrFailure(OcrFailureKind.noTextFound), stopwatch);
    }

    // ② 판독: 밴드 크롭을 늘려 리더에.
    final cropW = rect.x1 - rect.x0;
    final cropH = rect.y1 - rect.y0;
    final rawCrop = _crop(gray, rect);
    final crop = DeployPreprocess.resizeBilinear(
      rawCrop,
      cropW,
      cropH,
      _readerInW,
      _readerInH,
    );
    final readerOutputs = await _runModel(
      reader,
      DeployPreprocess.readerInput(crop),
    );
    if (readerOutputs == null) {
      return _failed(const OcrFailure(OcrFailureKind.unknown), stopwatch);
    }
    final logits = readerOutputs['logits'];
    if (logits == null ||
        logits.length != CrnnCtc.timeSteps * CrnnCtc.classCount) {
      return _failed(
        const OcrFailure(OcrFailureKind.unknown, '리더 출력 형태가 예상과 다릅니다.'),
        stopwatch,
      );
    }

    final reading = CrnnCtc.greedy(logits);
    if (reading.text.isEmpty) {
      return _failed(const OcrFailure(OcrFailureKind.noTextFound), stopwatch);
    }

    return OcrResult(
      engineId: engineId,
      candidates: [
        OcrCandidate(
          rawText: reading.text,
          confidence: reading.confidence,
          perCharConfidence: reading.perCharConfidence,
          // ROI 또는 검출기가 잡은 밴드를 원 해상도 그대로. 표시·기록용 참조라
          // 별도 복사는 하지 않는다.
          crop: OcrCrop(bytes: rawCrop, width: cropW, height: cropH),
        ),
      ],
      latency: stopwatch.elapsed,
    );
  }

  static const int _objCells = BandDetector.gridSize * BandDetector.gridSize;
  static const int _readerInH = 96;
  static const int _readerInW = 144;

  /// 정규화 ROI 의 네 경계를 원본 픽셀 경계로 반올림한다.
  /// 잘못된 ROI 를 전체 프레임으로 대체하면 다른 숫자를 읽을 수 있으므로
  /// 범위 밖·비유한 좌표와 너무 작은 영역은 미인식으로 돌린다.
  ({int x0, int y0, int x1, int y1})? _roiRect(
    NormalizedRect roi,
    int width,
    int height,
  ) {
    if (!roi.left.isFinite ||
        !roi.top.isFinite ||
        !roi.width.isFinite ||
        !roi.height.isFinite ||
        roi.left < 0 ||
        roi.top < 0 ||
        roi.width <= 0 ||
        roi.height <= 0 ||
        roi.right > 1 ||
        roi.bottom > 1) {
      return null;
    }
    final x0 = (roi.left * width).round();
    final y0 = (roi.top * height).round();
    final x1 = (roi.right * width).round();
    final y1 = (roi.bottom * height).round();
    if (x1 - x0 < 4 || y1 - y0 < 4) return null;
    return (x0: x0, y0: y0, x1: x1, y1: y1);
  }

  OcrResult _failed(OcrFailure failure, Stopwatch stopwatch) {
    stopwatch.stop();
    return OcrResult.failed(
      engineId: engineId,
      latency: stopwatch.elapsed,
      failure: failure,
    );
  }

  /// 모델 호출. 엔진 계약상 예외를 밖으로 흘리지 않는다.
  Future<Map<String, Float32List>?> _runModel(
    DeployOnnxModel model,
    Float32List input,
  ) async {
    try {
      return await model.run(input);
    } on Object {
      return null;
    }
  }

  ({Uint8List bytes, int width, int height})? _toGray(OcrFrame frame) {
    switch (frame.format) {
      case OcrImageFormat.grayscale8:
        if (frame.width <= 0 ||
            frame.height <= 0 ||
            frame.bytes.length < frame.width * frame.height) {
          return null;
        }
        return (bytes: frame.bytes, width: frame.width, height: frame.height);
      case OcrImageFormat.png:
      case OcrImageFormat.jpeg:
        return _decodeToGray(frame.bytes);
      default:
        return null;
    }
  }

  ({Uint8List bytes, int width, int height})? _decodeToGray(Uint8List encoded) {
    try {
      final decoded = img.decodeImage(encoded);
      if (decoded == null || decoded.width <= 0 || decoded.height <= 0) {
        return null;
      }
      final out = Uint8List(decoded.width * decoded.height);
      var i = 0;
      for (final pixel in decoded) {
        // ITU-R BT.601 휘도 — CameraFrameConverter 와 같은 식.
        final luma = (0.299 * pixel.r + 0.587 * pixel.g + 0.114 * pixel.b)
            .round()
            .clamp(0, 255);
        out[i++] = luma;
      }
      return (bytes: out, width: decoded.width, height: decoded.height);
    } on Object {
      return null;
    }
  }

  Uint8List _crop(
    ({Uint8List bytes, int width, int height}) gray,
    ({int x0, int y0, int x1, int y1}) rect,
  ) {
    final w = rect.x1 - rect.x0;
    final out = Uint8List(w * (rect.y1 - rect.y0));
    var o = 0;
    for (var y = rect.y0; y < rect.y1; y++) {
      final row = y * gray.width + rect.x0;
      for (var x = 0; x < w; x++) {
        out[o++] = gray.bytes[row + x];
      }
    }
    return out;
  }

  @override
  Future<void> dispose() async {
    _initialized = false;
    await _detector?.dispose();
    await _reader?.dispose();
    _detector = null;
    _reader = null;
  }
}
