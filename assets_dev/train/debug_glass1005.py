# 1005 유리 쿼드 부검 — 글로시 블랙 바디에서 어디에 쿼드가 붙는가
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
OUT = HERE / "rect_test"


def wt_order(q):
    ctr = q.mean(axis=0)
    ang = np.arctan2(q[:, 1] - ctr[1], q[:, 0] - ctr[0])
    q = q[np.argsort(-ang)]
    s = q[:, 0] + q[:, 1]
    q = np.roll(q, -int(np.argmin(s)), axis=0)
    if q[1, 1] > q[3, 1]:
        q = q[[0, 3, 2, 1]]
    return q

cid = "glucose_batch1/1005"
with Image.open(DATUMO / f"{cid}.jpg") as pil:
    pil = ImageOps.exif_transpose(pil)
g = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
H, W = g.shape
box = (950, 600, 2550, 2900)  # 사용자 박스 추정(유리+여유)
x0, y0, x1, y1 = box
mx, my = int((x1 - x0) * 0.06) + 2, int((y1 - y0) * 0.06) + 2
cx0, cy0 = max(0, x0 - mx), max(0, y0 - my)
cx1, cy1 = min(W, x1 + mx), min(H, y1 + my)
crop = g[cy0:cy1, cx0:cx1]
scale = 800.0 / max(crop.shape)
es = min(1.0, scale)
cs = (cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
      if scale < 1.0 else crop)
blur = cv2.GaussianBlur(cs, (5, 5), 0)
_, mpos = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
area_s = float(cs.shape[0] * cs.shape[1])
ch, cw = cs.shape
vis = cv2.cvtColor(cs, cv2.COLOR_GRAY2BGR)
print(f"크롭 {cw}x{ch}  오츠 밝기 평균 mpos.mean={mpos.mean():.0f}")
best, best_score, best_desc = None, 0.0, ""
for ksz in (9, 17, 29):
    for pname, m in (("dark", mpos), ("bright", cv2.bitwise_not(mpos))):
        m2 = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((ksz, ksz), np.uint8))
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
            score = a * fill
            if score > best_score:
                best_score = score
                best = (lab == k).astype(np.uint8)
                best_desc = (f"{pname} k{ksz} area {a / area_s * 100:.0f}% "
                             f"fill {fill:.2f}")
                vis2 = vis.copy()
                cv2.rectangle(vis2, (x, y), (x + w, y + h), (0, 255, 0), 3)
if best is None:
    print("통과 성분 없음")
    raise SystemExit(1)
print(f"선정: {best_desc}")
cnts, _ = cv2.findContours(best, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
c = max(cnts, key=cv2.contourArea)
box_area = float((x1 - x0) * (y1 - y0)) * es * es
quad = None
for eps in (0.02, 0.035, 0.05, 0.07):
    ap = cv2.approxPolyDP(c, eps * cv2.arcLength(c, True), True)
    if len(ap) == 4 and cv2.isContourConvex(ap):
        qa = float(cv2.contourArea(ap))
        if box_area * 0.35 <= qa <= box_area * 1.5:
            quad = ap.reshape(4, 2).astype(np.float32)
            break
cv2.drawContours(vis, [c], -1, (255, 0, 0), 2)
if quad is not None:
    rq = wt_order(quad)
    for p in quad:
        cv2.circle(vis, (int(p[0]), int(p[1])), 8, (0, 0, 255), -1)
    for p in rq:
        cv2.circle(vis, (int(p[0]), int(p[1])), 5, (0, 255, 255), -1)
cv2.imwrite(str(OUT / "debug_glass1005.png"), vis)
print("저장: rect_test/debug_glass1005.png (초록=선정성분 bbox, 파랑=윤곽, 빨강=approx 모서리, 노랑=정렬 후)")
