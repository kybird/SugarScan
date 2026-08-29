// LCD 숫자 밴드 자동 검출기.
//
// 사진에서 7세그 판독 밴드의 네 모서리를 찾아 `warpQuadToEngineFrame()` 으로
// 넘긴다. 카메라 경로는 가이드 박스가 이 역할을 하고, 사진 경로는 검출이
// 없으면 엔진 계약("프레임 전체가 4셀 표시")이 성립하지 않는다 — 2026-08-28
// 골든셋 진단에서 잉크 경계 박스(`_displayBox`)가 기기 외곽을 잡아 실패하는
// 것이 확정됐다.
//
// 접근: 화면 패널을 직접 찾지 않고 **글자들**을 찾는다. 숫자 밴드는
// (1) 2~6개의 비슷한 크기 글자가 (2) 가로로 일정한 피치로 (3) 한 줄에 늘어서
// (4) LCD 패널의 균일한 회색 속에 있다 — 네 가지가 동시에 성립하는 곳은
// 사진에서 드물다. 기기 외곽은 (가장자리 접촉 제외로), 브랜드 텍스트는
// (채움률 상한 + 링 균일성으로) 걸러진다. 저해상도에서 세그먼트가 쪼개지는
// 것은 인접 병합 단계에서 한 글자로 합친다(실측으로 확인된 실패).
//
// 검출은 축소본(maxDim)에서 하고 쿼드만 원본 좌표로 되돌린다 — 12MP 디코딩
// 비용은 피할 수 없어도 이진화·연결요소 비용은 축소 배율만큼 줄어든다.

import 'dart:typed_data';

import 'package:image/image.dart' as img;

/// 검출된 판독 밴드 — 원본 해상도 좌표의 네 모서리(좌상→우상→우하→좌하)와
/// 점수. 점수는 후보 간 상대 비교용이다.
class ReadingBand {
  ReadingBand({
    required this.quad,
    required this.score,
    required this.digitCount,
  });

  final List<({double x, double y})> quad;
  final double score;
  final int digitCount;
}

/// 사진에서 판독 밴드 후보들을 점수 순으로 돌려준다. 빈 목록은 정상 거부다 —
/// 호출자가 폴백을 선택한다.
List<ReadingBand> detectReadingBands(
  Uint8List imageBytes, {
  int maxDim = 960,
  void Function(String log)? debugLog,
}) {
  img.Image? decoded;
  try {
    decoded = img.decodeImage(imageBytes);
  } catch (_) {
    return const [];
  }
  if (decoded == null || decoded.width < 32 || decoded.height < 24) {
    return const [];
  }

  final scale = decoded.width > maxDim || decoded.height > maxDim
      ? maxDim /
          (decoded.width > decoded.height ? decoded.width : decoded.height)
      : 1.0;
  final sw = (decoded.width * scale).round();
  final sh = (decoded.height * scale).round();
  final small = scale < 1.0
      ? img.copyResize(decoded,
          width: sw, height: sh, interpolation: img.Interpolation.nearest)
      : decoded;

  final w = small.width;
  final h = small.height;
  final lum = Float64List(w * h);
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      final p = small.getPixel(x, y);
      lum[y * w + x] = 0.299 * p.r + 0.587 * p.g + 0.114 * p.b;
    }
  }

  final bands = <ReadingBand>[];
  for (final inverted in const [false, true]) {
    final mask = _otsuMask(lum, inverted);
    final comps = _components(mask, w, h);
    debugLog?.call(
        'polarity=${inverted ? "inv" : "norm"} comps=${comps.length}');
    final rows = _digitRows(comps, w, h, debugLog);
    for (final row in rows) {
      bands.add(_quadOf(row, w, h));
    }
    if (bands.isNotEmpty) break;
  }
  bands.sort((a, b) => b.score.compareTo(a.score));
  final inv = 1.0 / scale;
  return bands
      .map((b) => ReadingBand(
            quad: [for (final c in b.quad) (x: c.x * inv, y: c.y * inv)],
            score: b.score,
            digitCount: b.digitCount,
          ))
      .toList();
}

