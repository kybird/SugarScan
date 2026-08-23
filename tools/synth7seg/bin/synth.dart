// 장면 단위 합성 데이터 생성기 — 혈당계 표시 전체를 임의로 그린다.
//
// 왜 있는가
// ---------
// G15 가 셀 단위(숫자 한 개)만 잰 반면, 실제 엔진은 자릿수 분할·표시 전체
// 이진화·HI/LO 판정·소수점·자릿수 결합까지 한다. 이걸 검증할 장면 단위
// 데이터가 세상에 없어서 만든다. 장면 단위 벤치(G17)의 입력이다.
//
// 무엇을 지키나
// -------------
// - 글리프 비트표는 `segment_patterns.dart` 의 표를 **그대로 import 해서**
//   쓴다(손으로 옮겨 적지 않는다). 경로는 테스트 표면 `lib/ocr/testing.dart`
//   를 거친다. `lib/` 는 한 줄도 안 고친다.
// - 세그먼트 **위치** 는 판독기(`SegmentGeometry`)와 독립적인 일반적인
//   7-세그먼트 비율로 따로 그린다. 판독기의 기하를 그대로 쓰면
//   "자기가 그린 걸 자기가 읽는" 시험이 되어 아무것도 검증하지 못한다.
// - 변화 축과 범위는 지시서(G16)의 숫자를 그대로 쓴다.
// - 난수는 _Sample.draw 한 곳에서만 뽑는다. 같은 시드는 같은 바이트를
//   낳아야 한다 — 재현이 안 되면 벤치 결과를 비교할 수 없다.

import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:image/image.dart' as img;
// 테스트 표면만 쓴다 — 공개 배럴을 import 하면 ocr_bootstrap → tflite_flutter
// → Flutter 가 딸려와 `dart run` 으로 안 돈다. 셀 벤치와 같은 이유다.
import 'package:sugarscan/ocr/testing.dart';

// ---------------------------------------------------------------------------
// 고정 상수 — 지시서의 변화 축
// ---------------------------------------------------------------------------

const int kCanvasW = 320;
const int kCanvasH = 160;

/// HI/LO 비율: 전체의 8%.
const double kHiLoRate = 0.08;

/// 반사(글레어) 확률 15%.
const double kGlareRate = 0.15;

/// 소수점을 제외한 표시 글자 → 셀 패턴 비트.
///
/// `I` 와 `O` 는 각각 `1`, `0` 과 세그먼트 패턴이 같다(segment_patterns 의
/// 주석 참조). 혈당계도 그렇게 표시한다.
int? _patternOf(String ch) => switch (ch) {
      'H' => kLetterPatterns['H'],
      'L' => kLetterPatterns['L'],
      'I' => kDigitPatterns[1],
      'O' => kDigitPatterns[0],
      _ => kDigitPatterns[int.tryParse(ch) ?? -1],
    };

void main(List<String> args) {
  final opts = _Options.parse(args);
  if (opts == null) return;

  final outRoot = Directory(opts.outPath);
  final imagesDir =
      Directory('${outRoot.path}${Platform.pathSeparator}images');
  imagesDir.createSync(recursive: true);
  // 같은 out 에 재생성할 때 옛 이미지가 섞이지 않게 png 만 지운다.
  for (final f in imagesDir.listSync().whereType<File>()) {
    if (f.path.toLowerCase().endsWith('.png')) f.deleteSync();
  }

  final rnd = math.Random(opts.seed);
  final labels = <String>[];
  final stats = _Stats();
  final stopwatch = Stopwatch()..start();

  for (var i = 1; i <= opts.count; i++) {
    final sample = _Sample.draw(rnd);
    stats.record(sample);

    final file = '${i.toString().padLeft(6, '0')}.png';
    final png = _render(sample);
    File('${imagesDir.path}${Platform.pathSeparator}$file')
        .writeAsBytesSync(png);
    labels.add(sample.toJsonLine(file));

    if (i % 250 == 0 || i == opts.count) {
      stdout.writeln('[$i/${opts.count}] …');
    }
  }

  File('${outRoot.path}${Platform.pathSeparator}labels.jsonl')
      .writeAsStringSync('${labels.join('\n')}\n');

  stopwatch.stop();
  stats.printTo(opts, stopwatch.elapsed);
}

