# 1707 쿼드 부검 — 마스크·다각화 쿼드·워프 결과 시각화
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import webtool as wt

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
OUT = HERE / "rect_test"

cid = "glucose_batch1/1707"
row = None
for l in (HERE / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
    if l.strip() and json.loads(l)["id"] == cid:
        row = json.loads(l)
if row is None:
    raise SystemExit(f"{cid}: gmscreen 예측 없음")
q = np.array(row["quad"], np.float64)
x0, y0 = float(q[:, 0].min()), float(q[:, 1].min())
x1, y1 = float(q[:, 0].max()), float(q[:, 1].max())

with Image.open(DATUMO / f"{cid}.jpg") as pil:
    pil.load()
    g = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
H, W = g.shape
print(f"img {W}x{H}  box ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})  "
      f"w={x1-x0:.0f} h={y1-y0:.0f}")

# --- _find_glass_quad 내부 재현 (작업스케일 시각화) ---
bx0, by0, bx1, by1 = int(x0), int(y0), int(x1), int(y1)
mx = int((bx1 - bx0) * 0.06) + 2
my = int((by1 - by0) * 0.06) + 2
cx0, cy0 = max(0, bx0 - mx), max(0, by0 - my)
cx1, cy1 = min(W, bx1 + mx), min(H, by1 + my)
crop = g[cy0:cy1, cx0:cx1]
scale = 800.0 / max(crop.shape)
es = min(1.0, scale)
cs = (cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
      if scale < 1.0 else crop)
blur = cv2.GaussianBlur(cs, (5, 5), 0)
_, mpos = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
area_s = float(cs.shape[0] * cs.shape[1])
ch, cw = cs.shape
best, best_score = None, 0.0
for m in (mpos, cv2.bitwise_not(mpos)):
    m2 = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m2, 8)
    for k in range(1, n):
        x, y, w, h, a = stats[k]
        if a < area_s * 0.15 or a > area_s * 0.98:
            continue
        ccx, ccy = x + w / 2.0, y + h / 2.0
        if not (cw * 0.15 < ccx < cw * 0.85 and ch * 0.15 < ccy < ch * 0.85):
            continue
        fill = a / float(w * h)
        if fill < 0.55:
            continue
        if a * fill > best_score:
            best_score = a * fill
            best = (lab == k).astype(np.uint8)
print(f"선택 마스크: {'있음' if best is not None else '없음'}")
cnts, _ = cv2.findContours(best, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
c = max(cnts, key=cv2.contourArea)
box_area = float((bx1 - bx0) * (by1 - by0)) * es * es
vis = cv2.cvtColor(cs, cv2.COLOR_GRAY2BGR)
cv2.drawContours(vis, [c], -1, (0, 255, 0), 2)
quad = None
for eps in (0.02, 0.035, 0.05, 0.07):
    ap = cv2.approxPolyDP(c, eps * cv2.arcLength(c, True), True)
    print(f"eps {eps}: 꼭짓점 {len(ap)} 볼록={cv2.isContourConvex(ap) if len(ap) >= 4 else '-'} "
          f"면적비={cv2.contourArea(ap) / box_area:.2f}")
    if len(ap) == 4 and quad is None and cv2.isContourConvex(ap):
        qa = float(cv2.contourArea(ap))
        if box_area * 0.35 <= qa <= box_area * 1.5:
            quad = ap.reshape(4, 2).astype(np.float32)
for p in quad:
    cv2.circle(vis, (int(p[0]), int(p[1])), 6, (0, 0, 255), -1)
qo = wt._order_quad(quad)
print("정렬 쿼드(TL,TR,BR,BL):")
for name, p in zip(("TL", "TR", "BR", "BL"), qo):
    print(f"  {name}: ({p[0]:.0f},{p[1]:.0f})")
cv2.imwrite(str(OUT / "debug_1707_mask.png"), vis)

unw = wt._warp_quad(g, wt._order_quad(quad / es * 0 + quad) if False else
                    wt._order_quad((quad / es) + np.array([cx0, cy0], np.float32)))
cv2.imwrite(str(OUT / "debug_1707_unw.png"), unw)
# 원본 박스 크롭(무왜곡 참고용)
crop_full = g[max(0, by0):by1, max(0, bx0):bx1]
sc = 500.0 / max(crop_full.shape)
cv2.imwrite(str(OUT / "debug_1707_srccrop.png"),
            cv2.resize(crop_full, None, fx=sc, fy=sc))
print("저장: debug_1707_mask.png / debug_1707_unw.png / debug_1707_srccrop.png")
