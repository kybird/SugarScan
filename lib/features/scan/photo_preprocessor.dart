import 'dart:typed_data';
import 'dart:math' as math;

import 'package:image/image.dart' as img;

// 배럴(`ocr.dart`)은 bootstrap 을 거쳐 tflite_flutter → Flutter 를 끌어온다.
// 이 파일이 필요한 것은 프레임 값 타입 두 개뿐이라 정의 파일을 직접 가리킨다 —
// dart run 으로 도는 벤치 도구(golden_bench)가 이 전처리기를 그대로 물기 위해
// 필요하다. API 로 노출되는 타입은 바뀌지 않는다.
import '../../ocr/src/engine/ocr_frame.dart' show OcrFrame, OcrImageFormat;

/// 사진 전처리기 — 사진 불러오기(debug 전용)를 위한 실험 정렬 단계.
///
/// 무엇을 하나
/// ------------
/// 규칙 엔진은 프레임 전체가 "왼쪽부터 4셀, 셀 사이 3% 간격"인 표시라고
/// 가정한다(`MeterProfile.uniform`). 카메라에서는 사용자가 가이드 박스에
/// 표시를 맞춰 줘서 이 가정이 성립한다. 임의의 사진에는 성립하지 않아서
/// 사진을 그대로 넘기면 셀 격자가 숫자 위에 안 떨어진다.
///
/// 이 전처리기는 사진에서 표시를 찾아 엔진이 기대하는 규격으로 다시 그린다:
///
/// 1. 오츠 이진화로 잉크 마스크를 만든다(극성 자동).
/// 2. 잉크 경계 상자로 표시 줄을 찾는다.
/// 3. 잉크의 2차 모멘트로 기울기를 잡아 반대로 돌려 평평하게 한다.
/// 4. 상단 밴드의 세로 잉크 분포로 글자 클러스터를 나눈다(소수점은 하단이라
///    섞이지 않는다).
/// 5. 각 글자를 엔진 슬롯(4셀, 오른쪽 정렬, 빈 앞자리는 배경)으로 재샘플링
///    하고 퍼센타일 대비 스케일을 걸어 선명도 게이트가 볼 수 있게 한다.
///
/// 한계(알고 있는 것)
/// -------------------
/// - 셀 폭·간격 비율은 합성 데이터 생성기(tools/synth7seg)의 비율(셀 1:2,
///   간격 0.35 셀폭, 글자 오른쪽 끝 = 셀 폭의 0.9 지점)을 안다. 실촬 사진의
///   실제 혈당계 비율과는 다를 수 있다 — 이 도구는 합성 데이터로 판독 경로를
///   확인하려는 debug 기능이다.
/// - 원근 보정은 하지 않는다(±6% 흔들림은 셀 재배치가 흡수하는 정도).
/// - 글레어가 표시 일부를 지운 사진은 이진화가 무너져 실패할 수 있다.
///
/// 실패하면 null 을 돌려주고 호출자는 원본 프레임으로 넘어간다.
OcrFrame? preprocessPhotoForEngine(Uint8List pngBytes) {
  // 일부 실촬 JPEG 는 image 패키지 디코더가 마커를 이해하지 못하고
  // ImageException 을 던진다(2026-08-27 Datumo 표본에서 확인). 계약은
  // "해석할 수 없으면 null" 이므로 예외를 호출자 밖으로 흘려보내지 않는다.
  final img.Image? decoded;
  try {
    decoded = img.decodeImage(pngBytes);
  } catch (_) {
    return null;
  }
  if (decoded == null || decoded.width < 16 || decoded.height < 8) return null;

  var gray = <double>[
    for (var y = 0; y < decoded.height; y++)
      for (var x = 0; x < decoded.width; x++)
        0.299 * decoded.getPixel(x, y).r +
            0.587 * decoded.getPixel(x, y).g +
            0.114 * decoded.getPixel(x, y).b,
  ];

  // 1~3단계: 이진화 → 검출 → 기울기 보정. 잔차를 줄이려 두 번 돌린다.
  final initial = _displayBox(gray, decoded.width, decoded.height);
  if (initial == null) return null;
  var box = initial;

  for (var attempt = 0; attempt < 2; attempt++) {
    final angle = _skewAngle(gray, decoded.width, decoded.height, box);
    if (angle.abs() <= 0.002) break;
    gray = _rotate(gray, decoded.width, decoded.height, angle);
    final next = _displayBox(gray, decoded.width, decoded.height);
    if (next == null) return null;
    box = next;
  }

  // 4단계: 글자 클러스터(소수점이 있는 하단 밴드는 제외).
  final glyphs = _glyphColumns(
    gray,
    decoded.width,
    decoded.height,
    box,
  );
  if (glyphs.isEmpty || glyphs.length > 4) return null;

  // 5단계: 엔진 규격 캔버스로 재샘플링.
  return _renderSlots(gray, decoded.width, decoded.height, box, glyphs);
}