// ---------------------------------------------------------------------------
// 표본 — 변화 축을 한 곳에서 뽑는다. 뽑는 순서가 곧 재현성이다.
// ---------------------------------------------------------------------------

class _Sample {
  const _Sample({
    required this.value,
    required this.unit,
    required this.digits,
    required this.margin,
    required this.rotationDeg,
    required this.perspective,
    required this.contrast,
    required this.blur,
    required this.glare,
    required this.darkOnLight,
    required this.glareParams,
    required this.cornerAngles,
    required this.cornerMags,
  });

  final String value; // 화면에 보이는 문자열 그대로 ("137", "7.6", "HI", "LO")
  final String unit; // 'mgdl' | 'mmoll' — HI/LO 에도 그대로 둔다.
  final int digits; // 패널 자릿수 셀 수: 3 또는 4
  final double margin; // 0 ~ 0.25 (표시 둘레 여백)
  final double rotationDeg; // −8 ~ +8
  final double perspective; // 0 ~ 0.06 (폭 대비 최대 모서리 변위)
  final int contrast; // 30 ~ 200 (전경·배경 휘도 차)
  final double blur; // 0 ~ 1.5 px (가우시안 σ)
  final bool glare;
  final bool darkOnLight; // true: 어두운 글자/밝은 배경, false: 반대
  final _Glare glareParams;

  /// 원근용 모서리 변위(4개)의 방향과 크기(0~1, 렌더에서 스케일).
  final List<double> cornerAngles;
  final List<double> cornerMags;

  /// 뽑는 순서를 바꾸면 같은 시드가 다른 데이터를 낳는다. 고정.
  static _Sample draw(math.Random rnd) {
    // r1 하나로 삼분: 앞 4% LO, 다음 4% HI, 나머지 숫자.
    final r1 = rnd.nextDouble();
    final unitIsMgdl = rnd.nextBool();

    final String value;
    if (r1 < kHiLoRate / 2) {
      value = 'LO';
    } else if (r1 < kHiLoRate) {
      value = 'HI';
    } else if (unitIsMgdl) {
      value = '${rnd.nextInt(581) + 20}'; // 20 ~ 600
    } else {
      final tenth = rnd.nextInt(323) + 11; // 1.1 ~ 33.3
      value = '${tenth ~/ 10}.${tenth % 10}';
    }

    final glareParams = _Glare.draw(rnd); // glare 여부와 무관하게 항상 뽑는다.

    return _Sample(
      value: value,
      unit: unitIsMgdl ? 'mgdl' : 'mmoll',
      digits: rnd.nextBool() ? 3 : 4,
      margin: rnd.nextDouble() * 0.25,
      rotationDeg: rnd.nextDouble() * 16 - 8,
      perspective: rnd.nextDouble() * 0.06,
      contrast: 30 + rnd.nextInt(171), // 30 ~ 200
      blur: rnd.nextDouble() * 1.5,
      glare: rnd.nextDouble() < kGlareRate,
      darkOnLight: rnd.nextBool(),
      glareParams: glareParams,
      cornerAngles: [for (var i = 0; i < 4; i++) rnd.nextDouble()],
      cornerMags: [for (var i = 0; i < 4; i++) rnd.nextDouble()],
    );
  }

  /// 배경 휘도. 전경과의 차가 정확히 contrast 가 되도록 극성별로 정한다.
  /// (축별 분해에서 contrast 라벨을 그대로 믿을 수 있어야 한다.)
  double get backgroundLum => darkOnLight
      ? contrast + 15.0 // fg = 15 … 215 — 반사형 LCD 의 밝은 배경
      : 240.0 - contrast; // fg = 240 … 40 — 백라이트 화면의 어두운 배경

  /// 계획서 §2.6 형식. 키 이름과 순서를 그대로 쓴다.
  String toJsonLine(String file) => jsonEncode({
        'file': file,
        'value': value,
        'unit': unit,
        'digits': digits,
        'margin': _round(margin, 4),
        'rotation': _round(rotationDeg, 2),
        'perspective': _round(perspective, 4),
        'contrast': contrast,
        'blur': _round(blur, 2),
        'glare': glare,
      });
}

class _Glare {
  const _Glare(this.cx, this.cy, this.rx, this.ry);

