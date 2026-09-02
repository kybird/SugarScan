# 쿼드 좌표계 변환 검증 — 1005(ori=6): 변환 쿼드를 표시 이미지에 그려 확인
from pathlib import Path

import cv2
import json
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
OUT = HERE / "rect_test"

cid = "glucose_batch1/10"
row = None
for l in (HERE / "gmscreen_quads_oriented.jsonl").read_text(
        encoding="utf-8").splitlines():
    if l.strip() and json.loads(l)["id"] == cid:
        row = json.loads(l)
q = np.array(row["quad"], np.float32)

with Image.open(DATUMO / f"{cid}.jpg") as pil:
    pil = ImageOps.exif_transpose(pil)
im = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2BGR)
H, W = im.shape[:2]
print(f"표시 이미지 {W}x{H}  쿼드 x범위 {q[:, 0].min():.0f}~{q[:, 0].max():.0f}  "
      f"y범위 {q[:, 1].min():.0f}~{q[:, 1].max():.0f}")
cv2.polylines(im, [q.astype(np.int32)], True, (0, 255, 130), 12)
sc = 480.0 / H
cv2.imwrite(str(OUT / "verify_oriented_1005.jpg"),
            cv2.resize(im, (int(W * sc), int(H * sc))))
print("저장: rect_test/verify_oriented_1005.jpg")