/// 최상위 후보 하나의 쿼드. 실패면 null.
List<({double x, double y})>? detectReadingQuad(Uint8List imageBytes) {
  final bands = detectReadingBands(imageBytes);
  return bands.isEmpty ? null : bands.first.quad;
}

// ---------------------------------------------------------------------------
// 이진화
// ---------------------------------------------------------------------------

Uint8List _otsuMask(Float64List lum, bool inverted) {
  final hist = List<int>.filled(256, 0);
  for (final v in lum) {
    hist[v.round().clamp(0, 255)]++;
  }
  final total = lum.length;
  var sum = 0.0;
  for (var t = 0; t < 256; t++) {
    sum += t * hist[t];
  }
  var sumB = 0.0, wB = 0.0, best = -1.0, thr = 128;
  var wF = total.toDouble();
  for (var t = 0; t < 256; t++) {
    wB += hist[t];
    if (wB == 0) continue;
    wF = total - wB;
    if (wF == 0) break;
    sumB += t * hist[t];
    final mB = sumB / wB;
    final mF = (sum - sumB) / wF;
    final between = wB * wF * (mB - mF) * (mB - mF);
    if (between > best) {
      best = between;
      thr = t;
    }
  }
  final mask = Uint8List(total);
  for (var i = 0; i < total; i++) {
    final isInk = inverted ? lum[i] > thr : lum[i] <= thr;
    mask[i] = isInk ? 1 : 0;
  }
  return mask;
}

// ---------------------------------------------------------------------------
// 연결요소
// ---------------------------------------------------------------------------

class _Comp {
  int minX = 1 << 30, minY = 1 << 30, maxX = -1, maxY = -1, area = 0;
  double get cx => (minX + maxX) / 2;
  double get cy => (minY + maxY) / 2;
  int get bw => maxX - minX + 1;
  int get bh => maxY - minY + 1;
}

List<_Comp> _components(Uint8List mask, int w, int h) {
  final seen = Uint8List(w * h);
  final queue = Int32List(w * h);
  final comps = <_Comp>[];
  const minArea = 8;
  const maxAreaFrac = 0.02;

  for (var start = 0; start < mask.length; start++) {
    if (mask[start] == 0 || seen[start] == 1) continue;
    var head = 0, tail = 0;
    queue[tail++] = start;
    seen[start] = 1;
    final c = _Comp();
    while (head < tail) {
      final idx = queue[head++];
      final y = idx ~/ w, x = idx % w;
      c.area++;
      if (x < c.minX) c.minX = x;
      if (x > c.maxX) c.maxX = x;
      if (y < c.minY) c.minY = y;
      if (y > c.maxY) c.maxY = y;
      for (var dy = -1; dy <= 1; dy++) {
        for (var dx = -1; dx <= 1; dx++) {
          final nx = x + dx, ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          final n = ny * w + nx;
          if (mask[n] == 1 && seen[n] == 0) {
            seen[n] = 1;
            queue[tail++] = n;
          }
        }
      }
    }
    if (c.area < minArea || c.area > mask.length * maxAreaFrac) continue;
    if (c.minX <= 1 || c.minY <= 1 || c.maxX >= w - 2 || c.maxY >= h - 2) {
      continue;
    }
    comps.add(c);
  }
  return comps;
}

// ---------------------------------------------------------------------------
// 글자 병합 + 행 클러스터링
// ---------------------------------------------------------------------------

class _Row {
  final comps = <_Comp>[];
}

