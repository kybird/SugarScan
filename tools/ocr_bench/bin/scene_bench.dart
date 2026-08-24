// 장면 단위 판독 벤치 — G16 합성 장면으로 `SegmentRuleEngine.recognize()` 를
// 통째로 잰다.
//
// 셀 벤치(cell_bench.dart)가 잘라 낸 코어 3단계(이진화 → 샘플링 → 패턴 매칭)만
// 물렸다면, 이쪽은 앱이 실제로 거치는 전체 경로다 — 품질 게이트 → 이진화 →
// 자릿수 분할 → 조립까지. 엔진 구성도 앱 부트스트랩(`ocr_bootstrap.dart`)과
// 같은 생성 기본값(균등 4셀 프로파일, 기본 임계치)을 그대로 쓴다. 벤치가
// 엔진을 따로 조정하는 순간 기준선이 아니게 된다.
//
// 판정은 labels.jsonl 의 value 문자열과의 완전일치다. **오독과 미인식을 절대
// 한 칸에 합치지 않는다**(README 참조). 이 앱에서 위험한 것은 틀린 값을 내는
// 것이지 못 읽는 것이 아니다.
//
// 사용법
// ------
//   dart run tools/ocr_bench/bin/scene_bench.dart \
//     --dataset assets_dev/synth \
//     --out docs/reports/G17-scene-bench-result.md
//
//   --limit N          일정 간격으로 N 장만 (빠른 확인용, 기본: 전부)
//   --dump-failures N  오독 사례 N 건을 표로 (기본 12)

import 'dart:convert';
import 'dart:io';

import 'package:image/image.dart' as img;
// 셀 벤치와 같은 이유로 테스트 표면만 쓴다. 공개 배럴(`ocr.dart`)은
// `ocr_bootstrap.dart` 를 거쳐 tflite_flutter → Flutter 를 끌고 들어와
// `dart run` 으로는 돌지 않게 된다.
import 'package:sugarscan/ocr/testing.dart';

void main(List<String> args) async {
  final opts = _Options.parse(args);
  if (opts == null) return;

  final root = Directory(opts.datasetPath);
  final labelsFile = File(
    '${root.path}${Platform.pathSeparator}labels.jsonl',
  );
  final imagesDir = Directory('${root.path}${Platform.pathSeparator}images');
  if (!labelsFile.existsSync() || !imagesDir.existsSync()) {
    stderr.writeln(
      '데이터셋을 찾을 수 없다: ${opts.datasetPath}\n'
      'labels.jsonl 과 images/ 가 필요하다(tools/synth7seg 출력).\n'
      '없으면: dart run tools/synth7seg/bin/synth.dart',
    );
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
    // 셀 벤치와 같은 이유로 앞에서 자르지 않고 일정 간격으로 고른다.
    // 앞부분만 집으면 표본이 한쪽으로 치우친다.
    final stride = labels.length / opts.limit;
    labels = [
      for (var i = 0; i < opts.limit; i++) labels[(i * stride).floor()],
    ];
  }

  stdout.writeln('${labels.length}장 …');

  final engine = SegmentRuleEngine();
  await engine.initialize(const OcrEngineConfig());

  final report = _Report();
  final wall = Stopwatch()..start();

  for (final label in labels) {
    final file = File(
      '${imagesDir.path}${Platform.pathSeparator}${label.file}',
    );
    if (!file.existsSync()) {
      report.recordMissing(label);
      continue;
    }
    final bytes = file.readAsBytesSync();
    // 폭·높이를 채우기 위한 디코드. 엔진은 png 바이트를 스스로 디코딩한다.
    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      report.recordUndecodable(label);
      continue;
    }
    final result = await engine.recognize(
      OcrFrame(
        bytes: bytes,
        format: OcrImageFormat.png,
        width: decoded.width,
        height: decoded.height,
      ),
    );
    report.record(label, result);
  }
  wall.stop();

  final markdown = report.render(
    datasetPath: opts.datasetPath,
    dumpFailures: opts.dumpFailures,
    wall: wall,
  );

  stdout
    ..writeln()
    ..writeln(markdown);

  if (opts.outPath != null) {
    File(opts.outPath!).writeAsStringSync(markdown);
    stdout.writeln('리포트를 적었다: ${opts.outPath}');
  }

  // 재현 확인용 한 줄 요약. 실행마다 흔들리는 지연은 넣지 않는다.
  stdout.writeln(report.summaryLine());
}

