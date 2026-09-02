# 1707 재현 — 개선된 _find_glass_quad로 추정 박스 기반 검수 (실제 함수 경로)
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import webtool as wt

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
OUT = HERE / "rect_test"

cid = "glucose_batch1/1707"
with Image.open(DATUMO / f"{cid}.jpg") as pil:
    pil.load()
    g = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
H, W = g.shape
# 원본 보고 추정한 유리 영역 박스(사용자가 그렸을과 유사한 수준)
box = (int(W * 0.18), int(H * 0.15), int(W * 0.86), int(H * 0.88))
quad = wt._find_glass_quad(g, box)
print("쿼드:", None if quad is None else
      [[round(float(p[0])), round(float(p[1]))] for p in quad])
if quad is None:
    raise SystemExit("쿼드 실패")
unw = wt._warp_quad(g, quad, max_side=640)
unw2, k = wt._auto_upright(unw)
cv2.imwrite(str(OUT / "debug_1707_new_unw.png"), unw)
cv2.imwrite(str(OUT / "debug_1707_new_upright.png"), unw2)
print(f"auto upright: {k}°  → debug_1707_new_unw/upright.png")
