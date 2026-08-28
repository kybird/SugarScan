// 실촬 골든셋 판독 벤치 — Datumo(TILDE) 혈당계 사진 2,512쌍으로 앱의 사진 경로를
// 통째로 잰다.
//
// scene_bench.dart 가 합성 장면(G16)을 물어 엔진 단독을 재었다면, 이쪽은
// **실사진이라 "표시를 찾는 일"부터 측정 대상이다.** 앱(scan_screen.dart)이
// 사진에서 거치는 경로를 그대로 따라간다:
//
//   파일 바이트 → preprocessPhotoForEngine()   (정렬 성공시 그 프레임)
//                └ 실패(null)면 원본 프레임 폴백             ← 앱과 동일
//              → SegmentRuleEngine.recognize()
//
// 라벨은 `assets_dev/upstream/datumo/labels.jsonl`(이미지 1장당 측정값 정수 GT).
// 엔진 구성은 생성 기본값 그대로다 — 벤치가 엔진을 조정하는 순간 기준선이
// 아니게 된다.
//
// 오독과 미인식을 한 칸에 합치지 않는 것은 scene_bench 와 같다. 합성과 달리
// margin·rotation·contrast 라벨이 없으므로 축 분해는 배치·자릿수·값구간으로
// 대체한다.
//
// 사용법
// ------
//   dart run tools/ocr_bench/bin/golden_bench.dart \
//     --labels assets_dev/upstream/datumo/labels.jsonl \
//     --root   assets_dev/upstream/datumo \
//     --out    docs/reports/goldenset-real-baseline.md
//
//   --limit N          일정 간격으로 N 장만 (빠른 확인용, 기본: 전부)
//   --dump-failures N  오독 사례 N 건 표 (기본 12)
//   --dump-hits N      정답 사례 N 건 표 (기본 8, 눈 검증용)

import 'dart:convert';
import 'dart:io';

import 'package:image/image.dart' as img;
import 'package:sugarscan/features/scan/lcd_band_detector.dart';
import 'package:sugarscan/features/scan/photo_preprocessor.dart';
import 'package:sugarscan/ocr/testing.dart';

