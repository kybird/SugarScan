# 밴드 캔버스에서 글자 성분을 분할해 GT와 자동 정합하는 학습 데이터 생성.
#
# 원칙(사용자 지적): 등분할 금지. 성분 분할 개수 == GT 자릿수인 장만 학습에
# 쓴다 — 셀 라벨이 기계적으로 정확해진다. 안 맞는 장은 match_log에 기록.
#
# 산출: glyph_data/<class>_<id>_<k>.png (96×96) + glyph_data/match_log.csv
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "glyph_data"
BAND_W, BAND_H = 384, 128


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
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best:
            best = var
            thr = t
    mask = (gray <= thr).astype(np.uint8)
    if mask.sum() > total / 2:
        mask = 1 - mask
    return mask


def split_wide(boxes, mask):
    # 숫자들이 붙어 하나의 성분이 된 경우 — 컬럼 잉크 투영의 계곡에서 자른다.
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


def merge_boxes(boxes, max_h):
    # 가로 간격이 좁거나 겹치는 성분을 한 글자로 병합
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


def main() -> int:
    OUT.mkdir(exist_ok=True)
    labeled = [
        json.loads(l)
        for l in (HERE / "labeled.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    readings = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            readings[j["id"]] = j["reading"]
    corrections = {}
    corr = HERE / "gt_corrections.jsonl"
    if corr.exists():
        for l in corr.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                corrections[j["id"]] = j["corrected"]

    matched = mismatched = skipped = 0
    log = ["id,gt,glyphs,verdict"]
    for row in labeled:
        if row.get("source") != "human" or row.get("quad") is None:
            continue
        cid = row["id"]
        gt = str(corrections.get(cid, readings.get(cid)))
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            skipped += 1
            continue
        gray = cv2.cvtColor(
            np.asarray(Image.open(p).convert("RGB")), cv2.COLOR_RGB2GRAY)
        q = np.array(row["quad"], dtype=np.float32)
        xs, ys = q[:, 0], q[:, 1]
        src = np.array(
            [[xs.min(), ys.min()], [xs.max(), ys.min()],
             [xs.max(), ys.max()], [xs.min(), ys.max()]], dtype=np.float32)
        dst = np.array(
            [[0, 0], [BAND_W - 1, 0], [BAND_W - 1, BAND_H - 1], [0, BAND_H - 1]],
            dtype=np.float32)
        band = cv2.warpPerspective(gray, cv2.getPerspectiveTransform(src, dst),
                                   (BAND_W, BAND_H))
        # 극성 양쪽 시험 + 탐욕 정화: 성분 수 > GT 자릿수면 가장 작은 성분부터
        # 제거해 개수를 맞춘다(노이즈·단위 조각이 잉크 섞인 상자의 소수 성분).
        best_boxes = None
        best_drops = 99
        for invert in (False, True):
            mask = otsu_mask(band)
            if invert:
                mask = 1 - mask
            n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
            cand = [
                [stats[i, 0], stats[i, 1], stats[i, 2], stats[i, 3]]
                for i in range(1, n)
                if stats[i, 4] >= 12
            ]
            hm = max((b[3] for b in cand), default=0)
            cand = [b for b in cand if b[3] >= hm * 0.35]
            cand = merge_boxes(cand, hm)
            if len(cand) != len(gt):
                cand = split_wide(cand, mask)
            drops = 0
            while len(cand) > len(gt):
                cand.remove(min(cand, key=lambda b: b[3]))
                hm = max(b[3] for b in cand)
                drops += 1
            if len(cand) == len(gt) and drops < best_drops:
                best_boxes = [tuple(b) for b in cand]
                best_drops = drops
        if best_boxes is None:
            mismatched += 1
            log.append(f"{cid},{gt},-,no-polarity")
            continue
        boxes = best_boxes
        h_max = max(b[3] for b in boxes)
        if len(boxes) != len(gt):        h_max = max(b[3] for b in boxes)
        if len(boxes) != len(gt):
            mismatched += 1
            log.append(f"{cid},{gt},{len(boxes)},mismatch")
            continue
        s = max(8, h_max)
        for k, (bx, by, bw, bh) in enumerate(boxes):
            cls = int(gt[k])
            side = max(bw, bh) + int(s * 0.25)
            cx, cy = bx + bw / 2, by + bh / 2
            x0 = int(cx - side / 2)
            y0 = int(cy - side / 2)
            cell = np.full((side, side), 255, dtype=np.uint8)
            sx0, sy0 = max(0, x0), max(0, y0)
            sx1 = min(BAND_W, x0 + side)
            sy1 = min(BAND_H, y0 + side)
            if sx1 <= sx0 or sy1 <= sy0:
                continue
            patch = band[sy0:sy1, sx0:sx1]
            cell[sy0 - y0:sy0 - y0 + patch.shape[0],
                 sx0 - x0:sx0 - x0 + patch.shape[1]] = patch
            cell = cv2.resize(cell, (96, 96), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(OUT / f"{cls}_{cid.replace('/', '__')}_{k}.png"), cell)
        matched += 1
        log.append(f"{cid},{gt},{len(boxes)},match")

    (OUT / "match_log.csv").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"matched={matched} mismatched={mismatched} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
