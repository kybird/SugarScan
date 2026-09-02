# production 밴드 크롭에 최종 세그먼트 박스를 그려 눈검증용으로 저장.
import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Project\sugarScan\assets_dev\train")
import cv2
import numpy as np
from PIL import Image

from eval_glyph import segment_glyphs

CROPS = Path(r"D:\Project\sugarScan\assets_dev\train\crops")
OUT = Path(r"D:\Project\sugarScan\assets_dev\upstream\datumo\previews")
gt = {}
for l in (Path(r"D:\Project\sugarScan\assets_dev\upstream\datumo") / "labels.jsonl").read_text(encoding="utf-8").splitlines():
    if l.strip():
        j = json.loads(l)
        gt[j["id"].replace("/", "__")] = j["reading"]

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 12
for p in sorted(CROPS.glob("*.png"))[:limit]:
    band = cv2.cvtColor(
        np.asarray(Image.open(p).convert("RGB")), cv2.COLOR_RGB2GRAY)
    boxes = segment_glyphs(band)
    vis = cv2.cvtColor(band, cv2.COLOR_GRAY2BGR)
    for (x, y, w, h) in boxes:
        cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 0, 255), 2)
    cv2.putText(vis, f"GT:{gt.get(p.stem)} seg:{len(boxes)}",
                (4, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cv2.imwrite(str(OUT / f"segvis__{p.stem}.png"), vis)
    print(p.stem[:30], "GT:", gt.get(p.stem), "seg:", len(boxes),
          [(b[2], b[3]) for b in boxes])
