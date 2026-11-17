import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:image/image.dart' as img;
import 'package:path_provider/path_provider.dart';

import '../../ocr/ocr.dart';

/// 스캔 증거 이미지 기록 — **debug 빌드 전용.**
///
/// 목적은 오인식 사례 수집이다. 확정 순간의 크롭만으로는 "맞았다가 틀린 값으로
/// 수렴"한 사례의 수렴 과정이 안 보이므로, 직전 프레임들(합의에 못 미친 값
/// 포함)을 링 버퍼로 모아 확정 시점에 한꺼번에 남긴다. 나중에 모델을 개선할 때
/// 학습·분석 데이터로 쓴다.
///
/// 전부 로컬 파일이며 동기화·업로드 경로와는 완전히 분리되어 있다. 어떤 실패도
/// 예외를 밖으로 새지 않는다 — 스캔 루프가 이 기록 때문에 죽으면 본말전도다.
class ScanDebugRecorder {
  ScanDebugRecorder(this._baseDir, {this.maxEvents = 300});

  /// 문서 디렉터리 아래 `ocr_debug/` 를 기준으로 만든다. 실패하면 null —
  /// 호출자는 null 을 그대로 두면 기록이 꺼진다.
  static Future<ScanDebugRecorder?> create() async {
    try {
      final docs = await getApplicationDocumentsDirectory();
      return ScanDebugRecorder(Directory('${docs.path}/ocr_debug'));
    } on Object {
      return null;
    }
  }

  /// 이 상한을 넘으면 가장 오래된 이벤트부터 지운다.
  final int maxEvents;

  /// 확정에 필요한 연속 프레임(3)과 여유를 합친 크기. 스태빌라이저 창(6)과
  /// 같다 — 수렴 직전 이야기 전체가 담긴다.
  static const int _ringSize = 6;

  final Directory _baseDir;
  final List<_NotedFrame> _ring = [];
  OcrFrame? _latestFrame;

  /// 인식 프레임 하나를 기록해 둔다. IO 없이 참조만 쥐므로 매 프레임
  /// 불러도 부담이 없다.
  void note(OcrFrame frame, OcrCrop? crop, String? value) {
    _latestFrame = frame;
    _ring.add(
      _NotedFrame(
        ts: DateTime.now().millisecondsSinceEpoch,
        crop: crop,
        value: value,
      ),
    );
    if (_ring.length > _ringSize) {
      _ring.removeRange(0, _ring.length - _ringSize);
    }
  }

  /// 확정 시점의 증거 묶음을 디스크에 남긴다. 화면 전환을 막지 않도록
  /// 호출자는 await 하지 않아도 된다.
  Future<void> dumpConfirmed(ScanConfirmed confirmed) async {
    try {
      await _dump(confirmed);
    } on Object catch (error) {
      debugPrint('ScanDebugRecorder: 기록 실패(무시) - $error');
    }
  }

  Future<void> _dump(ScanConfirmed confirmed) async {
    final ts = DateTime.now().millisecondsSinceEpoch;
    final eventDir = Directory('${_baseDir.path}/$ts');
    await eventDir.create(recursive: true);

    // 확정 프레임의 크롭. 링의 마지막 항목과 같은 참조일 때가 대부분이지만,
    // 확정 크롭이 없는 엔진일 때도 메타는 남긴다.
    await _writePng(eventDir, 'confirmed.png', confirmed.confirmedCrop);

    final frames = <Map<String, Object?>>[];
    for (var i = 0; i < _ring.length; i++) {
      final noted = _ring[i];
      final name = 'f$i.png';
      final written = await _writePng(eventDir, name, noted.crop);
      frames.add({
        'file': written ? name : null,
        'value': noted.value,
        'ts': noted.ts,
      });
    }

    final full = _latestFrame;
    final fullWritten = full != null && full.format == OcrImageFormat.grayscale8
        ? await _tryWritePng(
            eventDir,
            'full.png',
            full.bytes,
            full.width,
            full.height,
          )
        : false;

    final meta = {
      'ts': ts,
      'value': confirmed.value,
      'unit': confirmed.unit.name,
      'valueMgdl': confirmed.valueMgdl,
      'rawText': confirmed.rawText,
      'engineId': confirmed.engineId,
      'confidence': confirmed.confidence,
      'frameCount': confirmed.frameCount,
      'fullFrame': fullWritten ? 'full.png' : null,
      'frames': frames,
    };
    await File('${eventDir.path}/meta.json').writeAsString(
      const JsonEncoder.withIndent('  ').convert(meta),
    );

    await _enforceRetention();
    _ring.clear();
  }

  /// grayscale8 바이트를 PNG 로 저장. 성공 여부를 돌려준다(없는 크롭은 false).
  Future<bool> _writePng(Directory dir, String name, OcrCrop? crop) async {
    if (crop == null) return false;
    return _tryWritePng(dir, name, crop.bytes, crop.width, crop.height);
  }

  Future<bool> _tryWritePng(
    Directory dir,
    String name,
    Uint8List bytes,
    int width,
    int height,
  ) async {
    try {
      // package:image 의 fromBytes 는 ByteBuffer 를 받는데, 들어온 Uint8List 가
      // 더 큰 버퍼의 뷰일 수 있어 buffer 를 그대로 쓰면 안전하지 않다.
      // 덤프는 확정마다 한 번이라 복사 비용을 감수한다.
      final exact = Uint8List.fromList(bytes);
      final image = img.Image.fromBytes(
        bytes: exact.buffer,
        width: width,
        height: height,
        numChannels: 1,
      );
      await File('${dir.path}/$name').writeAsBytes(img.encodePng(image));
      return true;
    } on Object catch (error) {
      debugPrint('ScanDebugRecorder: $name 저장 실패(무시) - $error');
      return false;
    }
  }

  Future<void> _enforceRetention() async {
    if (!await _baseDir.exists()) return;
    final events = await _baseDir.list(followLinks: false).toList();
    final dirs = events.whereType<Directory>().toList()
      ..sort((a, b) => a.path.compareTo(b.path));
    final excess = dirs.length - maxEvents;
    for (var i = 0; i < excess; i++) {
      try {
        await dirs[i].delete(recursive: true);
      } on Object catch (error) {
        debugPrint('ScanDebugRecorder: 오래된 이벤트 삭제 실패(무시) - $error');
      }
    }
  }
}

class _NotedFrame {
  const _NotedFrame({required this.ts, this.crop, this.value});

  final int ts;
  final OcrCrop? crop;
  final String? value;
}
