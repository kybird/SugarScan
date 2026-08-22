// 셀 단위 판독 벤치 — 실제 사진에 규칙 엔진의 핵심부를 물려 본다.
//
// 무엇을 재는가
// -------------
// `LcdBinarizer` → `SegmentSampler` → `SegmentPatternTable` 세 단계를 96×96
// 실촬 셀 이미지에 그대로 돌린다. **모델이 필요 없다.** 순수 Dart 라 호스트에서
// 그냥 돈다(호스트에는 TFLite 네이티브 런타임이 없어서 CNN 엔진은 못 돌린다).
//
// 무엇을 재지 않는가
// ------------------
// **이것은 §2.7 승격 게이트가 아니다.** 게이트는 혈당계를 실제로 촬영한
// 골든셋으로만 판정한다. 여기 쓰는 데이터는
//   - 혈당계가 아니라 일반 7-세그먼트 디스플레이이고,
//   - 이미 잘린 셀이라 ROI 정렬·기하 추정 단계를 건너뛰며,
//   - `HI`/`LO` 와 소수점이 한 장도 없다.
// 그래서 여기 숫자가 좋아도 제품이 준비됐다는 뜻이 아니다. 반대로 여기서
// 못 읽으면 실기기에서는 확실히 못 읽는다. **하한선을 재는 도구다.**
//
// 사용법
// ------
//   dart run tools/ocr_bench/bin/cell_bench.dart \
//     --dataset assets_dev/upstream/7segment-display-reader/01.dataset \
//     --out docs/reports/G15-cell-bench-result.md
//
//   --limit N        클래스당 N 장만 (빠른 확인용, 기본: 전부)
//   --dump-failures N 오독 사례 N 건의 비트열을 함께 적는다 (기본 12)

import 'dart:io';

import 'package:image/image.dart' as img;
// 테스트 표면만 쓴다. `lib/ocr/src/` 를 직접 import 하면 경계를 넘은 것이고,
// 공개 배럴(`ocr.dart`)을 쓰면 `ocr_bootstrap.dart` 를 거쳐 tflite_flutter →
// Flutter 가 딸려 들어와 `dart run` 으로는 돌지 않게 된다.
import 'package:sugarscan/ocr/testing.dart';

/// 데이터셋의 폴더 이름 → 기대값.
///
/// `00`~`09` 는 숫자, `11` 은 "표시 없음"이다. 저장소에 `10` 폴더는 없다
/// (생성기 쪽 데이터셋에서 `-` 가 쓰는 인덱스라 실촬 쪽에는 비어 있다).
const String blankClassDir = '11';

