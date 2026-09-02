# 사용자 LCD 라벨 전수 점검 — 빠른판(JPEG draft 1/8 디코드) + 자동 플래그. 시각화 전용.
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()

rows = [json.loads(l) for l in
        (HERE / "screen_boxes.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()]

pred = {}
for l in (HERE / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
    try:
        d = json.loads(l)
        pred[d["id"]] = np.array(d["quad"], np.float32)
    except Exception:
        pass

flags = {}
cells = []
CW, CH, COLS = 320, 240, 6
for i, d in enumerate(rows):
    cid = d["id"]
    q = np.array(d["quad"], np.float32)
    x0, y0 = float(q[:, 0].min()), float(q[:, 1].min())
    x1, y1 = float(q[:, 0].max()), float(q[:, 1].max())
    w, h = x1 - x0, y1 - y0
    ar = w / max(h, 1.0)

    img = Image.open(DATUMO / f"{cid}.jpg")
    W0, H0 = img.size
    img.draft("RGB", (W0 // 8, H0 // 8))
    arr = np.asarray(img.convert("RGB"))
    H, W = arr.shape[:2]
    s = W0 / W  # 원본→디코드 스케일

    af = (w * h) / (W0 * H0)
    fx = []
    if not (0.2 <= ar <= 4.5):
        fx.append(f"aspect{ar:.1f}")
    if af < 0.0008 or af > 0.35:
        fx.append(f"area{af:.3f}")
    if x0 <= 1 or y0 <= 1 or x1 >= W0 - 2 or y1 >= H0 - 2:
        fx.append("edge")
    if cid in pred:
        p = pred[cid]
        px0, py0 = float(p[:, 0].min()), float(p[:, 1].min())
        px1, py1 = float(p[:, 0].max()), float(p[:, 1].max())
        ix0, iy0 = max(x0, px0), max(y0, py0)
        ix1, iy1 = min(x1, px1), min(y1, py1)
        inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
        union = w * h + (px1 - px0) * (py1 - py0) - inter
        iou = inter / max(union, 1.0)
        if iou < 0.5:
            fx.append(f"iou{iou:.2f}")
    if fx:
        flags[cid] = fx

    dx, dy = (w / s) * 0.5, (h / s) * 0.5
    bx0, by0, bx1, by1 = x0 / s, y0 / s, x1 / s, y1 / s
    cx0, cy0 = max(0, int(bx0 - dx)), max(0, int(by0 - dy))
    cx1, cy1 = min(W, int(bx1 + dx)), min(H, int(by1 + dy))
    crop = cv2.cvtColor(arr[cy0:cy1, cx0:cx1], cv2.COLOR_RGB2BGR).copy()
    bw = max(2, int(min(crop.shape[:2]) / 140))
    cv2.rectangle(crop, (int(bx0 - cx0), int(by0 - cy0)),
                  (int(bx1 - cx0), int(by1 - cy0)), (0, 0, 255), bw)
    cv2.putText(crop, str(i), (8, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.3,
                (0, 255, 255), 3)
    if fx:
        cv2.putText(crop, "FLAG", (8, 84), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                    (0, 0, 255), 3)
    cells.append(cv2.resize(crop, (CW, CH)))

nr = (len(cells) + COLS - 1) // COLS
board = np.full((nr * CH, COLS * CW, 3), 30, np.uint8)
for i, c in enumerate(cells):
    r0, c0 = (i // COLS) * CH, (i % COLS) * CW
    board[r0:r0 + CH, c0:c0 + CW] = c
cv2.imwrite(str(HERE / "sheet_user_all_labels.png"), board)
print(f"labels={len(rows)}  flagged={len(flags)}  → sheet_user_all_labels.png")
for cid, fx in flags.items():
    print(f"  {cid}: {', '.join(fx)}")
