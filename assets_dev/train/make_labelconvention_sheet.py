# 라벨 관례 확인 시트 — ① Roboflow GM_SCREEN 박스 관례 ② 사용자 LCD 라벨 7장 스타일
# 시각화 전용. 학습·추론 없음.
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
GM = HERE / "gmscreen"
DATUMO = HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE"
OUT1 = HERE / "sheet_roboflow_gmscreen.png"
OUT2 = HERE / "sheet_user_lcd7.png"


def crop_with_box(img, box, pad_ratio=0.55, cw=420, ch=300):
    """box=(x,y,w,h) 주변을 여유 포함 크롭하고 박스를 그린 뒤 셀 크기로 리사이즈."""
    x, y, w, h = box
    px, py = int(w * pad_ratio), int(h * pad_ratio)
    x0, y0 = max(0, x - px), max(0, y - py)
    x1, y1 = min(img.shape[1], x + w + px), min(img.shape[0], y + h + py)
    crop = img[y0:y1, x0:x1].copy()
    cv2.rectangle(crop, (x - x0, y - y0), (x - x0 + w, y - y0 + h), (0, 0, 255), 3)
    return cv2.resize(crop, (cw, ch))


def sheet(cells, out, cols=4):
    rows = (len(cells) + cols - 1) // cols
    cw, ch = cells[0].shape[1], cells[0].shape[0]
    board = np.full((rows * ch, cols * cw, 3), 30, dtype=np.uint8)
    for i, c in enumerate(cells):
        board[(i // cols) * ch:(i // cols) * ch + ch,
              (i % cols) * cw:(i % cols) * cw + cw] = c
    cv2.imwrite(str(out), board)
    print(f"{out.name}: {len(cells)}셀")


# ① Roboflow GM_SCREEN 관례 (val + train 에서 표본)
cells = []
for split in ("val2017", "train2017"):
    ann = json.loads(
        (GM / "annotations" / f"instances_{split}.json")
        .read_text(encoding="utf-8"))
    imgs = {im["id"]: im for im in ann["images"]}
    by_img = {}
    for a in ann["annotations"]:
        by_img.setdefault(a["image_id"], []).append(a["bbox"])
    step = max(1, len(by_img) // 4)
    for k, (iid, boxes) in enumerate(sorted(by_img.items())):
        if k % step:
            continue
        p = GM / split / imgs[iid]["file_name"]
        if not p.exists():
            continue
        img = cv2.cvtColor(np.asarray(Image.open(p).convert("RGB")),
                           cv2.COLOR_RGB2BGR)
        for b in boxes[:1]:
            cells.append(crop_with_box(img, tuple(int(v) for v in b)))
        if len(cells) >= 8:
            break
    if len(cells) >= 8:
        break
sheet(cells, OUT1)

# ② 사용자 screen_boxes.jsonl (quad → 축정렬 bbox로 표시 — 실제 소비 방식과 동일)
user_rows = [json.loads(ln) for ln in
             (HERE / "screen_boxes.jsonl").read_text(encoding="utf-8").splitlines()
             if ln.strip()]
step = max(1, len(user_rows) // 8)
cells2 = []
for d in user_rows[::step][:8]:
    q = np.array(d["quad"], dtype=np.float32)
    x0, y0 = int(q[:, 0].min()), int(q[:, 1].min())
    x1, y1 = int(q[:, 0].max()), int(q[:, 1].max())
    p = DATUMO / f"{d['id']}.jpg"
    img = cv2.cvtColor(np.asarray(Image.open(p).convert("RGB")), cv2.COLOR_RGB2BGR)
    cells2.append(crop_with_box(img, (x0, y0, x1 - x0, y1 - y0)))
sheet(cells2, OUT2, cols=4)
