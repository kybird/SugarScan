import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/features/scan/scan_debug_recorder.dart';
import 'package:sugarscan/ocr/ocr.dart';

/// 스캔 증거 기록 — 파일 구성과 보존 상한, 그리고 "실패해도 조용하다" 계약.
/// 디렉터리를 주입해 순수 dart:io 로 검증한다.
void main() {
  OcrCrop cropOf(int w, int h) => OcrCrop(
    bytes: Uint8List.fromList(List<int>.filled(w * h, 128)),
    width: w,
    height: h,
  );

  OcrFrame fullFrame() => OcrFrame(
    bytes: Uint8List.fromList(List<int>.filled(16, 100)),
    format: OcrImageFormat.grayscale8,
    width: 4,
    height: 4,
  );

  ScanConfirmed confirmed({double value = 138}) => ScanConfirmed(
    value: value,
    unit: GlucoseUnit.mgdl,
    confidence: 0.9,
    engineId: 'fake',
    rawText: '138',
    frameCount: 3,
    confirmedCrop: cropOf(10, 4),
  );

  late Directory tmp;

  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('scan_debug_recorder_test');
  });

  tearDown(() async {
    if (await tmp.exists()) {
      await tmp.delete(recursive: true);
    }
  });

  ScanDebugRecorder recorder({int maxEvents = 300}) =>
      ScanDebugRecorder(Directory('${tmp.path}/ocr_debug'), maxEvents: maxEvents);

  List<Directory> events() => Directory('${tmp.path}/ocr_debug')
      .listSync()
      .whereType<Directory>()
      .toList();

  test('확정 시점에 크롭·전체 프레임·메타를 남긴다', () async {
    final r = recorder();
    for (var i = 0; i < 6; i++) {
      r.note(fullFrame(), cropOf(8, 3), '13$i');
    }
    await r.dumpConfirmed(confirmed());

    final dirs = events();
    expect(dirs, hasLength(1));
    final names = dirs.single
        .listSync()
        .map((e) => e.uri.pathSegments.last)
        .toSet();
    expect(
      names,
      containsAll(['confirmed.png', 'f0.png', 'f5.png', 'full.png', 'meta.json']),
    );

    final meta = jsonDecode(
      File('${dirs.single.path}/meta.json').readAsStringSync(),
    ) as Map<String, Object?>;
    expect(meta['value'], 138);
    expect(meta['valueMgdl'], 138);
    expect(meta['rawText'], '138');
    expect(meta['engineId'], 'fake');
    expect(meta['confidence'], 0.9);
    expect(meta['frameCount'], 3);
    expect(meta['fullFrame'], 'full.png');
    final frames = meta['frames']! as List<Object?>;
    expect(frames, hasLength(6));
    expect((frames.first as Map<String, Object?>)['value'], '130');
    expect((frames.last as Map<String, Object?>)['value'], '135');
  });

  test('링 버퍼는 크기를 넘는 프레임을 버린다', () async {
    final r = recorder();
    for (var i = 0; i < 10; i++) {
      r.note(fullFrame(), cropOf(4, 2), '1$i');
    }
    await r.dumpConfirmed(confirmed());

    final meta = jsonDecode(
      File('${events().single.path}/meta.json').readAsStringSync(),
    ) as Map<String, Object?>;
    final frames = meta['frames']! as List<Object?>;
    // 10개를 넣었지만 마지막 6개만 — 확정 합의(3연속) 직전 이야기를 잇는 데
    // 그만이다.
    expect(frames, hasLength(6));
    expect((frames.first as Map<String, Object?>)['value'], '14');
    expect((frames.last as Map<String, Object?>)['value'], '19');
  });

  test('보존 상한을 넘으면 오래된 이벤트부터 지운다', () async {
    final r = recorder(maxEvents: 2);
    for (var i = 0; i < 3; i++) {
      await r.dumpConfirmed(confirmed(value: 100.0 + i));
      // 이벤트 디렉터리 이름이 epoch 밀리초라 같은 밀리초면 겹친다.
      await Future<void>.delayed(const Duration(milliseconds: 2));
    }

    final dirs = events();
    expect(dirs, hasLength(2));
    // 마지막 두 이벤트(102, 101)가 남는다.
    final kept = dirs
        .map((d) => jsonDecode(
              File('${d.path}/meta.json').readAsStringSync(),
            ) as Map<String, Object?>)
        .map((m) => m['value'])
        .toSet();
    expect(kept, {101, 102});
  });

  test('기록 경로가 막혀 있어도 예외를 밖으로 새지 않는다', () async {
    // 디렉터리여야 할 자리에 파일이 있다 — 생성이 실패하는 상황의 대타.
    final blocker = File('${tmp.path}/blocker')..createSync();
    final r = ScanDebugRecorder(Directory(blocker.path));

    await r.dumpConfirmed(confirmed());
  });
}
