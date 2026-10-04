# glyph7_final4.png 이음새 간격 측정 — F가 A와 '떨어져 보인다'는 판정의 검증 자.
# 같은 기하(가로획 아래 세로획)끼리 비교한다:
#   A-F(좌상) vs A-B(우상) vs B-C(우중) 세로 틈, 그리고 F/B 좌우 정렬.
# 사용: python _diag/measure_glyph7_gaps.py [png경로]
import sys
from pathlib import Path

import numpy as np
from PIL import Image

png = Path(sys.argv[1] if len(sys.argv) > 1 else "_diag/glyph7_final4.png")
img = np.asarray(Image.open(png).convert("L"))
ink = img > 128

# 두 글리프 분리: 열 투영에서 잉크 없는 폭>=5 경계
colsum = ink.sum(axis=0)
splits, run = [], 0
for x, s in enumerate(colsum):
    if s == 0:
        run += 1
    else:
        if run >= 5:
            splits.append(x)
        run = 0
glyphs = []
prev = 0
for s in splits + [len(colsum)]:
    seg = ink[:, prev:s]
    if seg.sum() > 200:
        xs = np.where(seg.any(axis=0))[0] + prev
        ys = np.where(seg.any(axis=1))[0]
        glyphs.append({"x0": int(xs[0]), "x1": int(xs[-1]), "y0": int(ys[0]), "y1": int(ys[-1])})
    prev = s
print(f"{png.name}: 글리프 {len(glyphs)}개", [(g["x0"], g["x1"], g["y0"], g["y1"]) for g in glyphs])


def vgap_under_horizontal(g, x_center):
    """주어진 x(세로획 중심)에서: 위 가로획의 바닥 y 와 그 아래 세로획 꼭대기 y 의 틈."""
    col = ink[:, x_center]
    ys = np.where(col)[0]
    if len(ys) == 0:
        return None
    # 연결요소(행 run) 분리
    runs, start = [], ys[0]
    for i in range(1, len(ys)):
        if ys[i] != ys[i - 1] + 1:
            runs.append((start, ys[i - 1]))
            start = ys[i]
    runs.append((start, ys[-1]))
    if len(runs) < 2:
        return None
    # 두 번째 run(세로획 꼭대기) - 첫 run(가로획 바닥)
    return runs[1][0] - runs[0][1] - 1, runs


for g in glyphs:
    sub = ink[:, g["x0"]:g["x1"] + 1]
    row_ink = sub.sum(axis=1)
    # A 획: 위에서 첫 잉크 run
    ys = np.where(row_ink > 0)[0]
    runs, start = [], ys[0]
    for i in range(1, len(ys)):
        if ys[i] != ys[i - 1] + 1:
            runs.append((start, ys[i - 1]))
            start = ys[i]
    runs.append((start, ys[-1]))
    a_y0, a_y1 = runs[0]  # A run(행 투영 기준)
    # A 행들의 실제 좌우 끝
    a_rows = sub[a_y0:a_y1 + 1]
    a_x0 = g["x0"] + int(np.where(a_rows.any(axis=0))[0][0])
    a_x1 = g["x0"] + int(np.where(a_rows.any(axis=0))[0][-1])
    # B(우상 세로): A 구간 아래, 오른쪽 끝 근처 세로 run — 오른쪽 열 투영으로
    print(f"\n글리프 x{g['x0']}~{g['x1']} y{g['y0']}~{g['y1']}  A: y{a_y0}~{a_y1} x{a_x0}~{a_x1}")
    # 세로획 후보: 각 열의 잉크 픽셀 수가 큰 열들
    col_ink = sub.sum(axis=0)
    tall = [i for i, c in enumerate(col_ink) if c > (g["y1"] - g["y0"]) * 0.3]
    if not tall:
        continue
    # 군집화
    groups, s0 = [], tall[0]
    for i in range(1, len(tall)):
        if tall[i] != tall[i - 1] + 1:
            groups.append((s0, tall[i - 1]))
            s0 = tall[i]
    groups.append((s0, tall[-1]))
    mid = (a_x0 + a_x1) / 2
    for gx0, gx1 in groups:
        gx0a, gx1a = g["x0"] + gx0, g["x0"] + gx1
        tag = "세로획"
        if gx1a < mid:
            tag = "F(좌)" if len(groups) >= 3 else "?(좌)"
        elif gx0a > mid:
            tag = "B+C(우)" if len(groups) == 2 else "B/C(우)"
        # 해당 열 중심에서 A 아래 첫 틈
        r = vgap_under_horizontal(g, (gx0a + gx1a) // 2)
        w = gx1a - gx0a + 1
        if r:
            gap, colruns = r
            print(f"  {tag} x{gx0a}~{gx1a} (폭{w})  A바닥~꼭대기 틈: {gap}px")
        else:
            print(f"  {tag} x{gx0a}~{gx1a} (폭{w})  틈 측정 불가(단일 run)")
