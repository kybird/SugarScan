import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/ocr/ocr.dart';
import 'package:sugarscan/ocr/testing.dart';

/// 크롭 전달 경로 — 엔진이 후보에 실은 크롭이 스캐너 결과에 그대로 담겨
/// 나오는지. 값 판정과 무관한 표시·기록용 부속물이라, 없는 엔진은 없는 대로
/// null 이어야 하고 확정에는 영향이 없어야 한다.
void main() {
  OcrFrame frame() => OcrFrame(
    bytes: Uint8List(4),
    format: OcrImageFormat.grayscale8,
    width: 2,
    height: 2,
  );

  final crop = OcrCrop(
    bytes: Uint8List.fromList([1, 2, 3, 4]),
    width: 2,
    height: 2,
  );

  GlucoseScanner scannerWith(FakeOcrEngine engine) {
    final registry = OcrEngineRegistry();
    registry.register(engine.descriptor, () => engine);
    return GlucoseScanner(registry: registry);
  }

  test('스캔 중 결과에 후보 크롭이 실린다', () async {
    final scanner = scannerWith(
      FakeOcrEngine(script: [('138', 0.9)], crop: crop, latency: Duration.zero),
    );
    await scanner.start(unit: GlucoseUnit.mgdl);

    final outcome = await scanner.offer(frame());

    final scanning = outcome as ScanScanning;
    expect(scanning.previewValue, '138');
    expect(identical(scanning.candidateCrop, crop), isTrue);
  });

  test('확정 결과에도 크롭이 실린다', () async {
    final scanner = scannerWith(
      FakeOcrEngine(script: [('138', 0.95)], crop: crop, latency: Duration.zero),
    );
    await scanner.start(unit: GlucoseUnit.mgdl);

    await scanner.offer(frame());
    await scanner.offer(frame());
    final outcome = await scanner.offer(frame());

    final confirmed = outcome as ScanConfirmed;
    expect(confirmed.value, 138);
    expect(identical(confirmed.confirmedCrop, crop), isTrue);
  });

  test('크롭을 내지 않는 엔진은 null 이어도 확정에는 지장 없다', () async {
    final scanner = scannerWith(
      FakeOcrEngine(script: [('138', 0.95)], latency: Duration.zero),
    );
    await scanner.start(unit: GlucoseUnit.mgdl);

    final first = await scanner.offer(frame());
    await scanner.offer(frame());
    final third = await scanner.offer(frame());

    expect((first as ScanScanning).candidateCrop, isNull);
    final confirmed = third as ScanConfirmed;
    expect(confirmed.confirmedCrop, isNull);
    expect(confirmed.value, 138);
  });

  test('읽지 못한 프레임(noTextFound)에서는 크롭도 사라진다', () async {
    // 빈 script 는 매 프레임 noTextFound 를 낸다.
    final scanner = scannerWith(
      FakeOcrEngine(script: [], crop: crop, latency: Duration.zero),
    );
    await scanner.start(unit: GlucoseUnit.mgdl);

    final outcome = await scanner.offer(frame());

    expect(outcome, isA<ScanScanning>());
    expect((outcome as ScanScanning).candidateCrop, isNull);
  });
}
