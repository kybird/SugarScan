# C안 사전 진단 — 가로형 '반쪽 상자' 7장의 왼쪽에 숫자 비슷한 요소가 실재하는가
# (2026-10-09). 규칙: 축을 만들기 전에 커버리지를 잰다
# ([[axis-deepening-needs-coverage-measurement]]).
# 자: 라벨 박스 왼쪽 스트립(폭 0.8×밴드폭, 같은 세로 범위)에서 Otsu 이진화 후
# 연결요소 중 '숫자 비슷한 것'(높이 ≥ 밴드높이 30% · 종횡비 0.2~1.5) 개수와
# 최대 높이 비. 대조군 = 같은 지표로 IoU>0.85 사진 20장.
# 판(박스 안 그림 — 렌더 버그 재발 방지): 스트립 크롭만 ×2.
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
DATUMO = TRAIN.parent / "upstream" / "datumo"
FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 15)

FAIL = ["607", "1593", "606", "956", "1612", "1596", "1044"]

hold = json.loads((HERE / "det_latest_holdout.json").read_text(encoding="utf-8"))
byid = {r["id"]: r for r in hold}
imgs = {}
for ln in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip():
        j = json.loads(ln)
        imgs[j["id"].split("/")[-1]] = j["image"]


def left_features(pid):
    r = byid[pid]
    img = cv2.imread(str(DATUMO / imgs[pid]), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None, None
    gx0, gy0, gx1, gy1 = r["gt"]
    bw = gx1 - gx0
    x0 = max(0, int(gx0 - 0.8 * bw))
    strip = img[int(gy0):int(gy1), x0:int(gx0)]
    if strip.size < 100:
        return None, None
    _, bw_ = cv2.threshold(strip, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink = bw_ == 0
    n_, lab_ = cv2.connectedComponents(ink.astype(np.uint8))
    bh = gy1 - gy0
    cnt, hmax = 0, 0.0
    for i in range(1, n_):
        ys, xs = np.nonzero(lab_ == i)
        h, w = ys.max()-ys.min()+1, xs.max()-xs.min()+1
        if h >= 0.3 * bh and 0.2 <= w / h <= 1.5 and len(xs) >= 20:
            cnt += 1
            hmax = max(hmax, h / bh)
    return cnt, round(hmax, 2)


rng = random.Random(20261009)
ctrl_ids = [r["id"] for r in hold if r["iou"] > 0.85]
ctrl = rng.sample(ctrl_ids, 20)
rows = {"fail": {}, "ctrl": {}}
for pid in FAIL:
    c, hm = left_features(pid)
    rows["fail"][pid] = dict(n=c, hmax=hm, iou=byid[pid]["iou"])
    print(f"[반쪽] #{pid}: 왼쪽 숫자비슷 {c}개 · 최대높이비 {hm}")
ctrl_n = []
for pid in ctrl:
    c, hm = left_features(pid)
    if c is not None:
        rows["ctrl"][pid] = dict(n=c, hmax=hm)
        ctrl_n.append(c)
print(f"[대조 IoU>0.85 {len(ctrl_n)}장] 숫자비슷 개수: 중앙 "
      f"{np.median(ctrl_n):.1f} · p90 {np.percentile(ctrl_n, 90):.1f} · 최대 {max(ctrl_n)}")

# 판 — 스트립 크롭만(박스 그리기 없음)
TILE_W = 560
tiles = []
for pid in FAIL:
    r = byid[pid]
    img = cv2.imread(str(DATUMO / imgs[pid]), cv2.IMREAD_GRAYSCALE)
    gx0, gy0, gx1, gy1 = r["gt"]
    bw = gx1 - gx0
    x0 = max(0, int(gx0 - 0.8 * bw))
    strip = img[int(gy0):int(gy1), x0:int(gx1)]      # 왼쪽 스트립 + 밴드
    h = int(strip.shape[0] * TILE_W / strip.shape[1])
    tile = cv2.resize(strip, (TILE_W, min(h, 220)))
    f = rows["fail"][pid]
    cap = f"#{pid} IoU {r['iou']:.2f} · 왼쪽 숫자비슷 {f['n']}개 (최대높이비 {f['hmax']})"
    tiles.append((tile, cap))
W = 2 * (TILE_W + 8) + 8
rows_n = (len(tiles) + 1) // 2
sheet = Image.new("RGB", (W, rows_n * 250 + 30), (16, 16, 16))
d = ImageDraw.Draw(sheet)
d.text((10, 6), "반쪽상자 7장 — 라벨 왼쪽 스트립+밴드(선 없음, 실물 그대로)",
       font=FONT, fill=(250, 240, 210))
for i, (t, cap) in enumerate(tiles):
    cx = 6 + (i % 2) * (TILE_W + 8)
    cy = 30 + (i // 2) * 250
    sheet.paste(Image.fromarray(t).convert("RGB"), (cx, cy))
    d.text((cx + 2, cy + t.shape[0] + 4), cap, font=FONT, fill=(255, 220, 130))
sheet.save(HERE / "horizontal_left_diag.png")
out = HERE / "horizontal_left_diag.json"
out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("판:", HERE / "horizontal_left_diag.png", "· 기록:", out)
