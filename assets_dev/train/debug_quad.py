# 유리 쿼드 검출 부검 — 중간 산출 시각화 (1001)
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
OUT = HERE / "rect_test"

cid = "glucose_batch1/1001"
lcd = json.loads((HERE / "screen_boxes.jsonl").read_text(encoding="utf-8")
                 .splitlines()[0])
q = np.array(lcd["quad"], np.float64)
x0, y0 = float(q[:, 0].min()), float(q[:, 1].min())
x1, y1 = float(q[:, 0].max()), float(q[:, 1].max())

with Image.open(DATUMO / f"{cid}.jpg") as pil:
    pil.load()
    g = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
H, W = g.shape
print(f"img {W}x{H}  box ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})")
bx0, by0, bx1, by1 = int(x0), int(y0), int(x1), int(y1)

mx = int((bx1 - bx0) * 0.06) + 2
my = int((by1 - by0) * 0.06) + 2
cx0, cy0 = max(0, bx0 - mx), max(0, by0 - my)
cx1, cy1 = min(W, bx1 + mx), min(H, by1 + my)
crop = g[cy0:cy1, cx0:cx1]
print(f"crop {crop.shape[1]}x{crop.shape[0]}")
scale = 800.0 / max(crop.shape)
cs = (cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
      if scale < 1.0 else crop)
blur = cv2.GaussianBlur(cs, (5, 5), 0)
t, mpos = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
print(f"otsu threshold = {t:.1f}  (밝기 분포: p5={np.percentile(cs,5):.0f} "
      f"p50={np.percentile(cs,50):.0f} p95={np.percentile(cs,95):.0f})")
area_s = float(cs.shape[0] * cs.shape[1])
ch, cw = cs.shape
vis = cv2.cvtColor(cs, cv2.COLOR_GRAY2BGR)
for name, m in (("pos", mpos), ("neg", cv2.bitwise_not(mpos))):
    m2 = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m2, 8)
    print(f"--- 극성 {name}: CC {n - 1}개 ---")
    order = np.argsort(-stats[1:, 4])[:5] + 1
    for k in order:
        x, y, w, h, a = stats[k]
        ccx, ccy = x + w / 2, y + h / 2
        fill = a / float(w * h)
        central = (cw * 0.15 < ccx < cw * 0.85 and ch * 0.15 < ccy < ch * 0.85)
        ok = (area_s * 0.15 <= a <= area_s * 0.98) and central and fill >= 0.55
        print(f"  CC{k}: area {a / area_s * 100:.1f}%  bbox {w}x{h}  "
              f"fill {fill:.2f}  center ({ccx / cw:.2f},{ccy / ch:.2f})  "
              f"필터통과={ok}")
        if ok:
            color = (0, 0, 255)
        else:
            color = (0, 255, 0)
        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 3)
cv2.imwrite(str(OUT / "debug_quad_1001.png"), vis)
print("저장: rect_test/debug_quad_1001.png (빨강=통과, 초록=기각)")

# ---- 4점 다각화 부검: 통과한 CC6의 외곽 윤곽에서 eps별 결과 ----
m2 = cv2.morphologyEx(cv2.bitwise_not(mpos), cv2.MORPH_CLOSE,
                      np.ones((7, 7), np.uint8))
cnts, _ = cv2.findContours(m2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
c = max(cnts, key=cv2.contourArea)
box_area_ws = float((bx1 - bx0) * (by1 - by0)) * scale * scale
print(f"윤곽 면적(작업스케일) {cv2.contourArea(c):.0f} vs 박스면적 {box_area_ws:.0f}")
for eps in (0.02, 0.035, 0.05, 0.07, 0.10):
    ap = cv2.approxPolyDP(c, eps * cv2.arcLength(c, True), True)
    conv = cv2.isContourConvex(ap) if len(ap) >= 4 else False
    qa = float(cv2.contourArea(ap)) if len(ap) >= 3 else 0.0
    print(f"  eps {eps:.3f}: 꼭짓점 {len(ap)}  볼록={conv}  "
          f"면적비={qa / box_area_ws:.2f}")
