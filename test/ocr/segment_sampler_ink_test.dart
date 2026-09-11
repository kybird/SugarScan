import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

/// G19 — `SegmentSampler` 의 잉크 정규화(`normalizeToInk`) 규칙을 고정한다.
///
/// 셀 세로 범위가 숫자가 아니라 ROI 전체 높이일 때 A·D 박스가 여백을 재
/// `0`→`H`·`8`→`H` 를 낸다는 G15 발견의 재현이기도 하다 — 숫자를 셀의 한가운데
/// 밴드에만 그려 넣으면 기존 경로는 위·아래 가로 획을 놓친다.
void main() {
  // 셀 100x100. 숫자의 잉크는 지정한 상자 안에만 그린다.
  const size = 100;
  const cell = NormalizedRect(left: 0, top: 0, width: 1, height: 1);

  BinaryLcd lcdWithInkBox(
    double inkLeft,
    double inkTop,
    double inkWidth,
    double inkHeight, {
    bool neighborBleed = false,
  }) {
    final foreground = Uint8List(size * size);
    void fill(_Rect r) {
      for (var y = r.top; y < r.bottom; y++) {
        for (var x = r.left; x < r.right; x++) {
          foreground[y * size + x] = 1;
        }
      }
    }

    // '8' — 일곱 획 전부. 획은 잉크 상자 기준 SegmentGeometry 비율로 그리고
    // 반올림 경계를 감안해 ±2px 늘린다.
    for (final box in SegmentGeometry.standard.segments) {
      fill(_Rect.fromLTWH(
        (inkLeft + box.left * inkWidth).round() - 2,
        (inkTop + box.top * inkHeight).round() - 2,
        ((box.right - box.left) * inkWidth).round() + 4,
        ((box.bottom - box.top) * inkHeight).round() + 4,
      ));
    }
    if (neighborBleed) {
      // 셀 전체 폭에 걸친 가로 줄 — 이웃 자릿수의 획이 셀에 걸쳐 든 모형.
      fill(_Rect.fromLTWH(0, (inkTop + inkHeight / 2).round() - 2, size, 4));
    }

    return BinaryLcd(
      foreground: foreground,
      width: size,
      height: size,
      threshold: 128,
      darkOnLight: true,
      separability: 1,
      foregroundRatio: 0.2,
    );
  }

  GlyphMatch read(BinaryLcd lcd, {required bool normalizeToInk}) {
    final sample = SegmentSampler.sample(
      lcd,
      cell,
      SegmentGeometry.standard,
      normalizeToInk: normalizeToInk,
    );
    return SegmentPatternTable.match(sample.bits);
  }

  test('잉크가 셀의 한가운데 밴드면 정규화가 8 을 살린다', () {
    // 잉크 높이 45%(≥40%), 폭 60%(≤95%) — 정규화 조건 충족.
    final lcd = lcdWithInkBox(20, 30, 60, 45);

    final off = read(lcd, normalizeToInk: false);
    final on = read(lcd, normalizeToInk: true);

    // 기존 경로는 위·아래 가로(A·D)를 여백에서 재서 8 이 아니다.
    expect(off is DigitGlyph && off.digit == 8, isFalse);
    // 잉크 경계 상자 기준으로는 일곱 획이 모두 잡힌다.
    expect(on, isA<DigitGlyph>().having((g) => g.digit, 'digit', 8));
  });

  test('잉크 높이가 셀의 40% 미만이면 정규화하지 않는다', () {
    // 높이 30% — 숫자가 아닐 가능성이 높다는 스펙의 걸러냄.
    final lcd = lcdWithInkBox(20, 35, 60, 30);

    final off = SegmentSampler.sample(
      lcd, cell, SegmentGeometry.standard, normalizeToInk: false,
    );
    final on = SegmentSampler.sample(
      lcd, cell, SegmentGeometry.standard, normalizeToInk: true,
    );

    expect(on.bits, off.bits, reason: '40% 미만은 기존 경로로 떨어져야 한다');
  });

  test('잉크 폭이 셀의 95% 초과면 정규화하지 않는다', () {
    // 이웃 자릿수가 셀 전체 폭에 걸쳐 들어온 모형 — 스펙의 걸러냄.
    final lcd = lcdWithInkBox(20, 30, 60, 45, neighborBleed: true);

    final off = SegmentSampler.sample(
      lcd, cell, SegmentGeometry.standard, normalizeToInk: false,
    );
    final on = SegmentSampler.sample(
      lcd, cell, SegmentGeometry.standard, normalizeToInk: true,
    );

    expect(on.bits, off.bits, reason: '95% 초과는 기존 경로로 떨어져야 한다');
  });
}

/// 여기서만 쓰는 최소 사각형(외부 Rect 타입과 무관).
class _Rect {
  _Rect.fromLTWH(this.left, this.top, int width, int height)
      : right = left + width,
        bottom = top + height;

  final int left;
  final int top;
  final int right;
  final int bottom;
}