List<_Row> _digitRows(
  List<_Comp> comps,
  int w,
  int h,
  void Function(String log)? log,
) {
  // v5 — "제일 큰 숫자들 = 판독 밴드". 단위·시간 줄은 더 작은 글자들이므로
  // 높이 우위 하나로 걸러진다. 피치·링 게이트는 패널 내부에서 불필요하며,
  // 레이아웃(단위 위치·줄 수)이 기기마다 달라도 높이 우위는 불변이다
  // (2026-08-29 라벨링 실측: 단위는 오른쪽/위/아래 모두 나타남).
  final cands = <_Comp>[];
  for (final c in comps) {
    final ar = c.bh / c.bw;
    final fill = c.area / (c.bw * c.bh);
    if (ar < 0.8 || ar > 6.0) continue;
    if (fill < 0.15 || fill > 0.85) continue;
    if (c.bh < h * 0.01 || c.bh > h * 0.5) continue;
    if (c.bw > w * 0.3) continue;
    cands.add(c);
  }
  log?.call('shapeFilt=${cands.length}/${comps.length}');
  if (cands.isEmpty) return const [];

  // 인접 병합 — 저해상도에서 쪼개진 세그먼트를 한 글자로.
  var merged = true;
  while (merged) {
    merged = false;
    cands.sort((a, b) => a.cx.compareTo(b.cx));
    for (var i = 0; i < cands.length && !merged; i++) {
      for (var j = i + 1; j < cands.length && !merged; j++) {
        final a = cands[i], b = cands[j];
        final gapX = b.minX > a.maxX ? (b.minX - a.maxX).toDouble() : 0.0;
        final overlapY = (a.maxY < b.maxY ? a.maxY : b.maxY) -
            (a.minY > b.minY ? a.minY : b.minY) +
            1;
        final minH = a.bh < b.bh ? a.bh : b.bh;
        if (gapX < minH * 0.35 && overlapY > minH * 0.55) {
          a.minX = a.minX < b.minX ? a.minX : b.minX;
          a.minY = a.minY < b.minY ? a.minY : b.minY;
          a.maxX = a.maxX > b.maxX ? a.maxX : b.maxX;
          a.maxY = a.maxY > b.maxY ? a.maxY : b.maxY;
          a.area += b.area;
          cands.removeAt(j);
          merged = true;
        }
      }
    }
  }

  // 높이 우위: 가장 큰 글자와 같은 수평선의 비슷한 높이 성분들 = 판독 밴드
  var hMax = 0;
  _Comp? tallest;
  for (final c in cands) {
    if (c.bh > hMax) {
      hMax = c.bh;
      tallest = c;
    }
  }
  if (tallest == null || hMax == 0) return const [];
  final tcy = tallest.cy;
  final sel = cands
      .where((c) => c.bh >= hMax * 0.55)
      .where((c) => (c.cy - tcy).abs() <= hMax * 0.8)
      .toList()
    ..sort((a, b) => a.cx.compareTo(b.cx));
  log?.call('hMax=$hMax sel=${sel.length}/${cands.length}');
  if (sel.isEmpty) return const [];
  final row = _Row()..comps.addAll(sel);
  return [row];
}

// ---------------------------------------------------------------------------
// 쿼드 + 점수
// ---------------------------------------------------------------------------

ReadingBand _quadOf(_Row row, int w, int h) {
  final cs = row.comps..sort((a, b) => a.cx.compareTo(b.cx));
  final left = cs.first, right = cs.last;
  final heights = cs.map((c) => c.bh).toList()..sort();
  final pad = (heights.last * 0.22).round();

  final lx = (left.minX - pad).clamp(0, w - 1).toDouble();
  final rx = (right.maxX + pad).clamp(0, w - 1).toDouble();
  final topY = ((left.minY < right.minY ? left.minY : right.minY) - pad)
      .clamp(0, h - 1)
      .toDouble();
  final botY = ((left.maxY > right.maxY ? left.maxY : right.maxY) + pad)
      .clamp(0, h - 1)
      .toDouble();

  final n = cs.length;
  final countScore = switch (n) {
    3 => 1.0,
    4 => 1.0,
    2 => 0.6,
    _ => 0.5,
  };
  final sizeScore = (heights.last / h).clamp(0.0, 0.25) / 0.25;
  return ReadingBand(
    quad: [
      (x: lx, y: topY),
      (x: rx, y: topY),
      (x: rx, y: botY),
      (x: lx, y: botY),
    ],
    score: countScore * sizeScore * n,
    digitCount: n,
  );
}
