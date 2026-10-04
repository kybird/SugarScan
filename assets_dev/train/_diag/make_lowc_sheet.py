# 저대비 대결 판 — 합성 최저대비 패널들 vs 실화면 저대비 사진.
# 사람 관찰 "현재 합성은 대비가 좋기만 한데 실화면은 대비 거의 없는 것도
# 있다"(2026-10-04)를 데이터로 검증한 결과, 합성 분포는 저대비 꼬리를 이미
# 덮고 있다(<40 1.67% vs 실측 0.72%). 이 판은 '축이 이미 있는데 사람 눈에
# 안 보였다'인지 '저대비 합성이 실화면과 다르게 생겼다'인지를 가린다.
#   위 두 줄: 실화면 밴드 크롭(대비 오름차순) · 아래 두 줄: 합성 Gmaster
#   최저대비 패널 밴드 크롭. 라벨에 대비값(p95−p5, 같은 자).
# 사용: python _diag/make_lowc_sheet.py
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from eval_reader import load_gray  # noqa: E402
from gm_quads import quad_rows  # noqa: E402
from measure_polarity import _load_jsonl, _rect_of, polarity_of  # noqa: E402

UPSTREAM = HERE.parent / "upstream" / "datumo"
OUT = HERE / "_diag" / "lowc_synth_vs_real_v2.png"
FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 15)
NS, NR = 6, 6                       # 합성·실화면 각 몇 장
CW, CH = 300, 110                   # 크롭 셀 크기


def band_contrast(gray, box):
    x0, y0, x1, y1 = box
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(gray.shape[1], int(x1)), min(gray.shape[0], int(y1))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None, None
    band = gray[y0:y1, x0:x1].astype(np.float32)
    return abs(float(np.percentile(band, 95)) - float(np.percentile(band, 5))), \
        gray[y0:y1, x0:x1]


# ── 실화면: polarity 실측 경로와 동일하게 GM 크롭 안 밴드 비율로 재고,
#    대비 오름차순 하위 NR 장의 밴드 크롭을 뽑는다.
quads = {r["id"]: r for r in quad_rows()}
bands = _load_jsonl(HERE / "band_boxes.jsonl")
real = []
for b in bands:
    g = quads.get(b["id"])
    if g is None:
        continue
    rel = UPSTREAM / "extracted" / "TILDE" / (b["id"].replace("/", "\\") + ".jpg")
    if not rel.exists():
        rel = UPSTREAM / "extracted" / "TILDE" / (b["id"] + ".jpg")
    if not rel.exists():
        continue
    img = load_gray(rel)
    if img is None:
        continue
    gx0, gy0, gx1, gy1 = _rect_of(g["quad"])
    gw, gh = gx1 - gx0, gy1 - gy0
    crop = img[max(0, int(gy0)):int(gy1), max(0, int(gx0)):int(gx1)]
    if min(crop.shape) < 24:
        continue
    bx0, by0, bx1, by1 = _rect_of(b["quad"])
    frac = ((bx0 - gx0) / gw, (by0 - gy0) / gh, (bx1 - gx0) / gw, (by1 - gy0) / gh)
    x0, y0 = int(frac[0] * crop.shape[1]), int(frac[1] * crop.shape[0])
    x1, y1 = int(np.ceil(frac[2] * crop.shape[1])), int(np.ceil(frac[3] * crop.shape[0]))
    c, band = band_contrast(crop, (x0, y0, x1, y1))
    if band is None:
        continue
    real.append((c, b["id"], band))
real.sort(key=lambda t: t[0])
real = real[:NR]
print("실화면 최저대비:", [(f"{c:.0f}", i) for c, i, _ in real])

# ── 합성: 대상 세트 표본 800장에서 밴드 대비 재서 최저 NS 장.
# 사용: python _diag/make_lowc_sheet.py [세트=GEN1P]  (Gmaster 판은 v1 로 남아 있다)
SET = sys.argv[1] if len(sys.argv) > 1 else "GEN1P"
root = HERE / "synth_coco" / SET
rows = [json.loads(l) for l in open(root / "manifest.jsonl", encoding="utf-8")]
random.Random(11).shuffle(rows)
synth = []
for r in rows[:800]:
    p = root / "train2017" / (r["id"] + ".png")
    if not p.exists():
        continue
    img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue
    c, band = band_contrast(img, r["box"])
    if band is None:
        continue
    synth.append((c, r["id"], band))
synth.sort(key=lambda t: t[0])
synth = synth[:NS]
print("합성 최저대비:", [(f"{c:.0f}", i) for c, i, _ in synth])


def paste_cell(canvas, dr, x, y, band, label):
    h, w = band.shape
    s = min(CW / w, CH / h)
    big = cv2.resize(band, (max(2, int(w * s)), max(2, int(h * s))),
                     interpolation=cv2.INTER_AREA)
    canvas.paste(Image.fromarray(big), (x + (CW - big.shape[1]) // 2,
                                        y + (CH - big.shape[0]) // 2))
    dr.text((x + 4, y + CH - 18), label, font=FONT, fill=255)


pad, lab = 12, 30
W = pad + max(NS, NR) * (CW + pad)
H = pad + lab + NR // 2 * (CH + pad) + lab + 40 + NS // 2 * (CH + pad) + pad
canvas = Image.new("L", (W, H), 24)
dr = ImageDraw.Draw(canvas)
dr.text((pad, 8), "실화면 최저대비 밴드(오름차순) — 대비 p95-p5, 같은 자",
        font=FONT, fill=220)
for k, (c, cid, band) in enumerate(real):
    paste_cell(canvas, dr, pad + (k % (NR // 2 + 2)) * 0 + (k % 3) * (CW + pad),
               pad + lab + (k // 3) * (CH + pad), band, f"{c:.0f}  {cid}")
y2 = pad + lab + 2 * (CH + pad) + 20
dr.text((pad, y2), "합성 Gmaster 최저대비 밴드(오름차순)", font=FONT, fill=220)
for k, (c, cid, band) in enumerate(synth):
    paste_cell(canvas, dr, pad + (k % 3) * (CW + pad),
               y2 + lab + (k // 3) * (CH + pad), band, f"{c:.0f}  {cid[-6:]}")
canvas.save(OUT)
print(f"저장: {OUT}")
