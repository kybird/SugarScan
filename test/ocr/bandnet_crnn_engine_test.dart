import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:sugarscan/ocr/testing.dart';

/// 배포 엔진 조립 검증 — 실모델 없이 [DeployOnnxModel] 가짜로 끝까지 돈다.
/// 전처리·디코드 규약은 deploy_preprocess_test·band_detector_test 가 고정한다.
class _FakeModel implements DeployOnnxModel {
  _FakeModel(this.outputs);

  final Map<String, Float32List> outputs;
  int runCount = 0;

  @override
  Future<Map<String, Float32List>> run(Float32List input) async {
    runCount++;
    return outputs;
  }

  @override
  Future<void> dispose() async {}
}

/// throwsOnRun: 모델 호출이 터지는 경우(플랫폼 채널 실패 등).
class _ThrowingModel implements DeployOnnxModel {
  @override
  Future<Map<String, Float32List>> run(Float32List input) async {
    throw StateError('session closed');
  }

  @override
  Future<void> dispose() async {}
}

void main() {
  // 격자 40×40, 셀 (20,10) 이 뜨겁고 ltrb=(50,50,100,100).
  // 640×640 프레임(scale 1, dx 0, dy 0)에서 레터박스 좌표 그대로:
  // (328−50, 168−50, 328+100, 168+100) = (278,118,428,268) — 면적비 0.055.
  Float32List detObj() {
    final obj = Float32List(1600);
    obj.fillRange(0, obj.length, -6.0);
    obj[10 * 40 + 20] = 2.1972246; // sigmoid ≈ 0.9
    return obj;
  }

  Float32List detReg() {
    final reg = Float32List(6400);
    const i = 10 * 40 + 20;
    reg[i] = 50;
    reg[1600 + i] = 50;
    reg[3200 + i] = 100;
    reg[4800 + i] = 100;
    return reg;
  }

  /// "127" 을 내는 리더 logits.
  Float32List readerLogits() {
    final out = Float32List(36 * 11);
    for (var t = 0; t < 36; t++) {
      out[t * 11 + 10] = 3.0;
    }
    out[5 * 11 + 1] = 5.0;
    out[12 * 11 + 2] = 5.0;
    out[20 * 11 + 7] = 5.0;
    return out;
  }

  OcrFrame grayFrame({int size = 640}) => OcrFrame(
        bytes: Uint8List(size * size)..fillRange(0, size * size, 114),
        format: OcrImageFormat.grayscale8,
        width: size,
        height: size,
      );

  test('검출 → 크롭 → 판독까지 끝내 값 후보를 낸다', () async {
    final engine = BandNetCrnnEngine(
      detectorLoader: () async =>
          _FakeModel({'obj': detObj(), 'reg': detReg()}),
      readerLoader: () async => _FakeModel({'logits': readerLogits()}),
    );
    await engine.initialize(const OcrEngineConfig());

    final result = await engine.recognize(grayFrame());

    expect(result.failure, isNull);
    expect(result.engineId, BandNetCrnnEngine.engineId);
    final candidate = result.best!;
    expect(candidate.rawText, '127');
    expect(candidate.perCharConfidence, hasLength(3));
    expect(candidate.confidence, candidate.perCharConfidence.reduce((a, b) => a < b ? a : b));
  });

  test('initialize 전 호출은 notInitialized', () async {
    final engine = BandNetCrnnEngine(
      detectorLoader: () async => _FakeModel({}),
      readerLoader: () async => _FakeModel({}),
    );
    final result = await engine.recognize(grayFrame());
    expect(result.failure?.kind, OcrFailureKind.notInitialized);
  });

  test('모델 로드 실패(빌드에 애셋 없음)는 modelUnavailable — 앱은 수동 입력으로',
      () async {
    final engine = BandNetCrnnEngine(
      detectorLoader: () async => null,
      readerLoader: () async => null,
    );
    await engine.initialize(const OcrEngineConfig());
    expect(engine.isReady, isFalse);

    final result = await engine.recognize(grayFrame());
    expect(result.failure?.kind, OcrFailureKind.modelUnavailable);
  });

  test('게이트 탈락(확신 낮음)은 noTextFound — 라이브에서 정상 상태', () async {
    final coldObj = Float32List(1600);
    coldObj.fillRange(0, coldObj.length, -6.0);
    final engine = BandNetCrnnEngine(
      detectorLoader: () async =>
          _FakeModel({'obj': coldObj, 'reg': detReg()}),
      readerLoader: () async => _FakeModel({'logits': readerLogits()}),
    );
    await engine.initialize(const OcrEngineConfig());

    final result = await engine.recognize(grayFrame());
    expect(result.failure?.kind, OcrFailureKind.noTextFound);
  });

  test('리더 빈 출력은 noTextFound', () async {
    final blankLogits = Float32List(36 * 11);
    for (var t = 0; t < 36; t++) {
      blankLogits[t * 11 + 10] = 3.0;
    }
    final engine = BandNetCrnnEngine(
      detectorLoader: () async =>
          _FakeModel({'obj': detObj(), 'reg': detReg()}),
      readerLoader: () async => _FakeModel({'logits': blankLogits}),
    );
    await engine.initialize(const OcrEngineConfig());

    final result = await engine.recognize(grayFrame());
    expect(result.failure?.kind, OcrFailureKind.noTextFound);
  });

  test('출력 형태가 계약과 다르면 unknown', () async {
    final engine = BandNetCrnnEngine(
      detectorLoader: () async => _FakeModel({'obj': Float32List(10)}),
      readerLoader: () async => _FakeModel({'logits': readerLogits()}),
    );
    await engine.initialize(const OcrEngineConfig());

    final result = await engine.recognize(grayFrame());
    expect(result.failure?.kind, OcrFailureKind.unknown);
  });

  test('모델 호출이 예외를 던져도 엔진은 예외를 밖으로 흘리지 않는다', () async {
    final engine = BandNetCrnnEngine(
      detectorLoader: () async => _ThrowingModel(),
      readerLoader: () async => _ThrowingModel(),
    );
    await engine.initialize(const OcrEngineConfig());

    final result = await engine.recognize(grayFrame());
    expect(result.failure?.kind, OcrFailureKind.unknown);
  });

  test('지원하지 않는 프레임 포맷은 unsupportedFormat', () async {
    final engine = BandNetCrnnEngine(
      detectorLoader: () async =>
          _FakeModel({'obj': detObj(), 'reg': detReg()}),
      readerLoader: () async => _FakeModel({'logits': readerLogits()}),
    );
    await engine.initialize(const OcrEngineConfig());

    final result = await engine.recognize(OcrFrame(
      bytes: Uint8List(0),
      format: OcrImageFormat.nv21,
      width: 4,
      height: 4,
    ));
    expect(result.failure?.kind, OcrFailureKind.unsupportedFormat);
  });

  test('png 프레임(사진 가져오기 경로)도 휘도로 풀어 읽는다', () async {
    final image = img.Image(width: 64, height: 64);
    img.fill(image, color: img.ColorRgb8(114, 114, 114));
    final engine = BandNetCrnnEngine(
      detectorLoader: () async =>
          _FakeModel({'obj': detObj(), 'reg': detReg()}),
      readerLoader: () async => _FakeModel({'logits': readerLogits()}),
    );
    await engine.initialize(const OcrEngineConfig());

    final result = await engine.recognize(OcrFrame(
      bytes: Uint8List.fromList(img.encodePng(image)),
      format: OcrImageFormat.png,
      width: 64,
      height: 64,
    ));

    // 64×64 → 640 확대: scale 10, dx 0, dy 0. 레터박스 상자 (278,118,428,268)의
    // 원본 좌표는 (27.8, 11.8, 42.8, 26.8) — 면적비 0.055 로 게이트 통과.
    expect(result.failure, isNull);
    expect(result.best?.rawText, '127');
  });

  test('dispose 뒤에는 notInitialized', () async {
    final detector = _FakeModel({'obj': detObj(), 'reg': detReg()});
    final engine = BandNetCrnnEngine(
      detectorLoader: () async => detector,
      readerLoader: () async => _FakeModel({'logits': readerLogits()}),
    );
    await engine.initialize(const OcrEngineConfig());
    await engine.dispose();

    final result = await engine.recognize(grayFrame());
    expect(result.failure?.kind, OcrFailureKind.notInitialized);
  });
}