// ---------------------------------------------------------------------------
// 라벨
// ---------------------------------------------------------------------------

class _Label {
  _Label({
    required this.file,
    required this.value,
    required this.margin,
    required this.rotation,
    required this.contrast,
    required this.blur,
    required this.glare,
  });

  factory _Label.parse(String line) {
    final json = jsonDecode(line) as Map<String, dynamic>;
    return _Label(
      file: json['file'] as String,
      value: json['value'] as String,
      margin: (json['margin'] as num).toDouble(),
      rotation: (json['rotation'] as num).toDouble(),
      contrast: (json['contrast'] as num).toDouble(),
      blur: (json['blur'] as num).toDouble(),
      glare: json['glare'] as bool? ?? false,
    );
  }

  final String file;
  final String value;
  final double margin;
  final double rotation;
  final double contrast;
  final double blur;
  final bool glare;

  /// `HI`/`LO` 라벨인가. 범위 초과 표시는 별도로 정확도를 낸다.
  bool get isHiLo => value == 'HI' || value == 'LO';
}

class _Misread {
  _Misread(this.label, this.read);
  final _Label label;
  final String read;
}

// ---------------------------------------------------------------------------
// 집계
// ---------------------------------------------------------------------------

class _BinStats {
  int total = 0;
  int exact = 0;
  int misread = 0;
  int rejected = 0;
}

class _HiLoStats {
  int total = 0;
  int exact = 0;

  /// `HI`/`LO` 를 숫자로 읽었다 — 치명적 오독이면서 HI/LO 정확도의 실패.
  int numericMisread = 0;

  /// 값을 냈지만 숫자도 아니고 라벨도 아니다(예: `LO` → `HI`).
  int otherMisread = 0;

  int rejected = 0;
}

class _Report {
  int total = 0;
  int exact = 0;
  int misread = 0;

  /// 오독 중 자릿수 자체가 달라진 것(`95`→`195` 유형). misread 에 포함된다.
  int misreadDigitChanged = 0;

  int rejected = 0;
  int missing = 0;
  int undecodable = 0;

  /// 숫자 라벨을 `HI`/`LO` 로 읽은 오독(`318`→`LO` 유형).
  int numericReadAsHiLo = 0;

  final Map<String, int> rejectReasons = <String, int>{};
  final Map<String, _HiLoStats> hiLo = <String, _HiLoStats>{
    'HI': _HiLoStats(),
    'LO': _HiLoStats(),
  };

  final List<double> latenciesAll = <double>[];
  final List<double> latenciesProduced = <double>[];

  final List<_Misread> misreads = <_Misread>[];

  final List<_BinStats> byMargin = List.generate(3, (_) => _BinStats());
  final List<_BinStats> byRotation = List.generate(3, (_) => _BinStats());
  final List<_BinStats> byContrast = List.generate(3, (_) => _BinStats());

  void recordMissing(_Label label) {
    total++;
    missing++;
  }

  void recordUndecodable(_Label label) {
    total++;
    undecodable++;
  }

  void record(_Label label, OcrResult result) {
    total++;
    latenciesAll.add(result.latency.inMicroseconds.toDouble());

    if (label.isHiLo) hiLo[label.value]!.total++;

    final read = result.best?.rawText;
    if (read == null) {
      rejected++;
      rejectReasons.update(
        _rejectReason(result.failure),
        (v) => v + 1,
        ifAbsent: () => 1,
      );
      if (label.isHiLo) hiLo[label.value]!.rejected++;
      _bucketize(label, (exact: false, misread: false));
      return;
    }

    latenciesProduced.add(result.latency.inMicroseconds.toDouble());

    final isExact = read == label.value;
    if (isExact) {
      exact++;
      if (label.isHiLo) hiLo[label.value]!.exact++;
      _bucketize(label, (exact: true, misread: false));
      return;
    }

    misread++;
    // 자릿수 변동은 숫자↔숫자 오독에만 세운다. `318`→`LO` 처럼 글자가 나온
    // 경우는 자릿수 비교가 무의미하고 아래 numAsHiLo 로 따로 잡는다.
    if (_isNumericText(read) &&
        _isNumericText(label.value) &&
        _digitCount(read) != _digitCount(label.value)) {
      misreadDigitChanged++;
    }
    if (label.isHiLo) {
      final s = hiLo[label.value]!;
      if (_isNumericText(read)) {
        s.numericMisread++;
      } else {
        s.otherMisread++;
      }
    } else if (read == 'HI' || read == 'LO') {
      numericReadAsHiLo++;
    }
    if (misreads.length < 500) misreads.add(_Misread(label, read));

    _bucketize(label, (exact: false, misread: true));
  }