  /// 정규화 위치/반경 — 렌더에서 캔버스 크기로 환산한다.
  final double cx; // 0 ~ 1 (캔버스 폭 비율)
  final double cy; // 0 ~ 1 (캔버스 높이 비율)
  final double rx; // 0.15 ~ 0.35 (폭 비율)
  final double ry; // 0.15 ~ 0.45 (높이 비율)

  static _Glare draw(math.Random rnd) => _Glare(
        rnd.nextDouble(),
        rnd.nextDouble(),
        rnd.nextDouble() * 0.20 + 0.15,
        rnd.nextDouble() * 0.30 + 0.15,
      );
}

double _round(double v, int digits) {
  final f = math.pow(10, digits).toDouble();
  return (v * f).roundToDouble() / f;
}

// ---------------------------------------------------------------------------
// 렌더 — 평면 씬(회전·AA) → 글레어 → 원근 → 블러 → PNG
// ---------------------------------------------------------------------------

List<int> _render(_Sample s) {
  final bg = s.backgroundLum;
  final fg = s.darkOnLight ? bg - s.contrast : bg + s.contrast;

  final cells = _cellPatterns(s); // 좌측 셀부터. null = 공백.
  final dotAfterCell = _decimalCellIndex(s, cells.length); // −1 = 점 없음

  final flat = _FlatScene(s, bg, fg, cells, dotAfterCell);
  if (s.glare) flat.drawGlare(s.glareParams);
  final warped = flat.warpPerspective();
  final blurred = s.blur > 0.01 ? _gaussianBlur(warped, s.blur) : warped;

  final image = img.Image(width: kCanvasW, height: kCanvasH);
  for (var y = 0; y < kCanvasH; y++) {
    for (var x = 0; x < kCanvasW; x++) {
      final v = blurred[y * kCanvasW + x].round().clamp(0, 255);
      image.setPixelRgb(x, y, v, v, v);
    }
  }
  return img.encodePng(image);
}

/// 값 문자열 → 셀 패턴 배열. 오른쪽 정렬, 앞자리는 공백(null).
List<int?> _cellPatterns(_Sample s) {
  final chars = s.value.replaceAll('.', '').split('');
  final patterns = <int?>[
    for (var i = 0; i < s.digits - chars.length; i++) null,
  ];
  for (final ch in chars) {
    patterns.add(_patternOf(ch));
  }
  return patterns;
}

/// 소수점이 몇 번째 셀 **뒤에** 붙는지. 점이 없으면 −1.
int _decimalCellIndex(_Sample s, int cellCount) {
  final dot = s.value.indexOf('.');
  if (dot < 0) return -1;
  final totalGlyphs = s.value.length - 1; // 점 뺀 글자 수
  final firstGlyphCell = cellCount - totalGlyphs;
  return firstGlyphCell + dot - 1;
}

/// 평면 씬 — 회전된 표시 블록을 안티앨리어싱해서 그린다.
class _FlatScene {
  _FlatScene(this.s, this.bg, this.fg, this.cells, this.dotAfterCell)
      : lum = List<double>.filled(kCanvasW * kCanvasH, bg) {
    _layout();
    _drawDisplay();
  }

  final _Sample s;
  final double bg;
  final double fg;
  final List<int?> cells;
  final int dotAfterCell;

  final List<double> lum;

  // 표시 블록 배치 — 일반적인 7-세그먼트 비율. 판독기 기하와 무관하다.
  late final double blockX, blockY, cellW, cellH, cellGap;

  void _layout() {
    // 셀 폭 = 높이의 1/2, 셀 사이 간격 = 폭의 0.35, 소수점은 간격에 놓는다.
    const cellAspect = 0.5;
    const gapRatio = 0.35;
    final n = cells.length.toDouble();
    final blockAspect = n * cellAspect + (n - 1) * gapRatio * cellAspect;

    final availH = kCanvasH * (1 - 2 * s.margin);
    final availW = kCanvasW * (1 - 2 * s.margin);
    cellH = math.min(availH, availW / blockAspect);
    cellW = cellH * cellAspect;
    cellGap = cellW * gapRatio;

    final blockW = cells.length * cellW + (cells.length - 1) * cellGap;
    blockX = (kCanvasW - blockW) / 2;
    blockY = (kCanvasH - cellH) / 2;
  }

