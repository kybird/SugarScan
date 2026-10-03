# 걸침 의심 큐 상위 장의 판정 판을 굽는다 — 내 라벨이 틀렸는지 가린다.
#
# 질문(2026-09-27): "그러면 내 라벨링이 틀린 게 뭐야?" — 세운 기준
# (숫자줄만 · 단위 절반 이상 보이면 조임 · 기울임 걸침은 허용)으로
# 어떤 장이 실제 틀렸는지 사람이 화면에서 판정할 판을 낸다.
#
# 각 타일: 빨강 = 사람 라벨, 초록 = atone_s0 예측. 크롭은 라벨·예측
# 하단에서 충분히 아래까지 내려 단위 줄 전체가 보이게 한다(단위가
# 라벨 안에 얼마나 걸쳤는지가 판정 대상이므로).
#
# 사용:
#   python make_unit_clip_sheet.py                 # 상위 24장
#   python make_unit_clip_sheet.py --top 48 --min-depth 1.0
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=24)
    ap.add_argument("--min-depth", type=float, default=0.0)
    ap.add_argument("--ids", default=None,
                    help="쉼표 id 목록 — 큐 순서 대신 이 장들만 판에 굽는다")
    ap.add_argument("--out", default=str(HERE / "_diag" / "band_real" / "unit_clip_sheet.png"))
    a = ap.parse_args()

    queue = json.loads((HERE / "band_unit_clip_queue.json").read_text(encoding="utf-8"))
    if a.ids:
        want = [x.strip() for x in a.ids.split(",") if x.strip()]
        queue = [{"id": w, "note": "지정 · depth 미가림"} for w in want]
    else:
        queue = [r for r in queue if r["note"] and float(r["note"].split()[-1]) >= a.min_depth]
        queue = queue[:a.top]

    lab, pred = {}, {}
    for line in (HERE / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            if j.get("quad"):
                lab[j["id"]] = j["quad"]
    for line in (HERE / "band_quads_pred.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            if j.get("quad"):
                pred[j["id"]] = j["quad"]

    imgs = {}
    for line in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            imgs[j["id"]] = j["image"]

    tiles = []
    for r in queue:
        cid = r["id"]
        if cid not in lab or cid not in pred or cid not in imgs:
            continue
        img = cv2.imread(str(DATUMO / imgs[cid]), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        # quad 4점 → AABB (flatten 인덱스는 점 순서에 묶이지 않게 min/max 로)
        lxs = [pt[0] for pt in lab[cid]]; lys = [pt[1] for pt in lab[cid]]
        pxs = [pt[0] for pt in pred[cid]]; pys = [pt[1] for pt in pred[cid]]
        l = (min(lxs), min(lys), max(lxs), max(lys))
        p = (min(pxs), min(pys), max(pxs), max(pys))
        y_lo = int(max(l[3], p[3]) + (l[3] - l[1]) * 0.45)  # 단위 줄 전체가 보이게
        x0 = int(max(0, min(l[0], p[0]) - 40))
        y0 = int(max(0, min(l[1], p[1]) - 40))
        x1 = int(min(img.shape[1], max(l[2], p[2]) + 40))
        y1 = int(min(img.shape[0], y_lo))
        if x1 - x0 < 60 or y1 - y0 < 60:
            continue
        crop = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
        for box, col, th in ((lab[cid], (0, 0, 255), 6), (pred[cid], (0, 255, 0), 4)):
            bx = [box[0][0]-x0, box[0][1]-y0, box[2][0]-x0, box[2][1]-y0]
            cv2.rectangle(crop, (int(bx[0]), int(bx[1])), (int(bx[2]), int(bx[3])), col, th)
        depth = r["note"].split()[-1]
        cv2.putText(crop, depth, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 7)
        cv2.putText(crop, depth, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
        h = 260
        w = int(crop.shape[1] * h / crop.shape[0])
        tiles.append((cid, cv2.resize(crop, (w, h))))

    if not tiles:
        raise SystemExit("타일이 없다")
    W = min(t[1].shape[1] for t in tiles)
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    canvas = np.full((260 * rows + 16 * (rows - 1), W * cols + 16, 3), 40, np.uint8)
    for i, (cid, t) in enumerate(tiles):
        y = (i // cols) * 276
        x = (i % cols) * (W + 16)
        canvas[y:y+260, x:x+W] = t[:260, :W]
        cv2.putText(canvas, cid.split("/")[-1], (x + 6, y + 254),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (210, 210, 210), 2)
    cv2.imwrite(a.out, canvas)
    print(f"{a.out} · {len(tiles)}타일 (depth {queue[0]['note'].split()[-1]}"
          f" ~ {queue[-1]['note'].split()[-1]})")


if __name__ == "__main__":
    main()
