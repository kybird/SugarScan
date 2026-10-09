# 최신 검출기(gen2_v1_step8000) 홀드아웃 실패 기록(2026-10-07 사람:
# "우리 최신 검출기 실패 기록 보여줘"). 사람 밴드 상자 라벨(band_boxes.jsonl)
# 전체에서 배포 경로 그대로(top-1+점수, 게이트 0.25/0.02) 예측을 내고
# IoU·사람상자 커버(포함)를 잰다. 최악 12장 판(주황=예측, 초록=사람).
# 참고: 이 자의 직전 기록 atone_tg640w15 = IoU 중앙 0.8911(346장, 10-03).
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from band_net import BandNet, decode  # noqa: E402
from train_band import letterbox  # noqa: E402

DATUMO = HERE.parent.parent / "upstream" / "datumo"
FONT_S = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 15)

excl = set()
for ln in (HERE.parent / "band_label_excluded.jsonl").read_text(
        encoding="utf-8").splitlines():
    if ln.strip():
        excl.add(json.loads(ln)["id"].split("/")[-1])

human = []
for ln in (HERE.parent / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip():
        r = json.loads(ln)
        if r["id"].split("/")[-1] not in excl:
            human.append(r)
imgs = {}
for ln in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip():
        j = json.loads(ln)
        imgs[j["id"].split("/")[-1]] = j["image"]

dev = "cuda" if torch.cuda.is_available() else "cpu"
cd = torch.load(HERE.parent / "band_out" / "tone" / "gen2_v1_step8000",
                map_location="cpu", weights_only=False)
det = BandNet(width=cd["width"], stride=cd.get("stride", 16)).to(dev).eval()
det.load_state_dict(cd["model"])

rows = []
with torch.no_grad():
    for h in human:
        pid = h["id"].split("/")[-1]
        img = cv2.imread(str(DATUMO / imgs[pid]), cv2.IMREAD_GRAYSCALE)
        lb, r, dx, dy = letterbox(img, cd["size"])
        x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
        obj, reg = det(x.to(dev))
        b, s = decode(obj.float(), reg.float(), det.stride)
        b = b[0].cpu().numpy()
        sc = float(s[0].cpu())
        p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
        frac = ((p[2]-p[0])*(p[3]-p[1])) / max(1., img.shape[1]*img.shape[0])
        q = h["quad"]
        gx0, gy0 = min(t[0] for t in q), min(t[1] for t in q)
        gx1, gy1 = max(t[0] for t in q), max(t[1] for t in q)
        ix0, iy0 = max(p[0], gx0), max(p[1], gy0)
        ix1, iy1 = min(p[2], gx1), min(p[3], gy1)
        inter = max(0., ix1-ix0) * max(0., iy1-iy0)
        union = (p[2]-p[0])*(p[3]-p[1]) + (gx1-gx0)*(gy1-gy0) - inter
        cover = inter / max(1., (gx1-gx0)*(gy1-gy0))
        rows.append(dict(id=pid, sc=round(sc, 3), frac=round(frac, 4),
                         iou=round(inter/max(1., union), 3),
                         cover=round(cover, 3),
                         gated=bool(sc >= 0.25 and frac >= 0.02),
                         pred=[round(v, 1) for v in p],
                         gt=[gx0, gy0, gx1, gy1]))

ious = np.array([r["iou"] for r in rows])
n_gfail = sum(1 for r in rows if not r["gated"])
print(f"n={len(rows)} (제외 {len(excl)}) · IoU 중앙 {np.median(ious):.4f} "
      f"· p10 {np.percentile(ious,10):.3f} · 최저 {ious.min():.3f}")
print(f"게이트 미달 {n_gfail}장 · IoU<0.5 {int((ious<0.5).sum())}장 · "
      f"<0.7 {int((ious<0.7).sum())}장 · 커버<0.9 {sum(1 for r in rows if r['cover']<0.9)}장")
rows.sort(key=lambda r: r["iou"])
out_j = HERE / "det_latest_holdout.json"
out_j.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print("전체 기록:", out_j)

# 최악 12장 판
TILE_W, TH, CAP, HDR, COLS = 620, 460, 40, 34, 3
worst = rows[:12]
tiles = []
for r in worst:
    pid = r["id"]
    img = cv2.imread(str(DATUMO / imgs[pid]), cv2.IMREAD_GRAYSCALE)
    p = r["pred"]; gx0, gy0, gx1, gy1 = r["gt"]
    xs = [p[0], p[2], gx0, gx1]; ys = [p[1], p[3], gy0, gy1]
    mx, my = 0.25*(max(xs)-min(xs)+1), 0.25*(max(ys)-min(ys)+1)
    cx0 = max(0, min(xs)-mx); cy0 = max(0, min(ys)-my)
    cx1 = min(img.shape[1], max(xs)+mx); cy1 = min(img.shape[0], max(ys)+my)
    crop = img[int(cy0):int(cy1), int(cx0):int(cx1)]
    hh = min(TH, int(crop.shape[0] * TILE_W / crop.shape[1]))
    # 축소를 먼저 하고 그린다(2026-10-09 수리) — 풀해상도 위에 타일 축척으로
    # 그린 뒤 다시 resize 하면 상자가 이중 축소(×sx²)돼 좌상단에 작게 박힌다.
    # 이 버그로 하루를 날렸다([[render-bug-check-code-and-pixels-not-vision]]).
    tile = cv2.resize(crop, (TILE_W, hh))
    tile = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)
    sxx = tile.shape[1] / (cx1 - cx0)
    syy = tile.shape[0] / (cy1 - cy0)
    cv2.rectangle(tile, (int((p[0]-cx0)*sxx), int((p[1]-cy0)*syy)),
                  (int((p[2]-cx0)*sxx), int((p[3]-cy0)*syy)), (0, 140, 255), 3)
    cv2.rectangle(tile, (int((gx0-cx0)*sxx), int((gy0-cy0)*syy)),
                  (int((gx1-cx0)*sxx), int((gy1-cy0)*syy)), (90, 255, 90), 3)
    cap = (f"#{pid} IoU {r['iou']:.2f} 커버 {r['cover']:.2f} sc {r['sc']:.2f}"
           + ("" if r["gated"] else " [게이트미달]"))
    tiles.append((tile, cap))
H = HDR + ((len(tiles)+COLS-1)//COLS) * (TH + CAP)
sheet = Image.new("RGB", (COLS*(TILE_W+6)+6, H), (16, 16, 16))
d = ImageDraw.Draw(sheet)
d.rectangle([0, 0, sheet.width, HDR-4], fill=(46, 44, 40))
d.text((10, 6), "최신 검출기(gen2_v1_step8000) 홀드아웃 최악 12장 — "
                "주황=예측 · 초록=사람 라벨", font=FONT_S, fill=(250, 240, 210))
for i, (tile, cap) in enumerate(tiles):
    cx = 4 + (i % COLS) * (TILE_W + 6)
    cy = HDR + (i // COLS) * (TH + CAP)
    sheet.paste(Image.fromarray(cv2.cvtColor(tile, cv2.COLOR_BGR2RGB)), (cx, cy))
    d.text((cx+2, cy+tile.shape[0]+4), cap, font=FONT_S, fill=(255, 220, 130))
out_png = HERE / "det_latest_worst12_v3.png"
sheet.save(out_png)
print(out_png, sheet.size)
for r in worst:
    print(f"  #{r['id']} IoU {r['iou']:.3f} 커버 {r['cover']:.3f} "
          f"sc {r['sc']}{' [게이트미달]' if not r['gated'] else ''}")