  void _drawDisplay() {
    final theta = s.rotationDeg * math.pi / 180;
    final cosT = math.cos(-theta);
    final sinT = math.sin(-theta);
    final cx = kCanvasW / 2;
    final cy = kCanvasH / 2;

    // 픽셀당 4×4 서브샘플 — 회전 계단을 부드럽게 한다.
    const offs = [0.125, 0.375, 0.625, 0.875];

    for (var y = 0; y < kCanvasH; y++) {
      for (var x = 0; x < kCanvasW; x++) {
        var ink = 0;
        for (final oy in offs) {
          for (final ox in offs) {
            final px = x + ox - cx;
            final py = y + oy - cy;
            final qx = px * cosT - py * sinT + cx;
            final qy = px * sinT + py * cosT + cy;
            if (_inkAt(qx, qy)) ink++;
          }
        }
        final ratio = ink / 16.0;
        if (ratio > 0) {
          lum[y * kCanvasW + x] = bg * (1 - ratio) + fg * ratio;
        }
      }
    }
  }

  /// 블록 좌표 (qx, qy) 가 켜진 세그먼트/소수점 위인가.
  bool _inkAt(double qx, double qy) {
    final lx = qx - blockX;
    final ly = qy - blockY;
    if (lx < 0 || ly < 0 || ly >= cellH) return false;

    final pitch = cellW + cellGap;
    final cellIndex = (lx / pitch).floor();
    final inCellX = lx - cellIndex * pitch;

    if (inCellX >= cellW) {
      // 셀 사이 간격 — 소수점만 여기 있다. 갭 시작부터의 오프셋으로 바꿔
      // 넘긴다(원점이 셀 시작이면 점의 x 범위와 영영 안 겹친다).
      return dotAfterCell == cellIndex && _inDecimalDot(inCellX - cellW, ly);
    }
    if (cellIndex >= cells.length) return false;

    final bits = cells[cellIndex];
    if (bits == null || bits == 0) return false;
    return _segmentHit(bits, inCellX, ly);
  }

  /// 세그먼트 사각형(셀 내 좌표). 굵기 k = 폭의 1/6, 안쪽 여백 d = 폭의 0.1.
  bool _segmentHit(int bits, double x, double y) {
    final k = cellW / 6;
    final d = cellW * 0.1;
    final mid = cellH / 2;

    // 가로(A/G/D)와 세로(F/B/E/C) 사각형 판정. 비트 순서는 최상위 A 부터.
    bool hz(double y0) =>
        d <= x && x < cellW - d && y0 <= y && y < y0 + k;
    bool vt(double x0, double y0, double y1) =>
        x0 <= x && x < x0 + k && y0 <= y && y < y1;

    if (hz(d)) return (bits & Seg.a) != 0;
    if (hz(mid - k / 2)) return (bits & Seg.g) != 0;
    if (hz(cellH - d - k)) return (bits & Seg.d) != 0;
    if (vt(d, d, mid - k / 2)) return (bits & Seg.f) != 0;
    if (vt(cellW - d - k, d, mid - k / 2)) return (bits & Seg.b) != 0;
    if (vt(d, mid + k / 2, cellH - d - k)) return (bits & Seg.e) != 0;
    if (vt(cellW - d - k, mid + k / 2, cellH - d - k)) {
      return (bits & Seg.c) != 0;
    }
    return false;
  }

  bool _inDecimalDot(double gapX, double y) {
    final k = cellW / 6;
    final d = cellW * 0.1;
    final dotX0 = (cellGap - k) / 2;
    return dotX0 <= gapX &&
        gapX < dotX0 + k &&
        cellH - d - k <= y &&
        y < cellH - d;
  }

  /// 밝은 타원 하나 — 씬 위에 겹친다. 세그먼트도 함께 밝아진다(반사).
  void drawGlare(_Glare g) {
    final cx = g.cx * kCanvasW;
    final cy = g.cy * kCanvasH;
    final rx = math.max(8.0, g.rx * kCanvasW);
    final ry = math.max(6.0, g.ry * kCanvasH);
    // 정규화 거리 3σ 까지만 그린다.
    final x0 = (cx - rx * 3).floor().clamp(0, kCanvasW - 1);
    final x1 = (cx + rx * 3).ceil().clamp(0, kCanvasW - 1);
    final y0 = (cy - ry * 3).floor().clamp(0, kCanvasH - 1);
    final y1 = (cy + ry * 3).ceil().clamp(0, kCanvasH - 1);

    for (var y = y0; y <= y1; y++) {
      for (var x = x0; x <= x1; x++) {
        final dx = (x - cx) / rx;
        final dy = (y - cy) / ry;
        final d2 = dx * dx + dy * dy;
        if (d2 > 9) continue;
        final i = y * kCanvasW + x;
        lum[i] += math.exp(-d2 / 2) * (255 - lum[i]);
      }
    }
  }