void main(List<String> args) async {
  final opts = _Options.parse(args);
  if (opts == null) return;

  final labelsFile = File(opts.labelsPath);
  if (!labelsFile.existsSync()) {
    stderr.writeln('라벨을 찾을 수 없다: ${opts.labelsPath}');
    exitCode = 2;
    return;
  }
  var labels = labelsFile
      .readAsLinesSync()
      .where((line) => line.trim().isNotEmpty)
      .map(_Label.parse)
      .toList();
  if (labels.isEmpty) {
    stderr.writeln('labels.jsonl 이 비어 있다.');
    exitCode = 2;
    return;
  }
  if (opts.limit > 0 && labels.length > opts.limit) {
    // 앞에서 자르면 배치 순서(1차 전량 → 2차 꼬리)에 치우친다. 일정 간격.
    final stride = labels.length / opts.limit;
    labels = [
      for (var i = 0; i < opts.limit; i++) labels[(i * stride).floor()],
    ];
  }

  Map<String, List<({double x, double y})>> quads = {};
  if (opts.quadsPath != null) {
    for (final line in File(opts.quadsPath!)
        .readAsLinesSync()
        .where((l) => l.trim().isNotEmpty)) {
      final j = jsonDecode(line) as Map<String, dynamic>;
      quads[j['id'] as String] = [
        for (final pt in (j['quad'] as List))
          (x: (pt[0] as num).toDouble(), y: (pt[1] as num).toDouble()),
      ];
    }
    stdout.writeln('쿼드 ${quads.length}개 로드(${opts.quadsPath})');
  }

  stdout.writeln('${labels.length}장 …');

  final engine = SegmentRuleEngine();
  await engine.initialize(const OcrEngineConfig());

  final report = _Report()..align = opts.align;
  final wall = Stopwatch()..start();

  for (final label in labels) {
    final file = File(_join([opts.root, label.image]));
    if (!file.existsSync()) {
      report.recordMissing(label);
      continue;
    }

    // 앱 경로: 전처리 시도 → 실패면 원본 프레임 폴백. 디코딩 비용이 지배적일
    // 수 있어 전처리(내부 디코드 포함)와 엔진을 따로 잰다.
    final prepWatch = Stopwatch()..start();
    OcrFrame? prepared;
    if (opts.align == 'from-json') {
      final quad = opts.quadsPath == null ? null : quads[label.id];
      if (quad == null) {
        report.detectFail++;
        report.total++;
        continue;
      }
      try {
        prepared = warpQuadToEngineFrame(file.readAsBytesSync(), quad);
      } catch (_) {
        report.recordUndecodable(label);
        continue;
      }
      if (prepared == null) {
        report.warpFail++;
        report.total++;
        continue;
      }
      if (opts.relayout) {
        final laid = relayoutEngineFrame(prepared);
        if (laid == null) {
          report.relayoutFail++;
          report.total++;
          continue;
        }
        prepared = laid;
        report.relayoutOk++;
      }
    } else if (opts.align == 'auto') {
      // 자동 경로: 밴드 검출 → 4모서리 원근 펴기. 검출 실패는 원본 폴백이
      // 아니라 별도 카운터(전체 프레임 투입은 G17 에서 무의미가 확인됨).
      try {
        final quad = detectReadingQuad(file.readAsBytesSync());
        if (quad == null) {
          report.detectFail++;
          report.total++;
          continue;
        }
        prepared = warpQuadToEngineFrame(file.readAsBytesSync(), quad);
      } catch (_) {
        report.recordUndecodable(label);
        continue;
      }
      if (prepared == null) {
        report.warpFail++;
        report.total++;
        continue;
      }
    } else {
      try {
        prepared = preprocessPhotoForEngine(file.readAsBytesSync());
        // 실촬 파일은 어느 단계에서든 디코더 예외가 날 수 있다. 한 장의 죽음이
        // 전체 실행을 끊지 않게 각 단계를 고립한다.
      } catch (_) {
        report.recordUndecodable(label);
        continue;
      }
    }
    report.prepMicros += prepWatch.elapsedMicroseconds;

    final OcrFrame frame;
    if (prepared != null) {
      frame = prepared;
      report.prepared++;
    } else {
      final img.Image? decoded;
      try {
        decoded = img.decodeImage(file.readAsBytesSync());
      } catch (_) {
        report.recordUndecodable(label);
        continue;
      }
      if (decoded == null) {
        report.recordUndecodable(label);
        continue;
      }
      frame = OcrFrame(
        bytes: file.readAsBytesSync(),
        format: OcrImageFormat.png,
        width: decoded.width,
        height: decoded.height,
      );
      report.prepFallback++;
    }

    try {
      final sw = Stopwatch()..start();
      final result = await engine.recognize(frame);
      sw.stop();
      report.record(
        label,
        result,
        engineMicros: sw.elapsedMicroseconds.toDouble(),
        usedPrep: prepared != null,
      );
    } catch (_) {
      report.engineError++;
    }

    if (report.total % 100 == 0) {
      stdout.writeln(
        '… ${report.total}장 (정확 ${report.exact} · 오독 ${report.misread}'
        ' · 미인식 ${report.rejected})',
      );
    }
  }
  wall.stop();

  final markdown = report.render(
    labelsPath: opts.labelsPath,
    dumpFailures: opts.dumpFailures,
    dumpHits: opts.dumpHits,
    wall: wall,
  );
  stdout
    ..writeln()
    ..writeln(markdown);

  if (opts.outPath != null) {
    File(opts.outPath!).writeAsStringSync(markdown);
    stdout.writeln('리포트를 적었다: ${opts.outPath}');
  }
  stdout.writeln(report.summaryLine());
}

String _join(List<String> parts) => parts.join(Platform.pathSeparator);

String _normalize(String p) =>
    p.replaceAll('\\', '/').replaceFirst(RegExp(r'^\./'), '');

class _Label {
  _Label({
    required this.id,
    required this.image,
    required this.reading,
    required this.batch,
  });

