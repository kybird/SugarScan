# 회전된 라벨 장 찾기 — draft 디코드로 전 라벨 스캔, upright_k 기록
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import webtool as wt

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()

rows = [json.loads(l) for l in
        (HERE / "screen_boxes.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()]
print(f"라벨 {len(rows)}장 스캔…")

ks = {}
for i, d in enumerate(rows):
    cid = d["id"]
    q = np.array(d["quad"], np.float64)
    x0, y0 = float(q[:, 0].min()), float(q[:, 1].min())
    x1, y1 = float(q[:, 0].max()), float(q[:, 1].max())
    img = Image.open(DATUMO / f"{cid}.jpg")
    W0, H0 = img.size
    img.draft("RGB", (W0 // 8, H0 // 8))
    g = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    s = W0 / g.shape[1]
    box = (int(x0 / s), int(y0 / s), int(x1 / s), int(y1 / s))
    quad = wt._find_glass_quad(g, box)
    if quad is None:
        ks[cid] = ("QUADFAIL", 0)
        continue
    unw = wt._warp_quad(g, quad, max_side=320)
    _, k = wt._auto_upright(unw)
    ks[cid] = ("OK", k)

rot = [(c, k) for c, (st, k) in ks.items() if st == "OK" and k != 0]
fail = [c for c, (st, k) in ks.items() if st == "QUADFAIL"]
print(f"\n쿼드 실패: {len(fail)}장")
if fail:
    print("  " + ", ".join(fail[:12]))
print(f"회전(세우기 적용, k≠0): {len(rot)}장")
for c, k in rot[:15]:
    print(f"  {c}: {k}°")