  /// 네 모서리를 흔들어 원근을 준다. dest→flat 호모그래피로 역매핑.
  List<double> warpPerspective() {
    final maxOff = s.perspective * kCanvasW;
    final base = [
      (0.0, 0.0),
      (kCanvasW.toDouble(), 0.0),
      (kCanvasW.toDouble(), kCanvasH.toDouble()),
      (0.0, kCanvasH.toDouble()),
    ];
    final dest = <(double, double)>[
      for (var i = 0; i < 4; i++)
        (
          base[i].$1 + math.cos(s.cornerAngles[i] * 2 * math.pi) *
              s.cornerMags[i] * maxOff,
          base[i].$2 + math.sin(s.cornerAngles[i] * 2 * math.pi) *
              s.cornerMags[i] * maxOff,
        ),
    ];

    final h = _homography(dest, base);
    final out = List<double>.filled(kCanvasW * kCanvasH, bg);
    for (var y = 0; y < kCanvasH; y++) {
      for (var x = 0; x < kCanvasW; x++) {
        final w = h[6] * x + h[7] * y + 1;
        final fx = (h[0] * x + h[1] * y + h[2]) / w;
        final fy = (h[3] * x + h[4] * y + h[5]) / w;
        out[y * kCanvasW + x] = _bilinear(fx, fy);
      }
    }
    return out;
  }

  double _bilinear(double x, double y) {
    final cx = x.clamp(0.0, kCanvasW - 1.0);
    final cy = y.clamp(0.0, kCanvasH - 1.0);
    final x0 = cx.floor().clamp(0, kCanvasW - 2);
    final y0 = cy.floor().clamp(0, kCanvasH - 2);
    final tx = cx - x0;
    final ty = cy - y0;
    final tl = y0 * kCanvasW + x0;
    final tr = tl + 1;
    final bl = tl + kCanvasW;
    final br = bl + 1;
    final top = lum[tl] * (1 - tx) + lum[tr] * tx;
    final bottom = lum[bl] * (1 - tx) + lum[br] * tx;
    return top * (1 - ty) + bottom * ty;
  }
}

// ---------------------------------------------------------------------------
// 블러
// ---------------------------------------------------------------------------

