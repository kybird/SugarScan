# 7f 조립 설계 프로브 — 두 가지를 확인한다:
#  (1) 순수 파라메트릭 '7'(_value_glyph_mask) 구조: 왼쪽 세로획이 없어야 한다
#      (final4 판에서 왼쪽 글리프에도 왼쪽 세로획이 잡힌 것은 판 스크립트 버그였는지)
#  (2) '4' 래스터(h=300, '7'과 동일 base_h) 연결요소 분해: F 세그먼트가
#      독립 성분으로 나오는가, 위치는 '7' 래스터 좌표계와 일치하는가
# 사용: python _diag/probe_7f_parts.py
import sys
from pathlib import Path

import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from synth_profiles import _value_glyph_mask, _dseg_raster  # noqa: E402


def dump_tall_columns(mask, name):
    ink = mask > 0
    h, w = ink.shape
    col_ink = ink.sum(axis=0)
    thresh = h * 0.25
    tall = [i for i, c in enumerate(col_ink) if c > thresh]
    if not tall:
        print(f"{name}: 긴 세로 열 없음")
        return
    groups, s0 = [], tall[0]
    for i in range(1, len(tall)):
        if tall[i] != tall[i - 1] + 1:
            groups.append((s0, tall[i - 1]))
            s0 = tall[i]
    groups.append((s0, tall[-1]))
    print(f"{name} ({w}x{h}) 긴 세로 열: " + ", ".join(f"x{a}~{b}(폭{b-a+1})" for a, b in groups))


m7 = _value_glyph_mask("7", "Regular", 200)
print("파라메트릭 '7' 순수 출력:")
dump_tall_columns(m7, "  '7'")

base_h = 300
r7 = _dseg_raster("7", "Regular", base_h)
r4 = _dseg_raster("4", "Regular", base_h)
r0 = _dseg_raster("0", "Regular", base_h)
for name, r in [("7", r7), ("4", r4), ("0", r0)]:
    if r is None:
        print(f"DSEG '{name}' 래스터 실패")
        continue
    m = (r > 0).astype(np.uint8)
    n, lab = cv2.connectedComponents(m)
    print(f"\nDSEG '{name}' {m.shape[1]}x{m.shape[0]} 연결요소 {n-1}개:")
    H0, W0 = m.shape
    for i in range(1, n):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 8:
            continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        kind = "가로" if (x1 - x0) > (y1 - y0) else "세로"
        side = ""
        if kind == "세로":
            side = "좌" if (x0 + x1) / 2 < W0 / 2 else "우"
            half = "상" if (y0 + y1) / 2 < H0 / 2 else "하"
            side += half
        print(f"  comp{i}: x{x0}~{x1} y{y0}~{y1} ({x1-x0+1}x{y1-y0+1}) {kind}{side}")