void main(List<String> args) async {
  final opts = _Options.parse(args);
  if (opts == null) return;

  final root = Directory(opts.datasetPath);
  if (!root.existsSync()) {
    stderr.writeln('데이터셋을 찾을 수 없다: ${opts.datasetPath}');
    exitCode = 2;
    return;
  }

  final classDirs = root
      .listSync()
      .whereType<Directory>()
      .toList()
    ..sort((a, b) => _name(a).compareTo(_name(b)));

  if (classDirs.isEmpty) {
    stderr.writeln('클래스 폴더가 없다. 01.dataset 경로가 맞는지 볼 것.');
    exitCode = 2;
    return;
  }

  final report = _Report();
  final stopwatch = Stopwatch();

  for (final dir in classDirs) {
    final className = _name(dir);
    final expected = className == blankClassDir ? null : int.tryParse(className);
    if (expected == null && className != blankClassDir) {
      stderr.writeln('건너뜀 — 해석할 수 없는 클래스 폴더: $className');
      continue;
    }

    var files = dir
        .listSync()
        .whereType<File>()
        .where((f) => _isImage(f.path))
        .toList()
      ..sort((a, b) => a.path.compareTo(b.path));
    if (opts.limit > 0 && files.length > opts.limit) {
      // 앞에서 N 장을 자르지 않고 **일정 간격으로 고른다.** 파일명이 촬영
      // 순서라, 앞부분만 집으면 같은 세션의 연속 프레임을 보게 된다 — 조명도
      // 각도도 거의 같은 표본으로 정확도를 재고 전체를 대표한다고 믿게 된다.
      final stride = files.length / opts.limit;
      files = [
        for (var i = 0; i < opts.limit; i++) files[(i * stride).floor()],
      ];
    }

    stdout.writeln('[$className] ${files.length}장 …');

    for (final file in files) {
      final decoded = img.decodeImage(file.readAsBytesSync());
      if (decoded == null) {
        report.record(className, expected, const _Outcome.undecodable(), 0, 0);
        continue;
      }

      stopwatch
        ..reset()
        ..start();

      final gray = _toGray(decoded);
      final lcd = LcdBinarizer.binarize(gray);
      final sample = SegmentSampler.sample(
        lcd,
        // 셀 이미지 전체가 곧 자릿수 하나다.
        const NormalizedRect(left: 0, top: 0, width: 1, height: 1),
        SegmentGeometry.standard,
      );
      final glyph = SegmentPatternTable.match(sample.bits);

      stopwatch.stop();

      report.record(
        className,
        expected,
        _Outcome.from(glyph),
        sample.bits,
        sample.margin,
        micros: stopwatch.elapsedMicroseconds,
        path: file.path,
      );
    }
  }

  final markdown = report.render(
    datasetPath: opts.datasetPath,
    dumpFailures: opts.dumpFailures,
  );

  stdout
    ..writeln()
    ..writeln(markdown);

  if (opts.outPath != null) {
    File(opts.outPath!).writeAsStringSync(markdown);
    stdout.writeln('\n리포트를 적었다: ${opts.outPath}');
  }
}

// ---------------------------------------------------------------------------
// 이미지 → GrayImage
// ---------------------------------------------------------------------------

