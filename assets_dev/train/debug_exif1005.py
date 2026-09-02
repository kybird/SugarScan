# 1005 — PIL raw vs cv2(EXIF 적용) 나란히 저장: 어느 쪽이 올바른 표시인지 확정
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
OUT = HERE / "rect_test"

cid = "glucose_batch1/1005"
p = DATUMO / f"{cid}.jpg"

pil_raw = np.asarray(Image.open(p).convert("RGB"))
cv2_img = cv2.imread(str(p))  # cv2는 EXIF를 적용한다(실측)

h = 500


def fit(im):
    s = h / im.shape[0]
    return cv2.resize(im, (int(im.shape[1] * s), h), interpolation=cv2.INTER_AREA)


cv2.imwrite(str(OUT / "exif_1005_pilraw.png"), fit(pil_raw[..., ::-1]))
cv2.imwrite(str(OUT / "exif_1005_cv2.png"), fit(cv2_img))
print("저장: exif_1005_pilraw.png / exif_1005_cv2.png")
