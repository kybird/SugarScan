# GEN1 프로브 눈검판 ① — 값에 7 이 들어간 패널에서 두 종류 실장 확인.
#   위 줄: seven='7'(A+B+C+F) · 아래 줄: seven='7s'(A+B+C)
# 라벨에 값·종류·c_deg·열화. 밴드 상자 주변 여유를 두고 크롭.
# 사용: python _diag/make_gen1_7s_sheet.py
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE / "synth_coco" / "GEN1P"
OUT = HERE / "_diag" / "gen1_7s_panels_v1.png"
FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 15)

rows = [json.loads(l) for l in
        (ROOT / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
picks = {"7": [], "7s": []}
for r in rows:
    if "7" in r.get("label", "") and len(picks[r["seven"]]) < 4:
        picks[r["seven"]].append(r)

CW, CH, pad = 380, 150, 10
W = pad + 4 * (CW + pad)
H = pad + 2 * (CH + 46) + pad
canvas = Image.new("L", (W, H), 235)
dr = ImageDraw.Draw(canvas)

y = pad
for kind, title in (("7", "seven='7' — A+B+C+F(4세그먼트)"),
                    ("7s", "seven='7s' — A+B+C(3세그먼트)")):
    dr.text((pad, y), title, font=FONT, fill=0)
    y += 24
    for k, r in enumerate(picks[kind]):
        img = cv2.imread(str(ROOT / "train2017" / (r["id"] + ".png")),
                         cv2.IMREAD_GRAYSCALE)
        x0, y0, x1, y1 = [int(v) for v in r["box"]]
        m = int(0.10 * (y1 - y0))
        x0, y0 = max(0, x0 - m), max(0, y0 - m)
        x1, y1 = min(img.shape[1], x1 + m), min(img.shape[0], y1 + m)
        band = img[y0:y1, x0:x1]
        s = min(CW / band.shape[1], CH / band.shape[0])
        big = cv2.resize(band, (max(2, int(band.shape[1] * s)),
                                max(2, int(band.shape[0] * s))),
                         interpolation=cv2.INTER_AREA)
        x = pad + k * (CW + pad)
        canvas.paste(Image.fromarray(big),
                     (x + (CW - big.shape[1]) // 2, y + (CH - big.shape[0]) // 2))
        deg = r.get("degrade", {})
        dr.text((x, y + CH + 4),
                f"{r['label']} · {r['profile'][:18]} · c{r.get('c_deg', 0):.2f} · "
                f"n{deg.get('noise', 0)} b{deg.get('blur', 0)}",
                font=FONT, fill=60)
    y += CH + 30
print("7 포함 픽:", {k: [r["id"][-4:] + "=" + r["label"] for r in v]
                     for k, v in picks.items()})
canvas.save(OUT)
print(f"저장: {OUT}")
