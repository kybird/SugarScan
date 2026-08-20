import 'dart:typed_data';

import 'package:image/image.dart' as img;

import '../../engine/ocr_engine.dart';
import '../../engine/ocr_frame.dart';
import '../../engine/ocr_result.dart';
import 'display_assembler.dart';
import 'frame_quality.dart';
import 'gray_image.dart';
import 'lcd_binarizer.dart';
import 'meter_profile.dart';
import 'segment_patterns.dart';
import 'segment_sampler.dart';

/// 규칙 기반 7-세그먼트 판독 엔진.
///
/// 학습 모델을 쓰지 않는다. 7-세그먼트는 표현 가능한 상태가 유한하고 각 숫자의
/// 구조가 명시적이므로, "이 그림이 7인가"를 학습할 필요 없이
/// `획 7개의 켜짐 여부 → 7비트 → 대응표` 로 결정할 수 있다.
///
/// 이 방식이 CNN 대비 갖는 실질적 이점:
/// - **소수점을 읽는다.** 별도 영역을 따로 재므로 `102.5` 와 `1025` 를 구분한다.
///   덕분에 mmol/L 을 지원할 수 있다.
/// - **모르는 것을 모른다고 말한다.** 해밍 거리와 동점 여부로 판독 불가를
///   명시적으로 판정한다. 분류기는 언제나 가장 그럴듯한 클래스를 내놓는다.
/// - 학습 데이터도, 모델 에셋도, 재학습 파이프라인도 필요 없다.
///
/// 한계: 자릿수 위치를 알아야 한다([MeterProfile]). 사용자가 가이드 박스에
/// 화면을 맞추는 전제이며, 원근 보정은 아직 없다(정면 촬영 가정).
class SegmentRuleEngine implements OcrEngine {
  SegmentRuleEngine({
    MeterProfile? profile,
    this.blurThreshold = FrameQualityGate.minBlurScore,
    this.minSeparability = 0.25,
  }) : profile = profile ?? MeterProfile.uniform(digitCount: 4);

  static const String engineId = 'segment_rule_v1';

  final MeterProfile profile;

  /// 초점 판정 기준. 실촬 골든셋 확보 후 재보정 대상.
  final double blurThreshold;

  /// 전경/배경이 갈라지는 최소 정도. 낮으면 잡음에서 숫자가 만들어진다.
  final double minSeparability;

  bool _initialized = false;

  @override
  final OcrEngineDescriptor descriptor = const OcrEngineDescriptor(
    id: engineId,
    displayName: '7-segment rule decoder',
    kind: OcrEngineKind.rule,
    acceptedFormats: {
      OcrImageFormat.png,
      OcrImageFormat.jpeg,
      OcrImageFormat.bgra8888,
      OcrImageFormat.grayscale8,
    },
    // 소수점을 직접 검출하므로 두 단위를 모두 읽을 수 있다.
    supportsLiveStream: true,
    targetLatencyMs: 40,
  );

  @override
  Future<void> initialize(OcrEngineConfig config) async {
    _initialized = true;
  }

  /// 모델 에셋도 런타임도 없다. 초기화만 되면 항상 동작한다.
  @override
  bool get isReady => _initialized;

  @override
  Future<OcrResult> recognize(OcrFrame frame) async {
    final stopwatch = Stopwatch()..start();

    if (!_initialized) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: const OcrFailure(OcrFailureKind.notInitialized),
      );
    }
    if (!descriptor.acceptedFormats.contains(frame.format)) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: OcrFailure(
          OcrFailureKind.unsupportedFormat,
          '${frame.format.name} 은(는) 아직 지원하지 않습니다.',
        ),
      );
    }

    final gray = _toGray(frame);
    if (gray == null) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: const OcrFailure(
          OcrFailureKind.unknown,
          '프레임을 디코딩하지 못했습니다.',
        ),
      );
    }

    final roi = _cropRoi(gray, frame.roi);

    // 흐릿한 프레임은 해독하지 않는다. 뭉개진 세그먼트에서 나온 그럴듯한
    // 오답이 시간 투표에 섞이면 전체가 오염된다.
    final quality = FrameQualityGate.evaluate(roi, blurThreshold: blurThreshold);
    if (quality.rejected) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: OcrFailure(OcrFailureKind.noTextFound, quality.reason),
      );
    }

    final binary = LcdBinarizer.binarize(
      roi,
      forceDarkOnLight: profile.forceDarkOnLight,
    );
    if (binary.separability < minSeparability) {
      return OcrResult.failed(
        engineId: engineId,
        latency: stopwatch.elapsed,
        failure: OcrFailure(
          OcrFailureKind.noTextFound,
          '표시를 배경과 구분하지 못했습니다 '
          '(${binary.separability.toStringAsFixed(2)})',
        ),
      );
    }

    final cells = <CellReading>[];
    for (final cellRect in profile.digitCells) {
      final sample =
          SegmentSampler.sample(binary, cellRect, profile.geometry);
      cells.add(
        CellReading(
          glyph: SegmentPatternTable.match(sample.bits),
          decimalPoint: SegmentSampler.hasDecimalPoint(sample),
          margin: sample.margin,
        ),
      );
    }

    final assembled = DisplayAssembler.assemble(cells);
    stopwatch.stop();

    return switch (assembled) {
      ReadingText(:final text, :final confidence) => OcrResult(
          engineId: engineId,
          candidates: [
            OcrCandidate(
              rawText: text,
              confidence: confidence,
              perCharConfidence: [
                for (final cell in cells)
                  if (cell.glyph is! BlankGlyph) cell.margin,
              ],
            ),
          ],
          latency: stopwatch.elapsed,
        ),
      ReadingUnreadable(:final problem) => OcrResult.failed(
          engineId: engineId,
          latency: stopwatch.elapsed,
          failure: OcrFailure(OcrFailureKind.noTextFound, problem.name),
        ),
    };
  }

  GrayImage? _toGray(OcrFrame frame) {
    try {
      if (frame.format == OcrImageFormat.grayscale8) {
        return GrayImage(
          pixels: Uint8List.fromList(frame.bytes),
          width: frame.width,
          height: frame.height,
        );
      }

      final decoded = switch (frame.format) {
        OcrImageFormat.png || OcrImageFormat.jpeg => img.decodeImage(frame.bytes),
        OcrImageFormat.bgra8888 => img.Image.fromBytes(
            width: frame.width,
            height: frame.height,
            bytes: frame.bytes.buffer,
            numChannels: 4,
            order: img.ChannelOrder.bgra,
          ),
        _ => null,
      };
      if (decoded == null) return null;

      final pixels = Uint8List(decoded.width * decoded.height);
      var i = 0;
      for (var y = 0; y < decoded.height; y++) {
        for (var x = 0; x < decoded.width; x++) {
          final pixel = decoded.getPixel(x, y);
          // ITU-R BT.601 휘도.
          pixels[i++] =
              (0.299 * pixel.r + 0.587 * pixel.g + 0.114 * pixel.b)
                  .round()
                  .clamp(0, 255);
        }
      }
      return GrayImage(
        pixels: pixels,
        width: decoded.width,
        height: decoded.height,
      );
    } on Object {
      return null;
    }
  }

  GrayImage _cropRoi(GrayImage source, NormalizedRect? roi) {
    if (roi == null) return source;
    return source.crop(
      (roi.left * source.width).round(),
      (roi.top * source.height).round(),
      (roi.width * source.width).round(),
      (roi.height * source.height).round(),
    );
  }

  @override
  Future<void> dispose() async {
    _initialized = false;
  }
}
