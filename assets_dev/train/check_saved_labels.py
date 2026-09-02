# 저장된 라벨을 표시(EXIF 적용) 이미지에 그려 정합성 확인 — 1001/1005
from pathlib import Path

import cv2
import json
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
OUT = HERE / "rect_test"

for cid in ("glucose_batch1/1001", "glucose_batch1/1005"):
    row = None
    for l in (HERE / "screen_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip() and json.loads(l)["id"] == cid:
            row = json.loads(l)
    q = np.array(row["quad"], np.float32)
    with Image.open(DATUMO / f"{cid}.jpg") as pil:
        pil = ImageOps.exif_transpose(pil)
    im = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2BGR)
    H, W = im.shape[:2]
    print(f"{cid}: 표시 {W}x{H}  쿼드 x {q[:, 0].min():.0f}~{q[:, 0].max():.0f}  "
          f"y {q[:, 1].min():.0f}~{q[:, 1].max():.0f}")
    cv2.polylines(im, [q.astype(np.int32)], True, (0, 255, 130), 14)
    sc = 420.0 / H
    cv2.imwrite(str(OUT / f"label_check_{cid.split('/')[1]}.jpg"),
                cv2.resize(im, (int(W * sc), int(H * sc))))
    print(f"  → rect_test/label_check_{cid.split('/')[1]}.jpg")