  factory _Label.parse(String line) {
    final json = jsonDecode(line) as Map<String, dynamic>;
    final image = _normalize(json['image'] as String);
    final batch = image.split('/').firstWhere(
          (part) => part.startsWith('glucose_batch'),
          orElse: () => 'unknown',
        );
    return _Label(
      id: json['id'] as String,
      image: image,
      reading: (json['reading'] as num).toInt(),
      batch: batch,
    );
  }

  final String id;
  final String image;

  /// 이미지 1장당 측정값 GT (mg/dL 정수).
  final int reading;
  final String batch;

  String get valueText => '$reading';
  int get digitCount => valueText.length;

  /// 값구간 축 — 치료 판단이 아니라 세그먼트 구성이 급격히 바뀌는 밴드다.
  String get rangeBin {
    if (reading < 70) return '<70';
    if (reading <= 180) return '70~180';
    if (reading < 300) return '181~299';
    return '>=300';
  }
}

enum _Verdict { exact, numericOnly, misread }

class _Misread {
  _Misread(this.label, this.read, this.usedPrep);
  final _Label label;
  final String read;
  final bool usedPrep;
}

class _Hit {
  _Hit(this.label, this.read, this.usedPrep);
  final _Label label;
  final String read;
  final bool usedPrep;
}

class _BinStats {
  int total = 0;
  int exact = 0;

  /// 문자열은 다르지만 수치가 같은 판독(`095` ↔ `95`). 오독에서 뺀다.
  int numericOnly = 0;
  int misread = 0;
  int rejected = 0;
}

class _Report {
  int total = 0;
  int exact = 0;
  int numericOnly = 0;
  int misread = 0;

  /// 오독 중 자릿수 자체가 달라진 것(숫자↔숫자만).
  int misreadDigitChanged = 0;

  /// 숫자 라벨을 `HI`/`LO` 로 읽은 오독 — 범위판정 위험 직결.
  int numericReadAsHiLo = 0;

  int rejected = 0;
  int missing = 0;
  int undecodable = 0;

  /// 엔진이 예외로 죽은 표본 — 미인식과 별도 세운다(하네스·엔진 결함).
  int engineError = 0;
  int prepared = 0;
  int prepFallback = 0;
  int detectFail = 0;
  int warpFail = 0;
  int modelFail = 0;
  int relayoutOk = 0;
  int relayoutFail = 0;

  /// 정렬 경로 표기(리포트·요약줄용)
  String align = 'legacy';
  double prepMicros = 0;

  final Map<String, int> rejectReasons = {};
  final List<double> latenciesAll = [];
  final List<double> latenciesProduced = [];

  final List<_Misread> misreads = [];
  final List<_Hit> hits = [];

  final byBatch = <String, _BinStats>{};
  final List<_BinStats?> byDigits = [null, _BinStats(), _BinStats(), _BinStats()];
  final Map<String, _BinStats> byRange = {};

  void recordMissing(_Label label) {
    total++;
    missing++;
  }

  void recordUndecodable(_Label label) {
    total++;
    undecodable++;
  }

  void record(
    _Label label,
    OcrResult result, {
    required double engineMicros,
    required bool usedPrep,
  }) {
    total++;
    latenciesAll.add(engineMicros);

    final read = result.best?.rawText;
    if (read == null) {
      rejected++;
      rejectReasons.update(_rejectReason(result.failure), (v) => v + 1,
          ifAbsent: () => 1);
      _tally(label, null);
      return;
    }

    latenciesProduced.add(engineMicros);

    var verdict = _Verdict.misread;
    if (read == label.valueText) {
      verdict = _Verdict.exact;
    } else {
      final readNum = int.tryParse(read.replaceAll(RegExp(r'[^0-9]'), ''));
      if (readNum != null && readNum == label.reading) {
        verdict = _Verdict.numericOnly;
      }
    }

    _tally(label, verdict);
    switch (verdict) {
      case _Verdict.exact:
        exact++;
        if (hits.length < 500) hits.add(_Hit(label, read, usedPrep));
      case _Verdict.numericOnly:
        numericOnly++;
      case _Verdict.misread:
        misread++;
        if (read == 'HI' || read == 'LO') numericReadAsHiLo++;
        if (_isNumericText(read) && _digitCount(read) != label.digitCount) {
          misreadDigitChanged++;
        }
        if (misreads.length < 500) misreads.add(_Misread(label, read, usedPrep));
    }
  }