List<double> _gaussianBlur(List<double> src, double sigma) {
  final r = math.max(1, (3 * sigma).ceil());
  final kernel = <double>[
    for (var i = -r; i <= r; i++) math.exp(-(i * i) / (2 * sigma * sigma)),
  ];
  final sum = kernel.reduce((a, b) => a + b);
  for (var i = 0; i < kernel.length; i++) {
    kernel[i] /= sum;
  }

  final tmp = List<double>.filled(src.length, 0);
  final out = List<double>.filled(src.length, 0);

  for (var y = 0; y < kCanvasH; y++) {
    for (var x = 0; x < kCanvasW; x++) {
      var acc = 0.0;
      for (var i = -r; i <= r; i++) {
        final xx = (x + i).clamp(0, kCanvasW - 1);
        acc += src[y * kCanvasW + xx] * kernel[i + r];
      }
      tmp[y * kCanvasW + x] = acc;
    }
  }
  for (var y = 0; y < kCanvasH; y++) {
    for (var x = 0; x < kCanvasW; x++) {
      var acc = 0.0;
      for (var i = -r; i <= r; i++) {
        final yy = (y + i).clamp(0, kCanvasH - 1);
        acc += tmp[yy * kCanvasW + x] * kernel[i + r];
      }
      out[y * kCanvasW + x] = acc;
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// 호모그래피 (8×8 가우스 소거)
// ---------------------------------------------------------------------------

/// src 4점 → dst 4점 을 만족하는 h0..h7.
/// 매핑: X = (h0 x + h1 y + h2) / (h6 x + h7 y + 1), Y 도 같은 형태.
List<double> _homography(
  List<(double, double)> src,
  List<(double, double)> dst,
) {
  final a = List<List<double>>.generate(8, (_) => List<double>.filled(9, 0));
  for (var i = 0; i < 4; i++) {
    final (x, y) = src[i];
    final (X, Y) = dst[i];
    a[i * 2] = [x, y, 1, 0, 0, 0, -X * x, -X * y, X];
    a[i * 2 + 1] = [0, 0, 0, x, y, 1, -Y * x, -Y * y, Y];
  }

  // 조르당 소거(부분 피벗). 정규화는 하지 않는다 — 대각값으로 나눠 돌려준다.
  for (var col = 0; col < 8; col++) {
    var pivot = col;
    for (var row = col + 1; row < 8; row++) {
      if (a[row][col].abs() > a[pivot][col].abs()) pivot = row;
    }
    if (a[pivot][col].abs() < 1e-12) continue;
    if (pivot != col) {
      final t = a[col];
      a[col] = a[pivot];
      a[pivot] = t;
    }
    for (var row = 0; row < 8; row++) {
      if (row == col) continue;
      final f = a[row][col] / a[col][col];
      for (var k2 = col; k2 < 9; k2++) {
        a[row][k2] -= f * a[col][k2];
      }
    }
  }

  return [
    for (var i = 0; i < 8; i++)
      a[i][i].abs() < 1e-12 ? 0.0 : a[i][8] / a[i][i],
  ];
}

// ---------------------------------------------------------------------------
// 통계 · 인자
// ---------------------------------------------------------------------------

class _Stats {
  int mgdl = 0, mmoll = 0, hi = 0, lo = 0, glareCount = 0, dark = 0;

  void record(_Sample s) {
    if (s.value == 'HI') {
      hi++;
    } else if (s.value == 'LO') {
      lo++;
    } else if (s.unit == 'mgdl') {
      mgdl++;
    } else {
      mmoll++;
    }
    if (s.glare) glareCount++;
    if (s.darkOnLight) dark++;
  }

  void printTo(_Options o, Duration elapsed) {
    final total = mgdl + mmoll + hi + lo;
    String pct(int n) =>
        total == 0 ? '—' : '${(100 * n / total).toStringAsFixed(1)}%';
    stdout
      ..writeln()
      ..writeln('생성 완료: $total장 → ${o.outPath}')
      ..writeln(
        '  mg/dL $mgdl (${pct(mgdl)}) · mmol/L $mmoll (${pct(mmoll)})'
        ' · HI $hi · LO $lo (합계 ${pct(hi + lo)})',
      )
      ..writeln(
        '  반사 $glareCount (${pct(glareCount)}) · '
        '어두운 글자 $dark (${pct(dark)}) / 밝은 글자 ${total - dark}',
      )
      ..writeln('  걸린 시간: ${elapsed.inMilliseconds}ms');
  }
}

class _Options {
  _Options({required this.outPath, required this.count, required this.seed});

  final String outPath;
  final int count;
  final int seed;

  static _Options? parse(List<String> args) {
    var out = 'assets_dev/synth';
    var count = 2000;
    var seed = 0;

    for (var i = 0; i < args.length; i++) {
      switch (args[i]) {
        case '--out':
          if (i + 1 < args.length) out = args[++i];
        case '--count':
          count = int.tryParse(i + 1 < args.length ? args[++i] : '') ?? count;
        case '--seed':
          seed = int.tryParse(i + 1 < args.length ? args[++i] : '') ?? seed;
        case '-h':
        case '--help':
          _usage();
          return null;
        default:
          stderr.writeln('알 수 없는 인자: ${args[i]}');
          _usage();
          return null;
      }
    }
    return _Options(outPath: out, count: count, seed: seed);
  }

  static void _usage() {
    stdout.writeln('''
장면 단위 합성 데이터 생성기 (G16)

  dart run tools/synth7seg/bin/synth.dart [--out <디렉터리>] [--count N] [--seed N]

  --out <디렉터리>   기본 assets_dev/synth
  --count N          생성 장수, 기본 2000
  --seed N           시드, 기본 0 — 같은 시드는 같은 바이트를 낳는다
''');
  }
}
