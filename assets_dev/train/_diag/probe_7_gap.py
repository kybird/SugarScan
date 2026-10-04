# '7'(4세그먼트)의 F/B 세로획 꼭대기 위치 측정 — 세그먼트 규칙 준수 판정.
# F 중심 열에는 A 잉크가 닿지 않아 run 기반 틈 측정이 0 을 가짜로 내는
# 문제(make_glyph7_seg_kinds v1 라벨) 대신, 각 획의 꼭대기 y 를 A 밴드
# 바닥과 직접 비교한다.
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from synth_profiles import _value_glyph_mask  # noqa: E402

for variant in ("Regular", "Bold"):
    m = _value_glyph_mask("7", variant, 200)
    ink = m > 0
    h, w = ink.shape
    row = ink.sum(axis=1)
    bw = float(np.median(row[h // 2:]))
    a_rows = [i for i, v in enumerate(row) if v > bw * 1.8]
    a_top = min(a_rows)
    a_bot = max(r for r in a_rows if r < a_top + 40)
    print(f"{variant}: A밴드 y{a_top}~{a_bot} (두께 {a_bot - a_top + 1})")
    col = ink.sum(axis=0)
    tall = [i for i, c in enumerate(col) if c > h * 0.25]
    groups, s0 = [], tall[0]
    for i in range(1, len(tall)):
        if tall[i] != tall[i - 1] + 1:
            groups.append((s0, tall[i - 1]))
            s0 = tall[i]
    groups.append((s0, tall[-1]))
    for gx0, gx1 in groups:
        side = "F" if gx0 < w / 2 else "B"
        tops = [int(np.where(ink[:, x])[0][0]) for x in range(gx0, gx1 + 1)]
        print(f"  {side} x{gx0}~{gx1} 꼭대기 y{min(tops)}~{max(tops)}  "
              f"A바닥 대비 최소 {min(tops) - a_bot}px / 최대 {max(tops) - a_bot}px")