// ---------------------------------------------------------------------------
// 내부
// ---------------------------------------------------------------------------

class _Box {
  const _Box(this.left, this.top, this.right, this.bottom);
  final int left, top, right, bottom;
  int get w => right - left + 1;
  int get h => bottom - top + 1;
}

/// 오츠 이진화. 돌려주는 마스크는 "잉크" 위치만 true.
List<bool> _otsuInk(List<double> gray, int w, int h) {
  final hist = List<int>.filled(256, 0);
  for (final v in gray) {
    hist[v.clamp(0, 255).round()]++;
  }
  final total = gray.length;

  var bestThreshold = 128;
  var bestVariance = -1.0;
  var sumAll = 0.0;
  for (var i = 0; i < 256; i++) {
    sumAll += i * hist[i];
  }
  var sumBg = 0.0;
  var weightBg = 0;
  for (var t = 0; t < 256; t++) {
    weightBg += hist[t];
    if (weightBg == 0) continue;
    final weightFg = total - weightBg;
    if (weightFg == 0) break;
    sumBg += t * hist[t];
    final meanBg = sumBg / weightBg;
    final meanFg = (sumAll - sumBg) / weightFg;
    final variance =
        weightBg * weightFg * (meanBg - meanFg) * (meanBg - meanFg);
    if (variance > bestVariance) {
      bestVariance = variance;
      bestThreshold = t;
    }
  }

  final darkIsInk = _darkMinority(gray, bestThreshold);
  return [
    for (final v in gray)
      darkIsInk ? v < bestThreshold : v >= bestThreshold,
  ];
}

/// 잉크가 어두운 쪽인지 밝은 쪽인지 — 적은 쪽이 잉크다.
bool _darkMinority(List<double> gray, int threshold) {
  var dark = 0;
  for (final v in gray) {
    if (v < threshold) dark++;
  }
  return dark <= gray.length - dark;
}

/// 잉크 경계 상자. 잉크가 너무 적거나 화면을 다 덮으면 표시가 아니다.
_Box? _displayBox(List<double> gray, int w, int h) {
  final ink = _otsuInk(gray, w, h);
  var left = -1, top = -1, right = -1, bottom = -1;
  var count = 0;
  for (var y = 0; y < h; y++) {
    for (var x = 0; x < w; x++) {
      if (!ink[y * w + x]) continue;
      count++;
      if (left < 0 || x < left) left = x;
      if (x > right) right = x;
      if (top < 0 || y < top) top = y;
      if (y > bottom) bottom = y;
    }
  }
  if (count < w * h * 0.005) return null; // 잉크가 거의 없다
  if (count > w * h * 0.6) return null; // 배경-전경 구분 실패
  final box = _Box(left, top, right, bottom);
  if (box.w < 16 || box.h < 12) return null;
  return box;
}

