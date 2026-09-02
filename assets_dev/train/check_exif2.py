# cv2 EXIF 적용 여부 실측 — 기존 캐시 크기로 판정 (좌표계 이관 여부 결정 근거)
import json
from pathlib import Path

import cv2
from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()

cid = "glucose_batch1/1005"  # EXIF orientation=6 (4128x3096 저장)
p = DATUMO / f"{cid}.jpg"
img = cv2.imread(str(p))
print("cv2.imread (h,w):", img.shape, "→", "EXIF 적용됨(세로)" if
      img.shape[0] > img.shape[1] else "EXIF 미적용(가로)")

cache = HERE / "cache" / "glucose_batch1__1005_1600.jpg"
if cache.exists():
    with Image.open(cache) as im:
        print("기존 캐시 크기:", im.size, "→", "세로(적용)" if
              im.size[1] > im.size[0] else "가로(미적용)")
else:
    print("기존 캐시 없음")

with Image.open(p) as im:
    print("PIL raw:", im.size)

# 전체 2,512장 orientation 분포 (헤더만 읽음)
DAT = DATUMO
dist = {}
for l in (HERE / ".." / "upstream" / "datumo" / "labels.jsonl").read_text(
        encoding="utf-8").splitlines():
    if not l.strip():
        continue
    cid = json.loads(l)["id"]
    with Image.open(DAT / f"{cid}.jpg") as im:
        ori = im.getexif().get(274, 1)
    dist[ori] = dist.get(ori, 0) + 1
print("전체 2,512장 EXIF orientation 분포:", dist)