/// 휘도만 뽑는다.
///
/// 카메라 경로가 YUV420 의 Y 평면(=휘도)을 그대로 쓰므로, 벤치도 같은 것을
/// 봐야 한다. 여기서 RGB 를 다르게 섞으면 실기기와 다른 것을 재게 된다.
GrayImage _toGray(img.Image src) {
  final out = GrayImage.filled(src.width, src.height);
  for (var y = 0; y < src.height; y++) {
    for (var x = 0; x < src.width; x++) {
      final p = src.getPixel(x, y);
      // Rec.601 — `img.grayscale()` 과 같은 계수다.
      final luma = (0.299 * p.r + 0.587 * p.g + 0.114 * p.b).round();
      out.set(x, y, luma.clamp(0, 255));
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// 판정 결과
// ---------------------------------------------------------------------------

class _Outcome {
  const _Outcome.digit(this.digit)
      : letter = null,
        blank = false,
        unknown = null,
        undecodable = false;
  const _Outcome.letter(this.letter)
      : digit = null,
        blank = false,
        unknown = null,
        undecodable = false;
  const _Outcome.blank()
      : digit = null,
        letter = null,
        blank = true,
        unknown = null,
        undecodable = false;
  const _Outcome.unknown(this.unknown)
      : digit = null,
        letter = null,
        blank = false,
        undecodable = false;
  const _Outcome.undecodable()
      : digit = null,
        letter = null,
        blank = false,
        unknown = null,
        undecodable = true;

  factory _Outcome.from(GlyphMatch glyph) => switch (glyph) {
        DigitGlyph(:final digit) => _Outcome.digit(digit),
        LetterGlyph(:final letter) => _Outcome.letter(letter),
        BlankGlyph() => const _Outcome.blank(),
        UnknownGlyph(:final reason) => _Outcome.unknown(reason),
      };

  final int? digit;
  final String? letter;
  final bool blank;
  final UnknownReason? unknown;
  final bool undecodable;

  /// 값을 만들어 냈는가. 이 앱에서 위험한 것은 **틀린 값을 내는 것**이지
  /// 못 읽는 것이 아니다. 둘을 절대 같은 칸에 세지 않는다.
  bool get producedValue => digit != null;

  String get label {
    if (undecodable) return 'decode-fail';
    if (digit != null) return '$digit';
    if (letter != null) return letter!;
    if (blank) return 'blank';
    return switch (unknown!) {
      UnknownReason.tooFar => 'unknown(far)',
      UnknownReason.ambiguous => 'unknown(tie)',
    };
  }
}

class _Failure {
  _Failure(this.path, this.expected, this.got, this.bits, this.margin);
  final String path;
  final String expected;
  final String got;
  final int bits;
  final double margin;
}

class _ClassStats {
  int total = 0;
  int correct = 0;

  /// 숫자를 냈는데 다른 숫자였다. **치명적 오독.**
  int misread = 0;

  /// 값을 만들지 않았다(blank / unknown / letter). 안전한 실패.
  int abstained = 0;

  int undecodable = 0;

  final Map<String, int> confusion = <String, int>{};
  final List<double> margins = <double>[];
  final List<int> micros = <int>[];
}

class _Report {
  final Map<String, _ClassStats> byClass = <String, _ClassStats>{};
  final List<_Failure> failures = <_Failure>[];

  void record(
    String className,
    int? expectedDigit,
    _Outcome outcome,
    int bits,
    double margin, {
    int micros = 0,
    String path = '',
  }) {
    final s = byClass.putIfAbsent(className, _ClassStats.new);
    s.total++;
    if (micros > 0) s.micros.add(micros);

    if (outcome.undecodable) {
      s.undecodable++;
      return;
    }

    s.margins.add(margin);
    s.confusion.update(outcome.label, (v) => v + 1, ifAbsent: () => 1);

    final isBlankClass = expectedDigit == null;
    final ok = isBlankClass ? !outcome.producedValue : outcome.digit == expectedDigit;

    if (ok) {
      s.correct++;
      return;
    }

    if (outcome.producedValue) {
      s.misread++;
    } else {
      s.abstained++;
    }

    if (failures.length < 2000) {
      failures.add(
        _Failure(path, className, outcome.label, bits, margin),
      );
    }
  }

  String render({required String datasetPath, required int dumpFailures}) {
    final b = StringBuffer();
    final classes = byClass.keys.toList()..sort();

    var total = 0;
    var correct = 0;
    var misread = 0;
    var abstained = 0;

    for (final c in classes) {
      final s = byClass[c]!;
      total += s.total;
      correct += s.correct;
      misread += s.misread;
      abstained += s.abstained;
    }

    b
      ..writeln('# 셀 단위 판독 벤치 결과')
      ..writeln()
      ..writeln('- 데이터셋: `$datasetPath`')
      ..writeln('- 실행: ${DateTime.now().toIso8601String()}')
      ..writeln('- 대상: `LcdBinarizer` → `SegmentSampler` → `SegmentPatternTable`')
      ..writeln('- 모델 없음(순수 Dart). **§2.7 승격 게이트가 아니다** — 하한선 측정이다.')
      ..writeln()
      ..writeln('## 전체')
      ..writeln()
      ..writeln('| 지표 | 값 |')
      ..writeln('|---|---|')
      ..writeln('| 표본 | $total |')
      ..writeln('| 정답 | $correct (${_pct(correct, total)}) |')
      ..writeln('| **치명적 오독**(다른 숫자를 냄) | **$misread (${_pct(misread, total)})** |')
      ..writeln('| 미판독(값을 내지 않음) | $abstained (${_pct(abstained, total)}) |')
      ..writeln()
      ..writeln('> 오독과 미판독을 한 칸에 세지 않는다. 이 앱에서 위험한 것은')
      ..writeln('> 틀린 값을 내는 것이지 못 읽는 것이 아니다 — 못 읽으면 사용자가')
      ..writeln('> 수동 입력으로 간다.')
      ..writeln()
      ..writeln('## 클래스별')
      ..writeln()
      ..writeln('| 클래스 | 표본 | 정답률 | 오독 | 미판독 | margin p50 | p95 지연 |')
      ..writeln('|---|---|---|---|---|---|---|');

    for (final c in classes) {
      final s = byClass[c]!;
      final tag = c == blankClassDir ? '$c (표시없음)' : c;
      b.writeln(
        '| $tag | ${s.total} | ${_pct(s.correct, s.total)} | '
        '${s.misread} | ${s.abstained} | '
        '${_p(s.margins, 50).toStringAsFixed(2)} | '
        '${(_p(s.micros.map((e) => e.toDouble()).toList(), 95) / 1000).toStringAsFixed(1)}ms |',
      );
    }

    // 표시 없음 클래스는 따로 크게 적는다 — 없는 값을 만들어 내는 것이
    // 이 벤치에서 가장 나쁜 결과다.
    final blank = byClass[blankClassDir];
    if (blank != null) {
      b
        ..writeln()
        ..writeln('### 표시 없음(`$blankClassDir`)에서 값을 만들어 냈는가')
        ..writeln()
        ..writeln('**${blank.misread} / ${blank.total} '
            '(${_pct(blank.misread, blank.total)})**')
        ..writeln()
        ..writeln('꺼진 화면에서 숫자가 나오면 사용자는 재지도 않은 값을 기록하게')
        ..writeln('된다. 이 칸은 0 이어야 한다.');
    }

    b
      ..writeln()
      ..writeln('## 혼동 분포')
      ..writeln()
      ..writeln('| 기대 | 나온 것 (건수) |')
      ..writeln('|---|---|');
    for (final c in classes) {
      final s = byClass[c]!;
      final entries = s.confusion.entries.toList()
        ..sort((x, y) => y.value.compareTo(x.value));
      final shown = entries.take(6).map((e) => '`${e.key}` ${e.value}').join(' · ');
      b.writeln('| $c | $shown |');
    }

    b
      ..writeln()
      ..writeln('> 좌우 대칭인 `2`↔`5` 가 서로 섞여 나오면 비트 순서를 먼저 의심할 것.')
      ..writeln('> 순서는 최상위부터 `A B C D E F G` 다.');

    if (dumpFailures > 0 && failures.isNotEmpty) {
      b
        ..writeln()
        ..writeln('## 실패 사례')
        ..writeln()
        ..writeln('| 기대 | 나온 것 | bits(ABCDEFG) | margin | 파일 |')
        ..writeln('|---|---|---|---|---|');
      for (final f in failures.take(dumpFailures)) {
        b.writeln(
          '| ${f.expected} | `${f.got}` | `${_bits(f.bits)}` | '
          '${f.margin.toStringAsFixed(2)} | `${f.path.split(RegExp(r"[\\/]")).last}` |',
        );
      }
    }

    return b.toString();
  }
}

// ---------------------------------------------------------------------------
// 잡동사니
// ---------------------------------------------------------------------------

String _name(FileSystemEntity e) => e.path.split(RegExp(r'[\\/]')).last;

bool _isImage(String path) {
  final lower = path.toLowerCase();
  return lower.endsWith('.jpg') ||
      lower.endsWith('.jpeg') ||
      lower.endsWith('.png') ||
      lower.endsWith('.bmp');
}

String _pct(int n, int total) =>
    total == 0 ? '—' : '${(100 * n / total).toStringAsFixed(2)}%';

String _bits(int bits) =>
    bits.toRadixString(2).padLeft(7, '0');

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
셀 단위 판독 벤치

  dart run tools/ocr_bench/bin/cell_bench.dart --dataset <경로> [옵션]

  --dataset <경로>       클래스 폴더(00..09, 11)를 담은 디렉터리. 필수
  --out <파일>           리포트를 마크다운으로 적는다
  --limit N              클래스당 N 장만 (빠른 확인용)
  --dump-failures N      실패 사례 N 건을 표로 적는다 (기본 12)
''');
  }
}