  void _tally(_Label label, _Verdict? verdict) {
    void put(_BinStats b) {
      b.total++;
      switch (verdict) {
        case _Verdict.exact:
          b.exact++;
        case _Verdict.numericOnly:
          b.numericOnly++;
        case _Verdict.misread:
          b.misread++;
        case null:
          b.rejected++;
      }
    }

    put(byBatch.putIfAbsent(label.batch, _BinStats.new));
    if (label.digitCount >= 1 && label.digitCount <= 3) {
      put(byDigits[label.digitCount]!);
    }
    put(byRange.putIfAbsent(label.rangeBin, _BinStats.new));
  }

  static String _rejectReason(OcrFailure? failure) {
    final message = failure?.message ?? '';
    if (message.startsWith('초점이 흐')) return 'blur';
    if (message.startsWith('표시를 배경과 구분하지 못했습니다')) {
      return 'separability';
    }
    return switch (message) {
      'blank' || 'unknownGlyph' || 'malformed' => message,
      _ => 'other',
    };
  }

  static int _digitCount(String s) =>
      s.replaceAll(RegExp(r'[^0-9]'), '').length;

  static bool _isNumericText(String s) =>
      s.isNotEmpty && RegExp(r'^[0-9.]+$').hasMatch(s);

  String render({
    required String labelsPath,
    required int dumpFailures,
    required int dumpHits,
    required Stopwatch wall,
  }) {
    final b = StringBuffer()
      ..writeln('# 실촬 골든셋 판독 결과 — Datumo 혈당계')
      ..writeln()
      ..writeln('- 라벨: `$labelsPath` (실사진 + 측정값 GT)')
      ..writeln('- 실행: ${DateTime.now().toIso8601String()}')
      ..writeln('- 경로: $align — '
          '${align == 'from-json'
              ? '외부 쿼드 파일 → `warpQuadToEngineFrame()` → '
                  '`SegmentRuleEngine.recognize()`'
              : align == 'auto'
              ? '`detectReadingQuad()` → `warpQuadToEngineFrame()` → '
                  '`SegmentRuleEngine.recognize()`'
              : '`preprocessPhotoForEngine()` → 폴백 원본 프레임 → '
                  '`SegmentRuleEngine.recognize()`'}')
      ..writeln('- 엔진 구성: 생성 기본값 그대로(균등 4셀 · blur 60 · separability '
          '0.25). **임계치·기하는 무수정.**')
      ..writeln('- ROI 라벨 없음 — 전처리기가 표시를 스스로 찾아야 하는 조건이다.')
      ..writeln(
          '- 전량 소요: ${(wall.elapsedMilliseconds / 1000).toStringAsFixed(1)}s (벽시계)')
      ..writeln()
      ..writeln('## 전체')
      ..writeln()
      ..writeln('| 지표 | 값 |')
      ..writeln('|---|---|')
      ..writeln('| 표본 | $total |')
      ..writeln('| 전처리 정렬 성공 | $prepared (${_pct(prepared, total)})'
          ' · 원본 폴백 $prepFallback (${_pct(prepFallback, total)}) |')
      ..writeln('| 완전일치 | $exact (${_pct(exact, total)}) |')
      ..writeln('| └ 수치만 일치(`095`↔`95`) | $numericOnly |')
      ..writeln(
          '| **치명적 오독**(값을 냈는데 라벨과 다름) | **$misread (${_pct(misread, total)})** |')
      ..writeln('| └ 자릿수가 달라진 오독 | $misreadDigitChanged |')
      ..writeln('| └ 숫자를 `HI`/`LO` 로 읽음 | $numericReadAsHiLo |')
      ..writeln('| 미인식 | $rejected (${_pct(rejected, total)}) |')
      ..writeln('| 엔진 예외 | $engineError |')
      ..writeln(
          '| p50 / p95 지연(엔진) | ${_ms(latenciesAll, 50)} / ${_ms(latenciesAll, 95)} |')
      ..writeln('| 전처리 누적 | ${(prepMicros / 1e6).toStringAsFixed(1)}s |')
      ..writeln();

    if (missing > 0 || undecodable > 0) {
      b
        ..writeln('> 파일 없음 $missing · 디코드 실패 $undecodable — 데이터 문제다.')
        ..writeln();
    }

    b
      ..writeln('## 미인식 사유')
      ..writeln()
      ..writeln('| 사유 | 건수 |')
      ..writeln('|---|---|')
      ..writeln('| 게이트: 초점(laplace 분산 < 60) | ${rejectReasons['blur'] ?? 0} |')
      ..writeln(
          '| 게이트: 전경/배경 분리(< 0.25) | ${rejectReasons['separability'] ?? 0} |')
      ..writeln('| blank(켜진 자리 없음) | ${rejectReasons['blank'] ?? 0} |')
      ..writeln('| unknownGlyph(한 자리라도 판독 불가) | ${rejectReasons['unknownGlyph'] ?? 0} |')
      ..writeln('| malformed(수로 성립 안 함) | ${rejectReasons['malformed'] ?? 0} |')
      ..writeln('| 기타 | ${rejectReasons['other'] ?? 0} |')
      ..writeln();

    void axisTable(String title, String note, Iterable<_BinStats?> bins,
        Iterable<String> keys) {
      b
        ..writeln('## $title')
        ..writeln()
        ..writeln('> $note')
        ..writeln()
        ..writeln('| 구간 | 표본 | 완전일치 | 수치일치 | 오독 | 미인식 |')
        ..writeln('|---|---|---|---|---|---|');
      for (final (key, s) in keys.zip(bins)) {
        if (s == null || s.total == 0) continue;
        b.writeln(
            '| $key | ${s.total} | ${_pct(s.exact, s.total)} | '
            '${_pct(s.numericOnly, s.total)} | ${_pct(s.misread, s.total)} | '
            '${_pct(s.rejected, s.total)} |');
      }
      b.writeln();
    }

    final batchKeys = [...byBatch.keys]..sort();
    axisTable(
      '축 — 배치',
      '1차(크라우드소싱 2,375장) vs 2차(납품 137건)',
      batchKeys.map((k) => byBatch[k]),
      batchKeys,
    );
    axisTable(
      '축 — 값 자릿수',
      '선행 공백자리 처리가 섞이는 지점 — 3자리 값은 4셀 격자에서 빈칸 1개',
      byDigits.skip(1),
      const ['1', '2', '3'],
    );
    axisTable(
      '축 — 값 구간',
      '세그먼트 수가 급변하는 경계 확인용 숫자 밴드',
      orderRanges().map((k) => byRange[k]),
      orderRanges(),
    );

    if (dumpFailures > 0 && misreads.isNotEmpty) {
      b
        ..writeln('## 오독 사례')
        ..writeln()
        ..writeln('| GT | 판독 | 전처리 | 파일 |')
        ..writeln('|---|---|---|---|');
      for (final m in misreads.take(dumpFailures)) {
        b.writeln(
            '| ${m.label.reading} | `${m.read}` | ${m.usedPrep ? '예' : '폴백'} | '
            '`${m.label.id}` |');
      }
      b.writeln();
    }
    if (dumpHits > 0 && hits.isNotEmpty) {
      b
        ..writeln('## 정답 사례 (눈 검증용)')
        ..writeln()
        ..writeln('| GT | 판독 | 전처리 | 파일 |')
        ..writeln('|---|---|---|---|');
      for (final h in hits.take(dumpHits)) {
        b.writeln(
            '| ${h.label.reading} | `${h.read}` | ${h.usedPrep ? '예' : '폴백'} | '
            '`${h.label.id}` |');
      }
      b.writeln();
    }
    return b.toString();
  }

