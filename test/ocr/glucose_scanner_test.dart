import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/ocr/ocr.dart';
import 'package:sugarscan/ocr/testing.dart';

/// 모듈 경계 테스트.
///
/// 여기서 검증하는 것은 "앱이 [ScanConfirmed] 를 그대로 믿어도 되는가" 하나다.
/// 보정·검증·합의가 전부 모듈 안에서 끝나는지를 결과 타입만 보고 확인한다.
void main() {
  OcrFrame frame() => OcrFrame(
        bytes: Uint8List(0),
        format: OcrImageFormat.png,
        width: 1,
        height: 1,
      );

  GlucoseScanner scannerWith(
    List<(String, double)> script, {
    OcrFailure? failure,
  }) {
    final registry = OcrEngineRegistry();
    final engine = FakeOcrEngine(
      script: script,
      failure: failure,
      latency: Duration.zero,
    );
    registry.register(engine.descriptor, () => engine);
    return GlucoseScanner(registry: registry);
  }

  Future<ScanOutcome> offerTimes(GlucoseScanner scanner, int times) async {
    late ScanOutcome outcome;
    for (var i = 0; i < times; i++) {
      outcome = await scanner.offer(frame());
    }
    return outcome;
  }

  group('시작 전 / 엔진 없음', () {
    test('start 하지 않고 프레임을 넣으면 사용 불가로 답한다', () async {
      final scanner = GlucoseScanner(registry: OcrEngineRegistry());
      final outcome = await scanner.offer(frame());

      expect(outcome, isA<ScanUnavailable>());
      expect((outcome as ScanUnavailable).reason,
          ScanUnavailableReason.notStarted);
    });

    test('등록된 엔진이 없으면 사용 불가로 답한다', () async {
      final scanner = GlucoseScanner(registry: OcrEngineRegistry());
      final outcome = await scanner.start(unit: GlucoseUnit.mgdl);

      expect(outcome, isA<ScanUnavailable>());
      expect((outcome as ScanUnavailable).reason, ScanUnavailableReason.noEngine);
    });
  });

  group('단위 지원', () {
    GlucoseScanner mgdlOnlyScanner() {
      final registry = OcrEngineRegistry();
      final engine = FakeOcrEngine(
        script: [('76', 0.99)],
        latency: Duration.zero,
        supportedUnits: const {GlucoseUnit.mgdl},
      );
      registry.register(engine.descriptor, () => engine);
      return GlucoseScanner(registry: registry);
    }

    test('소수점을 못 읽는 엔진뿐이면 mmol/L 스캔을 거부한다', () async {
      // 이 방어가 없으면 7.6 이 76 으로 읽혀 10배 어긋난 값이 정상 범위
      // 안에 들어앉는다. 검증기도 안정화기도 이 오류는 잡지 못한다.
      final outcome = await mgdlOnlyScanner().start(unit: GlucoseUnit.mmoll);

      expect(outcome, isA<ScanUnavailable>());
      expect((outcome as ScanUnavailable).reason,
          ScanUnavailableReason.unitNotSupported);
    });

    test('지원하는 단위면 정상적으로 시작한다', () async {
      final outcome = await mgdlOnlyScanner().start(unit: GlucoseUnit.mgdl);
      expect(outcome, isA<ScanScanning>());
    });

    test('엔진을 직접 지정해도 단위를 검사한다', () async {
      final registry = OcrEngineRegistry();
      final engine = FakeOcrEngine(
        script: const [],
        supportedUnits: const {GlucoseUnit.mgdl},
      );
      registry.register(engine.descriptor, () => engine);
      final scanner = GlucoseScanner(registry: registry);

      final outcome = await scanner.start(
        unit: GlucoseUnit.mmoll,
        engineId: FakeOcrEngine.engineId,
      );
      expect((outcome as ScanUnavailable).reason,
          ScanUnavailableReason.unitNotSupported);
    });
  });

  group('확정', () {
    test('같은 값이 연속 3회 → 확정된 숫자를 돌려준다', () async {
      final scanner = scannerWith([('138', 0.95)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      expect(await offerTimes(scanner, 2), isA<ScanScanning>());

      final outcome = await scanner.offer(frame());
      expect(outcome, isA<ScanConfirmed>());

      final confirmed = outcome as ScanConfirmed;
      expect(confirmed.value, 138);
      expect(confirmed.unit, GlucoseUnit.mgdl);
      expect(confirmed.valueMgdl, 138);
      expect(confirmed.engineId, FakeOcrEngine.engineId);
    });

    test('원문에 단위가 붙어 있어도 앱은 숫자만 받는다', () async {
      // 앱은 "mg/dL 을 떼어내야 한다"는 사실 자체를 몰라도 된다.
      final scanner = scannerWith([('138 mg/dL', 0.95)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      final outcome = await offerTimes(scanner, 3);
      expect((outcome as ScanConfirmed).value, 138);
    });

    test('글자 오인식도 모듈 안에서 교정된다', () async {
      final scanner = scannerWith([('1O5', 0.95)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      final outcome = await offerTimes(scanner, 3);
      expect((outcome as ScanConfirmed).value, 105);
    });

    test('mmol/L 모드에서는 정본 변환까지 끝나서 나온다', () async {
      final scanner = scannerWith([('7.6', 0.95)]);
      await scanner.start(unit: GlucoseUnit.mmoll);

      final confirmed = await offerTimes(scanner, 3) as ScanConfirmed;
      expect(confirmed.value, 7.6);
      expect(confirmed.unit, GlucoseUnit.mmoll);
      expect(confirmed.valueMgdl, closeTo(136.94, 0.01));
    });

    test('확정 후에는 합의가 비워져 곧바로 재확정되지 않는다', () async {
      final scanner = scannerWith([('138', 0.95)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      expect(await offerTimes(scanner, 3), isA<ScanConfirmed>());
      expect(await scanner.offer(frame()), isA<ScanScanning>());
    });
  });

  group('확정하지 않아야 하는 경우', () {
    test('단일 프레임 오인식은 확정을 미룬다', () async {
      final scanner = scannerWith([('138', 0.95), ('198', 0.95)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      // 값이 매 프레임 번갈아 나오므로 영원히 확정되지 않는다.
      expect(await offerTimes(scanner, 8), isA<ScanScanning>());
    });

    test('확신도가 낮으면 연속이어도 확정하지 않는다', () async {
      final scanner = scannerWith([('138', 0.4)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      expect(await offerTimes(scanner, 6), isA<ScanScanning>());
    });

    test('물리적으로 불가능한 값은 연속으로 나와도 확정되지 않는다', () async {
      final scanner = scannerWith([('950', 0.99)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      expect(await offerTimes(scanner, 6), isA<ScanScanning>());
    });

    test('mg/dL 인데 소수점이 읽히면 확정하지 않는다', () async {
      final scanner = scannerWith([('13.8', 0.99)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      expect(await offerTimes(scanner, 6), isA<ScanScanning>());
    });
  });

  group('혈당계 범위 초과 표시', () {
    test('LO 는 값 10 이 아니라 거부로 나온다', () async {
      // 앱이 이 판정을 직접 했다면 L→1, O→0 교정 때문에 저혈당이 평범한
      // 숫자로 저장됐을 것이다. 그래서 이 판정이 모듈 안에 있다.
      final scanner = scannerWith([('LO', 0.99)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      final outcome = await scanner.offer(frame());
      expect(outcome, isA<ScanRejected>());
      expect((outcome as ScanRejected).reason, ScanRejectionReason.meterLow);
    });

    test('HI 도 거부로 나온다', () async {
      final scanner = scannerWith([('HI', 0.99)]);
      await scanner.start(unit: GlucoseUnit.mgdl);

      final outcome = await scanner.offer(frame());
      expect((outcome as ScanRejected).reason, ScanRejectionReason.meterHigh);
    });
  });

  group('엔진 오류', () {
    test('모델 로딩 실패는 사용 불가로 전달된다', () async {
      final scanner = scannerWith(
        const [],
        failure: const OcrFailure(OcrFailureKind.modelUnavailable),
      );
      await scanner.start(unit: GlucoseUnit.mgdl);

      final outcome = await scanner.offer(frame());
      expect((outcome as ScanUnavailable).reason,
          ScanUnavailableReason.modelUnavailable);
    });

    test('아무것도 못 읽은 프레임은 오류가 아니다', () async {
      final scanner = scannerWith(const []);
      await scanner.start(unit: GlucoseUnit.mgdl);

      expect(await scanner.offer(frame()), isA<ScanScanning>());
    });

    test('엔진이 예외를 던져도 밖으로 새지 않는다', () async {
      final registry = OcrEngineRegistry();
      final engine = _ThrowingEngine();
      registry.register(engine.descriptor, () => engine);
      final scanner = GlucoseScanner(registry: registry);
      await scanner.start(unit: GlucoseUnit.mgdl);

      // 라이브 프레임 루프에서 예외가 새면 스캔 화면 전체가 죽는다.
      final outcome = await scanner.offer(frame());
      expect((outcome as ScanUnavailable).reason,
          ScanUnavailableReason.engineError);
    });
  });
}

class _ThrowingEngine implements OcrEngine {
  @override
  final OcrEngineDescriptor descriptor = const OcrEngineDescriptor(
    id: 'throwing',
    displayName: 'Throwing engine',
    kind: OcrEngineKind.fake,
    acceptedFormats: {OcrImageFormat.png},
  );

  @override
  Future<void> initialize(OcrEngineConfig config) async {}

  @override
  bool get isReady => true;

  @override
  Future<OcrResult> recognize(OcrFrame frame) async =>
      throw StateError('engine exploded');

  @override
  Future<void> dispose() async {}
}
