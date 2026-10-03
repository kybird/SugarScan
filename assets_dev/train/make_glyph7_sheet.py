# 합성 7 vs 실촬 7 대조 시트 — 리더 눈높이(144x96 크롭)로 놓는다.
#
# 사람 질문(2026-10-03): "우리가 만든 7과 실촬의 7이 뭐가 다르냐?"
# 끝단 오독의 다수가 7→1 치환이다 — 7세그 7=A+B+C, 1=B+C 라 위 가로획
# 하나 차이다. 실촬 7의 위 가로획이 합성보다 짧/옅거나 위치가 다르면
# 리더가 1로 읽는다. 근원을 눈으로 가린다.
#
# 세 층:
#   1) 실촬 · 7 포함 오독 장 크롭(빨강 테두리 — GT/pred 캡션)
#   2) 실촬 · 7 포함 정답 장 크롭(초록 — 읽힌 7이 어떻게 생겼나)
#   3) 합성 B2 · label 7 포함 크롭(리더가 학습한 그 상자/그 크기)
# 모든 크롭은 리더 인풋 규약(grayscale → 144x96) 그대로 — 판정 환경과
# 동일한 픽셀에서 비교한다.
#
# 사용:
#   python make_glyph7_sheet.py
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"


def real_crop(cid, box, imgs):
    im = cv2.imread(str(DATUMO / imgs[cid]), cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    x0, y0 = max(0, int(box[0])), max(0, int(box[1]))
    x1 = min(im.shape[1], int(round(box[2])))
    y1 = min(im.shape[0], int(round(box[3])))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    return cv2.resize(im[y0:y1, x0:x1], (144, 96))


def synth_crop(fname, box):
    im = cv2.imread(str(HERE / "synth_coco" / "B2" / "train2017" / fname),
                    cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    x0, y0 = max(0, int(box[0])), max(0, int(box[1]))
    x1 = min(im.shape[1], int(round(box[2])))
    y1 = min(im.shape[0], int(round(box[3])))
    return cv2.resize(im[y0:y1, x0:x1], (144, 96))


def tile(img, tag, border):
    t = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(t, (0, 0), (143, 95), border, 2)
    cv2.rectangle(t, (0, 74), (143, 95), (20, 20, 20), -1)
    cv2.putText(t, tag, (3, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                (255, 255, 255), 1)
    return t


def row(tiles, h=96, gap=6):
    canvas = np.full((h, tiles[0].shape[1] * len(tiles) + gap * (len(tiles) - 1),
                      3), 24, np.uint8)
    for i, t in enumerate(tiles):
        x = i * (t.shape[1] + gap)
        canvas[:, x:x + t.shape[1]] = t
    return canvas


def main():
    imgs = {}
    for line in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            imgs[j["id"]] = j["image"]
    e2e = [json.loads(l) for l in
           (HERE / "_diag" / "e2e_bandnet" / "atone_tg640w15.jsonl")
           .read_text(encoding="utf-8").splitlines() if l.strip()]
    pred_boxes = {}
    for line in (HERE / "band_quads_pred.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            if j.get("quad"):
                xs = [p[0] for p in j["quad"]]
                ys = [p[1] for p in j["quad"]]
                pred_boxes[j["id"]] = [min(xs), min(ys), max(xs), max(ys)]

    wrong7 = [r for r in e2e if r["verdict"] == "wrong" and "7" in str(r["gt"])][:8]
    right7 = [r for r in e2e if r["verdict"] == "right" and "7" in str(r["gt"])][:6]

    t1 = []
    for r in wrong7:
        c = real_crop(r["id"], pred_boxes.get(r["id"]), imgs)
        if c is not None:
            t1.append(tile(c, f"{r['gt']}>{r.get('pred','?')}", (0, 0, 255)))
    t2 = []
    for r in right7:
        c = real_crop(r["id"], pred_boxes.get(r["id"]), imgs)
        if c is not None:
            t2.append(tile(c, f"GT {r['gt']}", (0, 200, 0)))

    boxes = {}
    for line in (HERE / "_diag" / "reader_boxes" / "B2_tg640w15.jsonl").read_text(
            encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            boxes[j["file_name"]] = j["pred"]
    labels = {}
    for line in (HERE / "synth_coco" / "B2" / "manifest.jsonl").read_text(
            encoding="utf-8").splitlines():
        if line.strip():
            m = json.loads(line)
            labels[f"{m['id']}.png"] = m["label"]
    syn = []
    for fname, box in boxes.items():
        if "7" in labels.get(fname, "") and len(syn) < 8:
            c = synth_crop(fname, box)
            if c is not None:
                syn.append(tile(c, f"syn {labels[fname]}", (255, 180, 0)))

    rows = [row(t1), row(t2), row(syn)]
    h = sum(r.shape[0] for r in rows) + 8 * (len(rows) - 1)
    w = max(r.shape[1] for r in rows)
    sheet = np.full((h, w, 3), 12, np.uint8)
    y = 0
    for r in rows:
        sheet[y:y + r.shape[0], :r.shape[1]] = r
        y += r.shape[0] + 8
    out = HERE / "_diag" / "glyph7_vs_real.png"
    cv2.imwrite(out, sheet)
    print(f"{out} · 오독7 {len(t1)} · 정답7 {len(t2)} · 합성7 {len(syn)}")


if __name__ == "__main__":
    main()