/// 잉크 2차 모멘트로 기울기(라디안).
///
/// 하단 밴드(소수점 영역)는 제외한다 — 점 몇 개가 모멘트를 흔들어
/// 기울기를 틀기면 모든 글자가 비뚜로 그려진다.
double _skewAngle(List<double> gray, int w, int h, _Box box) {
  final ink = _otsuInk(gray, w, h);
  final bandBottom = box.top + (box.h * 0.65).round();
  var n = 0.0, sx = 0.0, sy = 0.0;
  for (var y = box.top; y <= bandBottom && y < h; y++) {
    for (var x = box.left; x <= box.right; x++) {
      if (ink[y * w + x]) {
        n++;
        sx += x;
        sy += y;
      }
    }
  }
  if (n < 8) return 0;
  final cx = sx / n, cy = sy / n;
  var xx = 0.0, yy = 0.0, xy = 0.0;
  for (var y = box.top; y <= box.bottom; y++) {
    for (var x = box.left; x <= box.right; x++) {
      if (!ink[y * w + x]) continue;
      final dx = x - cx, dy = y - cy;
      xx += dx * dx;
      yy += dy * dy;
      xy += dx * dy;
    }
  }
  return 0.5 * math.atan2(2 * xy, xx - yy);
}

/// 캔버스 중심 기준 회전(쌍선형). 범위 밖은 원본 가장자리를 늘린다.
List<double> _rotate(List<double> gray, int w, int h, double rad) {
  final cosT = math.cos(rad);
  final sinT = math.sin(rad);
  final cx = w / 2, cy = h / 2;
  return [
    for (var y = 0; y < h; y++)
      for (var x = 0; x < w; x++)
        () {
          final px = x - cx, py = y - cy;
          final sx = px * cosT - py * sinT + cx;
          final sy = px * sinT + py * cosT + cy;
          final x0 = sx.floor().clamp(0, w - 2);
          final y0 = sy.floor().clamp(0, h - 2);
          final tx = (sx - x0).clamp(0.0, 1.0);
          final ty = (sy - y0).clamp(0.0, 1.0);
          final tl = gray[y0 * w + x0];
          final tr = gray[y0 * w + x0 + 1];
          final bl = gray[(y0 + 1) * w + x0];
          final br = gray[(y0 + 1) * w + x0 + 1];
          final top = tl * (1 - tx) + tr * tx;
          final bottom = bl * (1 - tx) + br * tx;
          return top * (1 - ty) + bottom * ty;
        }(),
  ];
}

/// 상단 밴드(하단 35% 는 소수점 영역)의 세로 잉크 분포로 글자 클러스터.
/// 각 클러스터의 세로 잉크 범위도 함께 돌려준다 — 원근으로 자릿수마다
/// 세로가 흔들려도 슬롯 매핑이 글자별로 맞춰 흡수한다.
List<(int, int, int, int)> _glyphColumns(
  List<double> gray,
  int w,
  int h,
  _Box box,
) {
  final ink = _otsuInk(gray, w, h);
  final bandBottom = box.top + (box.h * 0.65).round();
  final colInk = List<int>.filled(box.w, 0);
  for (var y = box.top; y <= bandBottom && y < h; y++) {
    for (var x = box.left; x <= box.right; x++) {
      if (ink[y * w + x]) colInk[x - box.left]++;
    }
  }
  final minInk = math.max(2, (box.h * 0.08).round());

  final xClusters = <(int, int)>[];
  var start = -1;
  for (var i = 0; i < colInk.length; i++) {
    final on = colInk[i] >= minInk;
    if (on && start < 0) start = i;
    if ((!on || i == colInk.length - 1) && start >= 0) {
      final end = on ? i : i - 1;
      xClusters.add((box.left + start, box.left + end));
      start = -1;
    }
  }

  // 아주 좁은 조각(점·이물)은 버린다.
  final cellW = box.h / 0.9 / 2;
  final wide = xClusters
      .where((c) => c.$2 - c.$1 + 1 > cellW * 0.12)
      .toList();

  final result = <(int, int, int, int)>[];
  for (final c in wide) {
    var top = -1;
    var bottom = -1;
    for (var y = box.top; y <= box.bottom; y++) {
      for (var x = c.$1; x <= c.$2; x++) {
        if (ink[y * w + x]) {
          if (top < 0) top = y;
          bottom = y;
        }
      }
    }
    if (top >= 0) result.add((c.$1, c.$2, top, bottom));
  }
  return result;
}