  /// 엔진 실패를 사유별로 쪼갠다. 게이트·조립 단계의 구분은 엔진이 돌려주는
  /// 실패 메시지 접두사로 매긴다 — 메시지가 바뀌면 `other` 로 떨어진다.
  static String _rejectReason(OcrFailure? failure) {
    final message = failure?.message ?? '';
    // '초점이 흐' 까지가 안전한 공통 접두사다 — 엔진 메시지는 활용형
    // '흐립니다'(흐리다 + ㅂ니다) 라서 '흐리' 로 두면 받침에서 어긋난다.
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

  void _bucketize(_Label label, ({bool exact, bool misread}) verdict) {
    void put(List<_BinStats> bins, int index) {
      final b = bins[index];
      b.total++;
      if (verdict.exact) {
        b.exact++;
      } else if (verdict.misread) {
        b.misread++;
      } else {
        b.rejected++;
      }
    }

    // 구간은 지시서(G17)가 정한 대로. 경계값은 아래(왼쪽) 구간에 포함시킨다.
    put(byMargin, label.margin < 0.05 ? 0 : (label.margin < 0.15 ? 1 : 2));
    final angle = label.rotation.abs();
    put(byRotation, angle < 3 ? 0 : (angle < 6 ? 1 : 2));
    put(byContrast, label.contrast < 80 ? 0 : (label.contrast < 140 ? 1 : 2));
  }

  // -------------------------------------------------------------------------
  // 출력
  // -------------------------------------------------------------------------

  String render({
    required String datasetPath,
    required int dumpFailures,
    required Stopwatch wall,
  }) {
    final b = StringBuffer();

    b
      ..writeln('# 장면 단위 판독 벤치 결과 — G17 기준선')
      ..writeln()
      ..writeln('- 데이터셋: `$datasetPath` (G16 합성 장면)')
      ..writeln('- 실행: ${DateTime.now().toIso8601String()}')
      ..writeln(
        '- 대상: `SegmentRuleEngine.recognize()` 전체 경로 — 품질 게이트 → '
        '이진화 → 자릿수 분할 → 조립',
      )
      ..writeln(
        '- 엔진 구성: 생성 기본값 그대로(균등 4셀 · blur 60 · separability '
        '0.25). **임계치·기하는 무수정.**',
      )
      ..writeln('- ROI 없음(프레임 전체). 모델 없음(순수 Dart).')
      ..writeln('- 전량 소요: ${(wall.elapsedMilliseconds / 1000).toStringAsFixed(1)}s (벽시계)')
      ..writeln()
      ..writeln('## 전체')
      ..writeln()
      ..writeln('| 지표 | 값 |')
      ..writeln('|---|---|')
      ..writeln('| 표본 | $total |')
      ..writeln('| 완전일치 | $exact (${_pct(exact, total)}) |')
      ..writeln(
        '| **치명적 오독**(값을 냈는데 라벨과 다름) | **$misread (${_pct(misread, total)})** |',
      )
      ..writeln('| └ 자릿수가 달라진 오독(`95`→`195` 유형) | $misreadDigitChanged |')
      ..writeln('| 미인식(값을 내지 않음) | $rejected (${_pct(rejected, total)}) |')
      ..writeln(
        '| p50 / p95 지연(전체 프레임) | ${_ms(latenciesAll, 50)} / ${_ms(latenciesAll, 95)} |',
      )
      ..writeln(
        '| p50 / p95 지연(값을 낸 프레임) | ${_ms(latenciesProduced, 50)} / ${_ms(latenciesProduced, 95)} |',
      )
      ..writeln();

    if (missing > 0 || undecodable > 0) {
      b
        ..writeln('> 이미지 없음 $missing · 디코드 실패 $undecodable — 데이터 문제다.')
        ..writeln();
    }

    b
      ..writeln('> 오독과 미인식을 한 칸에 세지 않는다. 이 앱에서 위험한 것은')
      ..writeln('> 틀린 값을 내는 것이지 못 읽는 것이 아니다 — 못 읽으면 사용자가')
      ..writeln('> 수동 입력으로 간다. 임계값·기하는 건드리지 않았다. 나쁜 숫자가')
      ..writeln('> 이 리포트의 결과물이다.')
      ..writeln()
      ..writeln('## 미인식 사유')
      ..writeln()
      ..writeln('| 사유 | 건수 |')
      ..writeln('|---|---|')
      ..writeln('| 게이트: 초점(라플라시안 분산 < 60) | ${rejectReasons['blur'] ?? 0} |')
      ..writeln(
        '| 게이트: 전경/배경 분리(separability < 0.25) | ${rejectReasons['separability'] ?? 0} |',
      )
      ..writeln('| 조립: blank(켜진 자리 없음) | ${rejectReasons['blank'] ?? 0} |')
      ..writeln('| 조립: unknownGlyph(한 자리라도 판독 불가) | ${rejectReasons['unknownGlyph'] ?? 0} |')
      ..writeln('| 조립: malformed(수로 성립 안 함) | ${rejectReasons['malformed'] ?? 0} |')
      ..writeln('| 기타 | ${rejectReasons['other'] ?? 0} |')
      ..writeln()
      ..writeln('## HI / LO 정확도')
      ..writeln()
      ..writeln('| 라벨 | 표본 | 정확 | 숫자로 오독 | 다르게 오독 | 미인식 |')
      ..writeln('|---|---|---|---|---|---|');
    for (final key in ['HI', 'LO']) {
      final s = hiLo[key]!;
      b.writeln(
        '| $key | ${s.total} | ${_pct(s.exact, s.total)} | '
        '${s.numericMisread} | ${s.otherMisread} | ${s.rejected} |',
      );
    }
    b
      ..writeln()
      ..writeln('숫자 라벨을 `HI`/`LO` 로 읽은 오독(`318`→`LO` 유형): '
          '**$numericReadAsHiLo 건**')
      ..writeln();

    _axisTable(
      b,
      title: '축별 분해 — 여백(라벨 margin)',
      note: 'ROI 가 베젤·여백을 얼마나 포함하는가.',
      rows: ['0~5%', '5~15%', '15~25%'],
      bins: byMargin,
    );
    _axisTable(
      b,
      title: '축별 분해 — 회전(라벨 |rotation|)',
      note: '손으로 들고 찍는 기울기.',
      rows: ['0~3°', '3~6°', '6~8°'],
      bins: byRotation,
    );
    _axisTable(
      b,
      title: '축별 분해 — 대비(라벨 contrast)',
      note: '전경·배경 휘도 차. 30 근처가 저대비 LCD.',
      rows: ['30~80', '80~140', '140~200'],
      bins: byContrast,
    );

    if (dumpFailures > 0 && misreads.isNotEmpty) {
      b
        ..writeln('## 오독 사례')
        ..writeln()
        ..writeln('| 라벨 | 판독 | margin | 회전 | 대비 | blur | 반사 | 파일 |')
        ..writeln('|---|---|---|---|---|---|---|');
      for (final m in misreads.take(dumpFailures)) {
        final l = m.label;
        b.writeln(
          '| ${l.value} | `${m.read}` | ${(l.margin * 100).toStringAsFixed(1)}% | '
          '${l.rotation.toStringAsFixed(1)}° | ${l.contrast.toStringAsFixed(0)} | '
          '${l.blur.toStringAsFixed(2)}px | ${l.glare ? '있음' : '없음'} | `${l.file}` |',
        );
      }
    }

    return b.toString();
  }

  void _axisTable(
    StringBuffer b, {
    required String title,
    required String note,
    required List<String> rows,
    required List<_BinStats> bins,
  }) {
    b
      ..writeln('## $title')
      ..writeln()
      ..writeln('> $note')
      ..writeln()
      ..writeln('| 구간 | 표본 | 완전일치 | 치명적 오독 | 미인식 |')
      ..writeln('|---|---|---|---|---|');
    for (var i = 0; i < rows.length; i++) {
      final s = bins[i];
      b.writeln(
        '| ${rows[i]} | ${s.total} | ${_pct(s.exact, s.total)} | '
        '${_pct(s.misread, s.total)} | ${_pct(s.rejected, s.total)} |',
      );
    }
    b.writeln();
  }

  /// 재현 확인용 한 줄. 실행마다 흔들리는 지연·시각은 넣지 않는다.
  String summaryLine() {
    final r = rejectReasons;
    String hiLoPart(String k) {
      final s = hiLo[k]!;
      return '$k:${s.total}/${s.exact}/${s.numericMisread}/${s.otherMisread}/${s.rejected}';
    }

    return 'SUMMARY '
        'n=$total exact=$exact misread=$misread digitChanged=$misreadDigitChanged '
        'rejected=$rejected '
        'reasons=blur:${r['blur'] ?? 0},sep:${r['separability'] ?? 0},'
        'blank:${r['blank'] ?? 0},unknown:${r['unknownGlyph'] ?? 0},'
        'malformed:${r['malformed'] ?? 0},other:${r['other'] ?? 0} '
        '${hiLoPart('HI')} ${hiLoPart('LO')} '
        'numAsHiLo=$numericReadAsHiLo missing=$missing undecodable=$undecodable';
  }
}

// ---------------------------------------------------------------------------
// 잡동사니
// ---------------------------------------------------------------------------

String _pct(int n, int total) =>
    total == 0 ? '—' : '${(100 * n / total).toStringAsFixed(2)}%';

String _ms(List<double> micros, int percentile) =>
    '${(_p(micros, percentile) / 1000).toStringAsFixed(1)}ms';

double _p(List<double> values, int percentile) {
  if (values.isEmpty) return 0;
  final sorted = [...values]..sort();
  final idx = ((percentile / 100) * (sorted.length - 1)).round();
  return sorted[idx.clamp(0, sorted.length - 1)];
}

class _Options {
  _Options({
    required this.datasetPath,
    required this.outPath,
    required this.limit,
    required this.dumpFailures,
  });

