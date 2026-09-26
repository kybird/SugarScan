# 박스 절단 의심 장 추출 — 사람 눈검용(2026-09-26). C2 패널 위에 GT 박스
# (초록)와 검출 예측 박스(빨강)를 그리고, 아래에 "GT 밴드 크롭 vs 예측 박스
# 크롭(리더가 실제 본 입력)"을 나란히 붙인 jpg 를 절단 의심 장마다 남긴다.
# 사용: python extract_cut_suspects.py
import json

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = __import__("pathlib").Path(__file__).resolve().parent
C2 = HERE / "synth_coco" / "C2"
PRED = HERE / "_diag" / "bandft" / "C2_boxes_panel.jsonl"
OUT = HERE / "_diag" / "reader_digit_loss" / "cut_suspects"
FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 16)


def fit(im, h):
    s = h / im.shape[0]
    return cv2.resize(im, (max(2, int(im.shape[1] * s)), h))


def main() -> int:
    coco = json.loads((C2 / "annotations" / "instances_train2017.json")
                      .read_text(encoding="utf-8"))
    ims = {im["id"]: im for im in coco["images"]}
    gt = {}
    for a in coco["annotations"]:
        im = ims[a["image_id"]]
        x, y, w, h = a["bbox"]
        gt[im["file_name"]] = [x, y, x + w, y + h]
    pred = {}
    for l in PRED.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            pred[r["file_name"]] = r["pred"]

    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for fn, g in sorted(gt.items()):
        p = pred.get(fn)
        if p is None:
            continue
        lc, rc = p[0] - g[0], g[2] - p[2]
        if max(lc, rc) <= 10:
            continue
        img = cv2.imread(str(C2 / "train2017" / fn))
        H0 = img.shape[0]
        og = img.copy()
        cv2.rectangle(og, (int(g[0]), int(g[1])), (int(g[2]), int(g[3])),
                      (0, 200, 0), 2)
        cv2.rectangle(img, (int(p[0]), int(p[1])), (int(p[2]), int(p[3])),
                      (0, 0, 230), 2)
        gx = fit(img[int(g[1]):int(g[3]), int(g[0]):int(g[2])], 120)
        px_im = img[int(max(0, p[1])):int(p[3]),
                    int(max(0, p[0])):int(p[2])]
        px = (fit(px_im, 120) if px_im.size
              else np.full((120, 10, 3), 25, np.uint8))
        strip_w = max(og.shape[1], gx.shape[1] + px.shape[1] + 24)
        canvas = np.full((og.shape[0] + 140 + 34, strip_w, 3), 25, np.uint8)
        canvas[:og.shape[0], :og.shape[1]] = og
        canvas[og.shape[0] + 6:og.shape[0] + 126, :gx.shape[1]] = gx
        canvas[og.shape[0] + 6:og.shape[0] + 126,
               gx.shape[1] + 24:gx.shape[1] + 24 + px.shape[1]] = px
        im2 = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(im2)
        d.text((6, og.shape[0] + 132),
               f"{fn[:-4]}  라벨 GT=초록 · 예측=빨강 | 아래 왼쪽=GT 밴드 · "
               "오른쪽=예측 박스(리더 입력)", fill=(210, 210, 210), font=FONT)
        im2.save(str(OUT / fn.replace(".png", ".jpg")), quality=88)
        n += 1
    print(f"절단 의심 장 {n}장 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