  Iterable<String> orderRanges() => const ['<70', '70~180', '181~299', '>=300'];

  /// 재현 확인용 한 줄. 흔들리는 지연·시각은 넣지 않는다.
  String summaryLine() =>
      'SUMMARY n=$total exact=$exact numEq=$numericOnly '
      'misread=$misread digitChanged=$misreadDigitChanged '
      'hiLoReads=$numericReadAsHiLo rejected=$rejected '
      'prep=ok:$prepared/fallback:$prepFallback detectFail=$detectFail '
      'warpFail=$warpFail modelFail=$modelFail '
      'relayout=ok:$relayoutOk/fail:$relayoutFail missing=$missing '
      'undecodable=$undecodable engineError=$engineError align=$align';
}

extension _Zip<A, B> on Iterable<A> {
  Iterable<(A, B)> zip(Iterable<B> other) sync* {
    final bi = other.iterator;
    for (final a in this) {
      if (!bi.moveNext()) break;
      yield (a, bi.current);
    }
  }
}

String _pct(int n, int total) =>
    total == 0 ? '—' : '${(100 * n / total).toStringAsFixed(2)}%';

String _ms(List<double> micros, int percentile) {
  if (micros.isEmpty) return '—';
  final sorted = [...micros]..sort();
  final idx = ((percentile / 100) * (sorted.length - 1)).round();
  return '${(sorted[idx.clamp(0, sorted.length - 1)] / 1000).toStringAsFixed(1)}ms';
}