/// 엔진 규격 캔버스: 높이 96, 4셀 × (셀폭 0.2275 + 간격 0.03).
OcrFrame? _renderSlots(
  List<double> gray,
  int w,
  int h,
  _Box box,
  List<(int, int, int, int)> glyphs,
) {
  const outH = 96.0;
  final outW = (outH * 2.1978).round();
  // 셀 폭 추정: 세로 잉크 높이 기반은 블러로 ±1~2px 흔들려 글자가 많아질수록
  // 누적 어긋난다. 인접 클러스터 중심 간 거리(= 셀 + 간격)를 직접 재는 게
  // 정확하다. 단, '1' 처럼 잉크가 셀의 오른쪽에만 있는 글자는 중심이
  // 오른쪽으로 치우쳐 피치를 오염시키므로, 세로 기반 추정의 ±12% 안에
  // 드는 후보만 쓴다. 하나도 없으면 세로 기반으로 돌아간다.
  final fallbackPitch = box.h / 0.9 / 2 * 1.35;
  double cellW;
  if (glyphs.length >= 2) {
    final centers = <double>[
      for (final g in glyphs) (g.$1 + g.$2) / 2,
    ];
    final candidates = <double>[
      for (var j = 1; j < centers.length; j++) centers[j] - centers[j - 1],
    ]
        .where((p) => (p - fallbackPitch).abs() < fallbackPitch * 0.12)
        .toList()
      ..sort();
    final pitch = candidates.isNotEmpty
        ? candidates[candidates.length ~/ 2]
        : fallbackPitch;
    // 생성기 비율: 간격 = 셀 폭의 0.35 → 피치 = 1.35 셀 폭.
    cellW = pitch / 1.35;
  } else {
    cellW = box.h / 0.9 / 2;
  }
  // 생성기 비율: 간격 = 셀 폭의 0.35 → 피치 = 1.35 셀 폭.
  final gap = cellW * 0.35;

  // 퍼센타일 대비 스케일 — 게이트(라플라시안 분산)와 이진화가 볼 수 있게.
  final crop = <double>[];
  for (var y = box.top; y <= box.bottom; y++) {
    for (var x = box.left; x <= box.right; x++) {
      crop.add(gray[y * w + x]);
    }
  }
  final sorted = [...crop]..sort();
  final lo = sorted[(sorted.length * 0.02).floor()];
  final hi = sorted[(sorted.length * 0.98).ceil() - 1];
  if (hi - lo < 12) return null; // 대비가 너무 낮아 아무것도 못 본다.
  double stretch(double v) => ((v - lo) / (hi - lo) * 255).clamp(0, 255);

  // 배경 추정(스케일 후) — 빈 슬롯과 여백을 채운다.
  final bgStretched = stretch(_backgroundLevel(crop, lo, hi));

  // 글자는 오른쪽 끝 글자부터 오른쪽 정렬. 오른쪽 끝 잉크 = 셀의 0.9 지점.
  final rightAnchor = box.right + 0.1 * cellW;
  final slotW = 0.2275 * outW;
  final pitch = slotW + 0.03 * outW;

  final out = Uint8List(outW * outH.toInt());
  for (var y = 0; y < outH.toInt(); y++) {
    for (var x = 0; x < outW; x++) {
      out[y * outW + x] = bgStretched.round();
    }
  }

  for (var i = 0; i < glyphs.length; i++) {
    // glyphs 는 왼쪽부터 — 뒤에서부터(i=0 이 오른쪽 끝 글자) 슬롯에 놓는다.
    final cellRight = rightAnchor - i * (cellW + gap);
    final cellLeft = cellRight - cellW;
    // 셀 폭만 1:1 로 샘플한다. 갭(소수점)까지 포함해 늘리면 오른쪽 세로
    // 획(B·C)이 엔진 샘플 박스 왼쪽으로 밀려 숫자가 무너진다. 소수점은
    // 아래에서 갭에서 검출해 박스 위치에 다시 그린다.
    final cropLeft = cellLeft;
    final cropW = cellW;

    final slotLeft = (outW - slotW) - i * pitch;
    // 이 글자의 세로 잉크 범위 — 원근 잔재를 자릿수마다 흡수한다.
    final glyphTop = glyphs[glyphs.length - 1 - i].$3.toDouble();
    final glyphBottom = glyphs[glyphs.length - 1 - i].$4.toDouble();
    for (var sy = 0; sy < outH; sy++) {
      for (var sx = 0; sx < slotW; sx++) {
        final u = cropLeft + (sx / slotW) * cropW;
        // 잉크(글자의 0~1)를 슬롯의 [0.05, 0.95] 로 — 엔진 기하가 잉크를
        // 셀 좌표 0.05~0.95 에 두고 세그먼트 박스를 잡기 때문이다.
        final glyphH = glyphBottom - glyphTop;
        final v = glyphTop +
            ((sy / outH - 0.05) / 0.9).clamp(0.0, 1.0) * glyphH;
        final value = stretch(
          _bilinear(gray, w, h, u, v.clamp(0.0, h - 1.0)),
        );
        final px = (slotLeft + sx).round();
        if (px < 0 || px >= outW) continue;
        // 소수점 박스(셀 우하단 x>0.88, y>0.85)는 일단 배경으로 둔다.
        // 셀 경계에서 번진 잉크가 점으로 오인되는 것을 막는다(318→3.18
        // 유형의 거짓 점). 진짜 점은 아래에서 갭에서 검출해 다시 그린다.
        final cellY = sy / outH;
        final cellX = sx / slotW;
        if (cellX > 0.88 && cellY > 0.85) continue;
        out[sy.round() * outW + px] = value.round();
      }
    }
  }

  // 소수점 복원 — 점은 글자 사이 갭의 하단에 있다. 갭 하단 밴드에 잉크가
  // 있으면 그 글자의 점으로 보고, 엔진이 보는 셀 우하단 박스에 그려 넣는다.
  final dots = _otsuInk(gray, w, h);
  final dotBandTop = box.top + (box.h * 0.6).round();
  final fgStretched = bgStretched > 127 ? 0 : 255;
  for (var i = 0; i < glyphs.length; i++) {
    final cellRight = rightAnchor - i * (cellW + gap);
    final gapX0 = (cellRight + gap * 0.05).round();
    final gapX1 = (cellRight + gap * 0.6).round();
    var dotInk = 0;
    for (var y = dotBandTop; y <= box.bottom; y++) {
      for (var x = gapX0; x <= gapX1 && x < w; x++) {
        if (x >= 0 && dots[y * w + x]) dotInk++;
      }
    }
    if (dotInk < 4) continue;

    final dotSlotLeft = (outW - slotW) - i * pitch;
    for (var y = (outH * 0.86).round(); y < (outH * 0.96).round(); y++) {
      for (
        var x = (dotSlotLeft + slotW * 0.90).round();
        x < (dotSlotLeft + slotW * 0.99).round();
        x++
      ) {
        if (x < 0 || x >= outW) continue;
        out[y * outW + x] = fgStretched;
      }
    }
  }

  return OcrFrame(
    bytes: out,
    format: OcrImageFormat.grayscale8,
    width: outW,
    height: outH.toInt(),
  );
}

double _backgroundLevel(List<double> crop, double lo, double hi) {
  // 잉크보다 배경이 넓다 — 히스토그램 양 끝 중 넓은 쪽이 배경.
  var nearLo = 0, nearHi = 0;
  final mid = (lo + hi) / 2;
  for (final v in crop) {
    if (v < mid) {
      nearLo++;
    } else {
      nearHi++;
    }
  }
  final bg = nearLo > nearHi ? lo : hi;
  return bg;
}

double _bilinear(List<double> gray, int w, int h, double x, double y) {
  final x0 = x.floor().clamp(0, w - 2);
  final y0 = y.floor().clamp(0, h - 2);
  final tx = (x - x0).clamp(0.0, 1.0);
  final ty = (y - y0).clamp(0.0, 1.0);
  final tl = gray[y0 * w + x0];
  final tr = gray[y0 * w + x0 + 1];
  final bl = gray[(y0 + 1) * w + x0];
  final br = gray[(y0 + 1) * w + x0 + 1];
  final top = tl * (1 - tx) + tr * tx;
  final bottom = bl * (1 - tx) + br * tx;
  return top * (1 - ty) + bottom * ty;
}
