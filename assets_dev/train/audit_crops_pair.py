# 2026-11-19 지시서 §3 — 크롭 파일별 비교(자): ps10b vs ps10d crops.jsonl
# 중앙값 비교로 끝내지 않고 file_name 조인으로 전수 비교한다.
import json
from collections import Counter

import numpy as np


def load(path):
    rows = {}
    for line in open(path, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            rows[r["file_name"]] = r
    return rows


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    ua = ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1])
          - inter)
    return inter / ua if ua > 0 else 0.0


A = load("band_out/ps10b_det_neg25_crops.jsonl")
B = load("band_out/ps10d_det640_crops.jsonl")
ka, kb = set(A), set(B)
print(f"ps10b {len(A)}행 · ps10d {len(B)}행 · 공통 {len(ka & kb)} · "
      f"ps10b만 {len(ka - kb)} · ps10d만 {len(kb - ka)}")

for name, D in (("ps10b", A), ("ps10d", B)):
    print(f"{name}: kind={dict(Counter(r.get('kind') for r in D.values()))} "
          f"· pred 있음 {sum(1 for r in D.values() if r['pred'])} "
          f"· pred null {sum(1 for r in D.values() if not r['pred'])}")

# BandCrops 가 실제로 쓰는 항목: COCO images ∩ pred 있는 행
import sys
sys.path.insert(0, ".")
from reader_crnn import BandCrops  # noqa: E402

for name, path in (("ps10b", "band_out/ps10b_det_neg25_crops.jsonl"),
                   ("ps10d", "band_out/ps10d_det640_crops.jsonl")):
    ds = BandCrops("synth_coco/GEN9_READER", boxes=path, jitter=0.0)
    labs = Counter("" if lb == "" else "값" for _, _, lb in ds.items)
    print(f"{name} BandCrops 실제 학습 항목 {len(ds)} (건너뜀 {ds.skipped}) "
          f"· 라벨 {dict(labs)}")

# 공통 file_name + 양쪽 pred 있는 행의 상자 비교
common_both = [f for f in (ka & kb) if A[f]["pred"] and B[f]["pred"]]
ious, cshift, edges, asp = [], [], [], []
clip_a = clip_b = 0
gt = {}
for line in open("synth_coco/GEN9_READER/manifest.jsonl", encoding="utf-8"):
    if line.strip():
        m = json.loads(line)
        if m.get("box"):
            gt[m["id"] + ".png"] = m["box"]
for f in common_both:
    a, b = A[f]["pred"], B[f]["pred"]
    ious.append(iou(a, b))
    cshift.append(np.hypot((a[0] + a[2]) / 2 - (b[0] + b[2]) / 2,
                           (a[1] + a[3]) / 2 - (b[1] + b[3]) / 2))
    edges.append([b[0] - a[0], b[1] - a[1], b[2] - a[2], b[3] - a[3]])
    asp.append((b[2] - b[0]) / (b[3] - b[1]) - (a[2] - a[0]) / (a[3] - a[1]))
    g = gt.get(f)
    if g:
        gx0, gy0, gx1, gy1 = g
        # 숫자 잘림: pred 박스가 GT 밴드를 95% 이상 덮는가
        for box, tag in ((a, "a"), (b, "b")):
            inter = (max(0, min(box[2], gx1) - max(box[0], gx0))
                     * max(0, min(box[3], gy1) - max(box[1], gy0)))
            cover = inter / max(1e-6, (gx1 - gx0) * (gy1 - gy0))
            if cover < 0.95:
                if tag == "a":
                    clip_a += 1
                else:
                    clip_b += 1

ious, cshift = np.array(ious), np.array(cshift)
edges, asp = np.array(edges), np.array(asp)
print(f"\n공통·양측 pred {len(common_both)}행:")
print(f"  IoU p10/중앙/p90: {np.percentile(ious,[10,50,90]).round(3)}")
print(f"  중심이동 px p50/p90: {np.percentile(cshift,[50,90]).round(1)}")
print(f"  변 이동 px (l,t,r,b) p50: {np.percentile(edges,50,axis=0).round(1)}")
print(f"  종횡비차 |Δ| p50/p90: {np.percentile(np.abs(asp),[50,90]).round(3)}")
print(f"  GT밴드 95% 미달(잘림 의심): ps10b {clip_a}건 · ps10d {clip_b}건")

# 라벨이 다른 공통 행 (양성/음성 구성이 어긋난 경우)
lab_diff = [f for f in (ka & kb)
            if (A[f].get("label") or "") != (B[f].get("label") or "")]
print(f"  공통행 중 라벨 상이 {len(lab_diff)}건")
