import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;
import 'package:sugarscan/features/scan/photo_preprocessor.dart';

/// 원근 펴기 코어 — 검출 없이 모서리 4점으로 사진을 엔진 규격(211×96)으로 편다.
/// 엔진 호출 없이 기하만 검증한다(판독 종단은 golden_bench 가 한다).
void main() {
  const w = 211, h = 96;

  /// raw 픽셀(행우선) — 비교 기준. PNG 바이트와 혼동하지 않는다.
  /// 패턴은 세로로 균일하므로 행 인덱스는 쓰이지 않는다.
  final raw = List<int>.generate(w * h, (i) {
    final x = i % w;
    final inBar = (x >= 20 && x < 32) || (x >= 100 && x < 112) || (x >= 180 && x < 192);
    return inBar ? 20 : 235;
  });

  Uint8List patternPng() {
    final im = img.Image(width: w, height: h);
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        im.setPixelRgb(x, y, raw[y * w + x], raw[y * w + x], raw[y * w + x]);
      }
    }
    return img.encodePng(im);
  }

  ({double x, double y}) pt(double x, double y) => (x: x, y: y);

  final identity = [pt(0, 0), pt(w - 1, 0), pt(w - 1, h - 1), pt(0, h - 1)];

  test('출력은 엔진 규격 캔버스(grayscale8 211×96)다', () {
    final frame = warpQuadToEngineFrame(patternPng(), identity);
    expect(frame, isNotNull);
    expect(frame!.width, 211);
    expect(frame.height, 96);
    expect(frame.bytes.length, 211 * 96);
  });

  test('항등 모서리면 화면이 보존된다', () {
    final frame = warpQuadToEngineFrame(patternPng(), identity)!;
    // 출력에는 퍼센타일 대비 스트레치가 걸린다(20→0, 235→255). 원본 raw 를
    // 같은 스트레치로 변환한 값과 비교한다.
    var diff = 0;
    for (var i = 0; i < frame.bytes.length; i++) {
      final stretched = ((raw[i] - 20) * 255 / 215).round().clamp(0, 255);
      diff += (frame.bytes[i] - stretched).abs();
    }
    expect(diff / frame.bytes.length, lessThan(12.0));
  });

  test('회전 모서리는 회전된 위치에 잉크를 놓는다', () {
    final rad = 12 * math.pi / 180;
    ({double x, double y}) rot(double x, double y) {
      const cx = w / 2, cy = h / 2;
      final dx = x - cx, dy = y - cy;
      return (
        x: cx + dx * math.cos(rad) - dy * math.sin(rad),
        y: cy + dx * math.sin(rad) + dy * math.cos(rad),
      );
    }

    final frame = warpQuadToEngineFrame(
      patternPng(),
      [rot(0, 0), rot(w - 1, 0), rot(w - 1, h - 1), rot(0, h - 1)],
    )!;

    // 원본의 첫 바(x=20..31) 중심축 x=26 이 출력에서 어디로 가는지 —
    // 샘플링이 캔버스→사진을 +12° 회전으로 물었으므로 내용은 사진에서
    // −12° 방향으로 옮겨져 보인다.
    ({double x, double y}) fwd(double sx, double sy) {
      final dx = sx - w / 2, dy = sy - h / 2;
      return (
        x: (frame.width - 1) / 2 + dx * math.cos(rad) + dy * math.sin(rad),
        y: (frame.height - 1) / 2 - dx * math.sin(rad) + dy * math.cos(rad),
      );
    }

    bool inkAt(int x, int y) =>
        x >= 0 && x < frame.width && frame.bytes[y * frame.width + x] < 100;

    for (final (sx, sy) in const [(26.0, 20.0), (26.0, 48.0), (26.0, 76.0)]) {
      final want = fwd(sx, sy);
      var found = false;
      for (var dx = -3; dx <= 3; dx++) {
        if (inkAt((want.x + dx).round(), want.y.round())) found = true;
      }
      expect(found, isTrue, reason: 'src($sx,$sy) → want (${want.x},${want.y})');
    }
  });

  test('키스톤 모서리는 원근(위/아래 폭 비)를 따른다', () {
    // 위 변을 절반 폭으로 좁힌 사다리꼴 — 아핀으로는 성립하지 않는 대응.
    const topScale = 0.5;
    final frame = warpQuadToEngineFrame(patternPng(), [
      pt((w - 1) * (1 - topScale) / 2, 0),
      pt((w - 1) * (1 + topScale) / 2, 0),
      pt((w - 1).toDouble(), (h - 1).toDouble()),
      pt(0, (h - 1).toDouble()),
    ])!;

    int barWidthAt(int y) {
      var best = 0, run = 0;
      for (var x = 0; x < frame.width; x++) {
        if (frame.bytes[y * frame.width + x] < 100) {
          run++;
          if (run > best) best = run;
        } else {
          run = 0;
        }
      }
      return best;
    }

    final topW = barWidthAt(4);
    final bottomW = barWidthAt(frame.height - 5);
    // 캔버스 위 행은 사진의 좁은 스팬(≈절반 폭)을 늘려 담는다 — 즉 위쪽 바가
    // 1/topScale 배로 확대되어 보인다.
    expect(topW / bottomW, closeTo(1 / topScale, 0.35),
        reason: 'top=$topW bottom=$bottomW');
  });

  test('퇴화 모서리(한 직선)는 null 을 돌려준다', () {
    final frame = warpQuadToEngineFrame(patternPng(), [
      pt(0, 10), pt(100, 10), pt(200, 10), pt(150, 10),
    ]);
    expect(frame, isNull);
  });
}