  final String datasetPath;
  final String? outPath;
  final int limit;
  final int dumpFailures;

  static _Options? parse(List<String> args) {
    String? dataset;
    String? out;
    var limit = 0;
    var dump = 12;

    for (var i = 0; i < args.length; i++) {
      switch (args[i]) {
        case '--dataset':
          dataset = _next(args, i++);
        case '--out':
          out = _next(args, i++);
        case '--limit':
          limit = int.tryParse(_next(args, i++) ?? '') ?? 0;
        case '--dump-failures':
          dump = int.tryParse(_next(args, i++) ?? '') ?? 12;
        case '-h':
        case '--help':
          _usage();
          return null;
      }
    }

    if (dataset == null) {
      _usage();
      return null;
    }
    return _Options(
      datasetPath: dataset,
      outPath: out,
      limit: limit,
      dumpFailures: dump,
    );
  }

  static String? _next(List<String> args, int i) =>
      i + 1 < args.length ? args[i + 1] : null;

  static void _usage() {
    stdout.writeln('''
장면 단위 판독 벤치 — SegmentRuleEngine.recognize() 전체 경로

  dart run tools/ocr_bench/bin/scene_bench.dart --dataset <경로> [옵션]

  --dataset <경로>       labels.jsonl 과 images/ 를 담은 디렉터리(tools/synth7seg 출력). 필수
  --out <파일>           리포트를 마크다운으로 적는다
  --limit N              일정 간격으로 N 장만 (빠른 확인용)
  --dump-failures N      오독 사례 N 건을 표로 적는다 (기본 12)
''');
  }
}
