# glyph_cnn.keras 을 production-path 밴드 크롭 57장에 평가한다.
# 경로: 밴드 크롭 → 성분 분할(otsu+CC+병합+와이드분할) → 글자별 분류 → 조립.
import json
import re
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image

HERE = Path(__file__).resolve().parent
CROPS = HERE / "crops"
MODEL = HERE / "glyph_cnn.keras"
LABELS = HERE.parent / "upstream" / "datumo" / "labels.jsonl"


def otsu_mask(gray):
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = gray.size
    sum_all = float(np.dot(np.arange(256), hist))
    sum_b = 0.0
    w_b = 0.0
    best = -1.0
    thr = 128
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        var = w_b * w_f * ((sum_b / w_b) - ((sum_all - sum_b) / w_f)) ** 2
        if var > best:
            best = var
            thr = t
    mask = (gray <= thr).astype(np.uint8)
    if mask.sum() > total / 2:
        mask = 1 - mask
    return mask


def merge_boxes(boxes, max_h):
    boxes = sorted(boxes, key=lambda b: b[0])
    changed = True
    while changed:
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                gap = max(0, b[0] - (a[0] + a[2]))
                if gap <= max_h * 0.12:
                    x0 = min(a[0], b[0])
                    y0 = min(a[1], b[1])
                    x1 = max(a[0] + a[2], b[0] + b[2])
                    y1 = max(a[1] + a[3], b[1] + b[3])
                    boxes[i] = (x0, y0, x1 - x0, y1 - y0)
                    boxes.pop(j)
                    changed = True
                    break
            if changed:
                break
    return sorted(boxes, key=lambda b: b[0])


def split_wide(boxes, mask):
    out = []
    for (x, y, w, h) in boxes:
        if w <= h * 1.25 or w < 10 or h < 6:
            out.append((x, y, w, h))
            continue
        sub = mask[y:y + h, x:x + w]
        proj = sub.sum(axis=0).astype(np.float64)
        target = max(6, int(h * 0.62))
        cuts = [0]
        cx = 0
        while cx < w - 1:
            nxt = min(cx + target, w - 1)
            lo = max(cx + int(target * 0.45), nxt - int(target * 0.3))
            hi = min(w - 2, nxt + int(target * 0.3))
            if hi > lo:
                nxt = lo + int(np.argmin(proj[lo:hi + 1]))
            cuts.append(max(cuts[-1] + 3, nxt))
            cx = nxt
        cuts.append(w)
        for a, b in zip(cuts, cuts[1:]):
            if b - a >= 4:
                out.append((x + a, y, b - a, h))
    return out


def segment_glyphs(band_gray):
    mask = otsu_mask(band_gray)
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    boxes = [
        (stats[i, 0], stats[i, 1], stats[i, 2], stats[i, 3])
        for i in range(1, n)
        if stats[i, 4] >= 12
    ]
    if not boxes:
        return []
    h_max = max(b[3] for b in boxes)
    boxes = [b for b in boxes if b[3] >= h_max * 0.35]
    boxes = merge_boxes(boxes, h_max)
    boxes = split_wide(boxes, mask)
    return sorted(boxes, key=lambda b: b[0])


def main() -> int:
    model = tf.keras.models.load_model(MODEL)
    gt = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            gt[j["id"].replace("/", "__")] = j["reading"]

    crops = sorted(CROPS.glob("*.png"))
    exact = wrong = no_seg = 0
    misses = []
    for p in crops:
        gt_val = gt.get(p.stem)
        if gt_val is None:
            continue
        band = cv2.cvtColor(
            np.asarray(Image.open(p).convert("RGB")), cv2.COLOR_RGB2GRAY)
        boxes = segment_glyphs(band)
        if not boxes:
            no_seg += 1
            wrong += 1
            continue
        digits = []
        for k, (bx, by, bw, bh) in enumerate(boxes):
            side = max(bw, bh)
            cx, cy = bx + bw / 2, by + bh / 2
            x0 = int(cx - side / 2)
            y0 = int(cy - side / 2)
            cell = np.full((side, side), 255, dtype=np.uint8)
            sx0, sy0 = max(0, x0), max(0, y0)
            sx1 = min(band.shape[1], x0 + side)
            sy1 = min(band.shape[0], y0 + side)
            if sx1 <= sx0 or sy1 <= sy0:
                continue
            patch = band[sy0:sy1, sx0:sx1]
            cell[sy0 - y0:sy0 - y0 + patch.shape[0],
                 sx0 - x0:sx0 - x0 + patch.shape[1]] = patch
            cell = cv2.resize(cell, (96, 96), interpolation=cv2.INTER_AREA)
            x = np.asarray(cell, dtype=np.float32)[np.newaxis, ..., np.newaxis]
            x = np.repeat(x, 3, axis=-1)
            pred = model(x, training=False).numpy()[0]
            digits.append(str(int(np.argmax(pred))))
        reading = "".join(digits)
        if reading == str(gt_val):
            exact += 1
        else:
            wrong += 1
            misses.append((p.stem, gt_val, reading))
    total = exact + wrong
    print(f"crops={total} segmented={total - no_seg} no_seg={no_seg}")
    print(f"exact={exact} ({100 * exact / max(total, 1):.1f}%) wrong={wrong}")
    for m in misses[:12]:
        print("  MISS", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
