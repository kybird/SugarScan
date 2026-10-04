# 7 두 종류 검수판 v3 — 사람 눈검 + 자가 픽셀 측정 + 코너 확대 삽입.
#   '7'  = DSEG 원형 4세그먼트(A+B+C+F) — 종래부터 이 형태였다
#   '7s' = F 성분을 뺀 3세그먼트(A+B+C) — 새로 추가(사람 결정 2026-10-04)
# 판정 초점(사람 지적 "추가한 F 획이 세그먼트 규칙을 안지킨다"):
#   F 모서리가 B 모서리와 같은 규칙(A 아래 틈·절단각·두께)을 지키는가.
#   v1 라벨의 "좌틈 0px" 은 측정 오류였다 — F 중심 열에 A 잉크가 없어
#   run 이 하나뿐이면 기본값 0 을 찍은 것. v2 는 안쪽 귀 꼭대기와
#   A 밴드 바닥을 직접 비교한다(A 밴드는 세로획 전용 행 대비 1.5배 문턱).
# 사용: python _diag/make_glyph7_seg_kinds.py
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from synth_profiles import _value_glyph_mask  # noqa: E402

OUT = Path(__file__).resolve().parent / "glyph7_seg_kinds_v3.png"
FONT = Path("C:/Windows/Fonts/malgun.ttf")


def analyze(mask):
    """A 밴드·세로획 그룹·안쪽 귀 꼭대기·두께·틈을 잰다."""
    ink = mask > 0
    h, w = ink.shape
    row = ink.sum(axis=1)
    # A 밴드 = 최대 행 잉크의 55% 이상인, 맨 위에서 연속된 구간.
    # 세로획만 있는 행(F+B≈40px)은 A 행(전폭)보다 훨씬 적어 여기서 끊긴다.
    thr = 0.55 * float(row.max())
    a_top, a_bot = 0, 0
    while a_bot + 1 < h and row[a_bot + 1] > thr:
        a_bot += 1
    a_cols = np.nonzero(ink[a_top:a_bot + 1].any(axis=0))[0]
    col = ink.sum(axis=0)
    tall = [i for i, c in enumerate(col) if c > h * 0.25]
    groups, s0 = [], tall[0]
    for i in range(1, len(tall)):
        if tall[i] != tall[i - 1] + 1:
            groups.append((s0, tall[i - 1]))
            s0 = tall[i]
    groups.append((s0, tall[-1]))
    segs = []
    for gx0, gx1 in groups:
        # 안쪽 귀 = 글리프 중심 쪽 끝 열의 꼭대기
        x_in = gx1 if gx0 < w / 2 else gx0
        top_in = int(np.where(ink[:, x_in])[0][0])
        # 그 열 위 A 잉크가 있으면 run 틈, 없으면 A 밴드 바닥과의 거리
        ys = np.where(ink[:, x_in])[0]
        runs, st = [], ys[0]
        for i in range(1, len(ys)):
            if ys[i] != ys[i - 1] + 1:
                runs.append((st, ys[i - 1]))
                st = ys[i]
        runs.append((st, ys[-1]))
        if len(runs) >= 2:
            gap = runs[1][0] - runs[0][1] - 1
        else:
            gap = top_in - a_bot - 1
        segs.append({"side": "F" if gx0 < w / 2 else "B",
                     "gap": gap, "tw": gx1 - gx0 + 1})
    return {"a_top": a_top, "a_bot": a_bot, "a_w": int(a_cols[-1] - a_cols[0] + 1),
            "segs": segs, "ink": ink}


specs = [("Regular", "7"), ("Regular", "7s"), ("Bold", "7"), ("Bold", "7s")]
gh, cell_w, pad = 200, 250, 26
inset, zoom = 62, 3            # 코너 크롭 크기·배율
lab1, lab2, ins_h = 26, 3 * 20, inset * zoom
W = pad * 2 + cell_w * len(specs)
H = pad + gh + ins_h + lab1 + lab2 * 2 + pad
canvas = Image.new("L", (W, H), 235)
dr = ImageDraw.Draw(canvas)
f1 = ImageFont.truetype(str(FONT), 18)
f2 = ImageFont.truetype(str(FONT), 14)

dr.text((pad, 8), "7 두 종류(값 숫자·파라메트릭) — '7'=A+B+C+F(종래형) / '7s'=A+B+C(신규) · 아래는 '7' 의 F·B 모서리 3배 확대",
        font=f2, fill=80)
for idx, (variant, ch) in enumerate(specs):
    m = _value_glyph_mask(ch, variant, gh)
    assert m is not None, (variant, ch)
    st = analyze(m)
    x0 = pad + idx * cell_w + (cell_w - m.shape[1]) // 2
    arr = (255 - m.astype(np.uint8) * 255).astype(np.uint8)
    canvas.paste(Image.fromarray(arr), (x0, pad))
    y = pad + gh + 6
    dr.text((x0, y), f"{variant} '{ch}'  {'A+B+C+F' if ch == '7' else 'A+B+C'}",
            font=f1, fill=0)
    y += lab1
    for s in st["segs"]:
        dr.text((x0, y), f"{s['side']}획: A아래 틈 {s['gap']}px · 두께 {s['tw']}px",
                font=f2, fill=60)
        y += 20
    # '7' 에만 코너 확대 — F(좌상) vs B(우상) 절단·틈 비교
    if ch == "7":
        h_, w_ = m.shape
        for k, (cx0, label) in enumerate([(0, "F 모서리"), (w_ - inset, "B 모서리")]):
            crop = m[0:inset, max(0, cx0):max(0, cx0) + inset]
            big = Image.fromarray(
                (255 - crop.astype(np.uint8) * 255).astype(np.uint8))
            big = big.resize((inset * zoom, inset * zoom), Image.NEAREST)
            canvas.paste(big, (x0 + k * (inset * zoom + 14), y + 4))
        dr.text((x0, y + ins_h + 8),
                f"F 모서리(좌) vs B 모서리(우) 3배 — A아래 틈·절단각 비교",
                font=f2, fill=60)
    print(f"{variant} '{ch}': A y{st['a_top']}~{st['a_bot']} 폭{st['a_w']} | " +
          " | ".join(f"{s['side']}틈{s['gap']}px 두께{s['tw']}px" for s in st["segs"]))

canvas.save(OUT)
print(f"저장: {OUT}")
