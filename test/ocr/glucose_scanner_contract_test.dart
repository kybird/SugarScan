import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/core/result.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/services/glucose_validator.dart';
import 'package:sugarscan/ocr/ocr.dart';
import 'package:sugarscan/ocr/testing.dart';

/// `offer()` 는 **절대 예외를 던지지 않는다** — 그 계약을 고정한다.
///
/// 예전에는 엔진 호출만 try 로 감쌌다. 하지만 정규화·검증·안정화도 같은
/// 메서드 안에서 돌고, 그중 하나가 던지면 라이브 프레임 루프가 죽어 스캔 화면
/// 전체가 멈춘다. 엔진이 아닌 부품이 터지는 경우까지 여기서 막는다.
class _ExplodingValidator extends GlucoseValidator {
  const _ExplodingValidator();

  @override
  Result<double, GlucoseValidationFailure> parse(String text, GlucoseUnit unit) {
    throw StateError('검증기가 터졌다');
  }
}

void main() {
  OcrFrame frame() => OcrFrame(
        bytes: Uint8List(0),
        format: OcrImageFormat.png,
        width: 1,
        height: 1,
      );

  GlucoseScanner scannerWith(
    List<(String, double)> script, {
    GlucoseValidator validator = const GlucoseValidator(),
  }) {
    final registry = OcrEngineRegistry();
    final engine = FakeOcrEngine(script: script, latency: Duration.zero);
    registry.register(engine.descriptor, () => engine);
    return GlucoseScanner(registry: registry, validator: validator);
  }

  test('엔진이 아닌 부품이 던져도 offer 는 예외를 흘리지 않는다', () async {
    final scanner = scannerWith(
      [('138', 0.99)],
      validator: const _ExplodingValidator(),
    );
    await scanner.start(unit: GlucoseUnit.mgdl);

    final outcome = await scanner.offer(frame());

    expect(outcome, isA<ScanUnavailable>());
    expect(
      (outcome as ScanUnavailable).reason,
      ScanUnavailableReason.engineError,
    );
  });

  test('터진 뒤에도 다음 프레임을 계속 받는다 — 루프가 죽지 않는다', () async {
    final scanner = scannerWith(
      [('138', 0.99), ('138', 0.99)],
      validator: const _ExplodingValidator(),
    );
    await scanner.start(unit: GlucoseUnit.mgdl);

    await scanner.offer(frame());
    // 두 번째 호출도 던지지 않아야 한다. 던지면 프레임 스트림이 끊긴다.
    expect(await scanner.offer(frame()), isA<ScanUnavailable>());
  });

  test('stop 뒤에 돌아온 프레임은 확정하지 않는다', () async {
    // 단위가 바뀐 채 확정되면 값의 의미가 뒤집힌다(10~50 은 두 단위 모두
    // 검증을 통과한다). 세션이 끝난 프레임은 결과를 버려야 한다.
    final scanner = scannerWith([('138', 0.99)]);
    await scanner.start(unit: GlucoseUnit.mgdl);

    final inFlight = scanner.offer(frame());
    await scanner.stop();
    final outcome = await inFlight;

    expect(outcome, isNot(isA<ScanConfirmed>()));
  });
}
