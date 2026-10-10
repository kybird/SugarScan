import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/ocr/ocr.dart';
import 'package:sugarscan/ocr/testing.dart';

const _networkDescriptor = OcrEngineDescriptor(
  id: 'anything_networked',
  displayName: 'Networked engine',
  kind: OcrEngineKind.onnx,
  acceptedFormats: {OcrImageFormat.png},
  requiresNetwork: true,
);

void main() {
  OcrFrame frame() => OcrFrame(
        bytes: Uint8List(0),
        format: OcrImageFormat.png,
        width: 1,
        height: 1,
      );

  test('엔진을 등록하고 활성화한다', () async {
    final registry = OcrEngineRegistry();
    final engine = FakeOcrEngine(script: [('138', 0.9)]);
    registry.register(engine.descriptor, () => engine);

    expect(registry.isRegistered(FakeOcrEngine.engineId), isTrue);
    expect(registry.available, hasLength(1));

    final active = await registry.activate(FakeOcrEngine.engineId);
    expect(identical(active, engine), isTrue);
    expect(registry.activeId, FakeOcrEngine.engineId);
  });

  test('네트워크를 요구하는 엔진은 항상 등록이 거부된다', () {
    // 조건부 허용 플래그를 두지 않는다. 플래그가 있으면 언젠가 켜지고,
    // 그 순간 온디바이스 원칙이 깨진다.
    final registry = OcrEngineRegistry();

    expect(
      () => registry.register(
        _networkDescriptor,
        () => FakeOcrEngine(script: const []),
      ),
      throwsA(isA<OcrEngineRegistrationError>()),
    );
    expect(registry.isRegistered(_networkDescriptor.id), isFalse);
  });

  test('id 가 중복되면 등록을 거부한다', () {
    final registry = OcrEngineRegistry();
    final engine = FakeOcrEngine(script: const []);
    registry.register(engine.descriptor, () => engine);

    expect(
      () => registry.register(engine.descriptor, () => engine),
      throwsA(isA<OcrEngineRegistrationError>()),
    );
  });

  test('등록되지 않은 엔진 활성화는 실패한다', () {
    final registry = OcrEngineRegistry();
    expect(
      () => registry.activate('nope'),
      throwsA(isA<OcrEngineRegistrationError>()),
    );
  });

  test('엔진이 없으면 activateFirst 는 null 을 돌려준다', () async {
    final registry = OcrEngineRegistry();
    expect(await registry.activateFirst(), isNull);
  });

  test('엔진 교체 시 이전 엔진을 dispose 한다', () async {
    final registry = OcrEngineRegistry();
    final first = FakeOcrEngine(script: [('138', 0.9)]);
    final second = FakeOcrEngine(script: [('140', 0.9)]);
    registry.register(first.descriptor, () => first);
    registry.register(
      const OcrEngineDescriptor(
        id: 'second',
        displayName: 'Second',
        kind: OcrEngineKind.fake,
        acceptedFormats: {OcrImageFormat.png},
      ),
      () => second,
    );

    await registry.activate(FakeOcrEngine.engineId);
    await registry.activate('second');

    // dispose 되면 initialize 플래그가 풀려 notInitialized 를 돌려준다.
    final result = await first.recognize(frame());
    expect(result.failure?.kind, OcrFailureKind.notInitialized);
    expect(registry.activeId, 'second');
  });

  group('부트스트랩', () {
    test('모델 에셋이 없는 환경에서도 스캔을 시작한다', () async {
      // 규칙 기반 판독기는 모델 에셋도 네이티브 런타임도 필요 없다.
      // 테스트 환경(TFLite 없음)에서도 그대로 동작해야 한다.
      final scanner = buildGlucoseScanner();
      final outcome = await scanner.start(unit: GlucoseUnit.mgdl);

      expect(outcome, isA<ScanScanning>());
      expect(scanner.activeEngineId, 'segment_rule_v1');
    });

    test('mmol/L 도 지원한다 — 규칙 판독기가 소수점을 읽는다', () async {
      final scanner = buildGlucoseScanner();
      final outcome = await scanner.start(unit: GlucoseUnit.mmoll);

      expect(outcome, isA<ScanScanning>());
      expect(scanner.activeEngineId, 'segment_rule_v1');
    });

    test('mgdl 첫 후보(bandnet_crnn)가 준비 안 되면 다음 엔진으로 넘어간다',
        () async {
      // 테스트 환경엔 ONNX 런타임이 없어 배포 엔진이 준비되지 못한다 —
      // 그래서 스캐너는 activateFirstReadyWhere 로 규칙 엔진에 도달한다.
      // 위 부트스트랩 검증과 같은 사실을 레지스트리 각도에서 고정한다.
      final scanner = buildGlucoseScanner();
      final outcome = await scanner.start(unit: GlucoseUnit.mgdl);

      expect(outcome, isA<ScanScanning>());
      expect(scanner.activeEngineId, isNot('bandnet_crnn_v1'));
    });
  });

  group('activateFirstReadyWhere', () {
    test('준비되지 않은 엔진은 건너뛰고 다음 후보를 활성화한다', () async {
      final registry = OcrEngineRegistry();
      final notReady = _NeverReadyEngine('not_ready');
      final ready = FakeOcrEngine(script: [('138', 0.9)]);
      registry.register(notReady.descriptor, () => notReady);
      registry.register(ready.descriptor, () => ready);

      final active = await registry.activateFirstReadyWhere(
        (descriptor) => descriptor.supportedUnits.contains(GlucoseUnit.mgdl),
      );

      expect(identical(active, ready), isTrue);
      expect(registry.activeId, FakeOcrEngine.engineId);
    });

    test('후보가 전부 준비되지 않으면 null 이고 활성 엔진도 없다', () async {
      final registry = OcrEngineRegistry();
      final notReady = _NeverReadyEngine('only_one');
      registry.register(notReady.descriptor, () => notReady);

      final active = await registry.activateFirstReadyWhere((_) => true);

      expect(active, isNull);
      expect(registry.activeId, isNull);
    });
  });
}

/// initialize 는 성공하지만 모델이 없어 isReady 가 거짓인 엔진 —
/// 애셋 없는 빌드의 배포판(ONNX)을 재현한다.
class _NeverReadyEngine implements OcrEngine {
  _NeverReadyEngine(this.id_);

  final String id_;

  @override
  OcrEngineDescriptor get descriptor => OcrEngineDescriptor(
        id: id_,
        displayName: 'never ready',
        kind: OcrEngineKind.onnx,
        acceptedFormats: const {OcrImageFormat.grayscale8},
      );

  bool _initialized = false;

  @override
  Future<void> initialize(OcrEngineConfig config) async {
    _initialized = true;
  }

  @override
  bool get isReady => false; // 모델 로드 실패 — 초기화돼도 쓸 수 없다

  @override
  Future<OcrResult> recognize(OcrFrame frame) async => OcrResult.failed(
        engineId: id_,
        latency: Duration.zero,
        failure: OcrFailure(
          _initialized
              ? OcrFailureKind.modelUnavailable
              : OcrFailureKind.notInitialized,
        ),
      );

  @override
  Future<void> dispose() async {}
}