class _Options {
  _Options({
    required this.labelsPath,
    required this.root,
    required this.outPath,
    required this.limit,
    required this.dumpFailures,
    required this.dumpHits,
    required this.align,
    required this.quadsPath,
    required this.relayout,
  });

  final String labelsPath;
  final String root;
  final String? outPath;
  final int limit;
  final int dumpFailures;
  final int dumpHits;

  /// legacy = photo_preprocessor(잉크박스 정렬), auto = 밴드 검출+원근 펴기,
  /// from-json = 외부(학습 모델)가 만든 쿼드 파일
  final String align;
  final String? quadsPath;

  /// 워프 후 글자 칼럼 재배치(라벨 텍스트 제거) 적용
  final bool relayout;

  static _Options? parse(List<String> args) {
    String? labels;
    String? root;
    String? out;
    var limit = 0;
    var dumpF = 12;
    var dumpH = 8;
    var align = 'legacy';
    String? quadsPath;
    var relayout = false;

    for (var i = 0; i < args.length; i++) {
      switch (args[i]) {
        case '--labels':
          labels = _next(args, i++);
        case '--root':
          root = _next(args, i++);
        case '--out':
          out = _next(args, i++);
        case '--limit':
          limit = int.tryParse(_next(args, i++) ?? '') ?? 0;
        case '--dump-failures':
          dumpF = int.tryParse(_next(args, i++) ?? '') ?? 12;
        case '--dump-hits':
          dumpH = int.tryParse(_next(args, i++) ?? '') ?? 8;
        case '--align':
          align = _next(args, i++) ?? 'legacy';
        case '--quads':
          quadsPath = _next(args, i++);
        case '--relayout':
          relayout = true;
        case '-h':
        case '--help':
          _usage();
          return null;
      }
    }
    if (labels == null) {
      _usage();
      return null;
    }
    return _Options(
      labelsPath: labels,
      root: root ?? '.',
      outPath: out,
      limit: limit,
      dumpFailures: dumpF,
      dumpHits: dumpH,
      align: align,
      quadsPath: quadsPath,
      relayout: relayout,
    );
  }

  static String? _next(List<String> args, int i) =>
      i + 1 < args.length ? args[i + 1] : null;

  static void _usage() {
    stdout.writeln('''
실촬 골든셋 판독 벤치 — 앱 사진 경로(전처리 + 엔진) 전체

  dart run tools/ocr_bench/bin/golden_bench.dart --labels <labels.jsonl> [옵션]

  --labels <파일>        datumo labels.jsonl. 필수
  --root <디렉터리>       image 상대경로의 기준점 (기본: 현 디렉터리)
  --out <파일>           리포트를 마크다운으로 적는다
  --limit N              일정 간격으로 N 장만
  --dump-failures N      오독 사례 N 건 (기본 12)
  --dump-hits N          정답 사례 N 건 (기본 8)
  --align auto|legacy|from-json  정렬 경로 (기본 legacy)
  --quads <파일>         from-json 용 쿼드 JSONL {id, quad:[[x,y]x4]}
  --relayout             워프 후 글자 칼럼 재배치(라벨 텍스트 제거)
''');
  }
}
