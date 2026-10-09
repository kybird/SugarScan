# 검출기 오류 11장 판(2026-10-07 사람: "검출기 오류목록 11개 보여줘").
# 구성: 실패 1(2317) + 순수 나쁜상자 8(30에폭 전량 오답) + 공동 2(458·1593,
# 에폭 따라 정답 — 감사 ②측정). 주황=배포 검출기(gen2_v1_step8000) 예측 상자,
# 초록=사람 상자 라벨(band_boxes.jsonl, 8/11장 보유). 게이트(0.25/0.02)를
# 못 넘은 장은 빨간 얇은 상자+점수로 그린다("확신 사망" 진단용).
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
FONT = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 17)
FONT_S = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 15)

GROUPS = [
    ("검출 실패(게이트 미달) — 1장", [("2317", "실패")]),
    ("순수 나쁜 상자 — 8장(에폭 30개 전량 오답, 리더 교체로 못 고침)",
     [("1612", "순수"), ("1596", "순수"), ("1643", "순수·사람판정"),
      ("956", "순수"), ("1707", "순수·사람판정"), ("606", "순수"),
      ("607", "순수"), ("1044", "순수")]),
    ("공동(경계 상자) — 2장(에폭 따라 읽힘: 458=ep5·75, 1593=ep45·50)",
     [("458", "공동·사람판정"), ("1593", "공동")]),
]

human = {}
for ln in (HERE.parent / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip():
        r = json.loads(ln)
        human[r["id"].split("/")[-1]] = r["quad"]

labels, imgs = {}, {}
for ln in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip():
        j = json.loads(ln)
        labels[j["id"].split("/")[-1]] = j["reading"]
        imgs[j["id"].split("/")[-1]] = j["image"]

e25 = {}
for ln in (HERE / "e2e_bandnet" / "gen2lad25000.jsonl").read_text(
        encoding="utf-8").splitlines():
    if ln.strip():
        r = json.loads(ln)
        e25[r["id"].split("/")[-1]] = r

dev = "cuda" if torch.cuda.is_available() else "cpu"
cd = torch.load(HERE.parent / "band_out" / "tone" / "gen2_v1_step8000",
                map_location="cpu", weights_only=False)
det = BandNet(width=cd["width"], stride=cd.get("stride", 16)).to(dev).eval()
det.load_state_dict(cd["model"])

TILE_W = 620
CAP = 40
HDR = 34
COLS = 3

rows_t = []
with torch.no_grad():
    for title, members in GROUPS:
        tiles = []
        for pid, kind in members:
            img = cv2.imread(str(DATUMO / imgs[pid]), cv2.IMREAD_GRAYSCALE)
            lb, r, dx, dy = letterbox(img, cd["size"])
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            obj, reg = det(x.to(dev))
            b, s = decode(obj.float(), reg.float(), det.stride)
            b = b[0].cpu().numpy()
            sc = float(s[0].cpu())
            p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
            frac = ((p[2]-p[0])*(p[3]-p[1])) / max(1., img.shape[1]*img.shape[0])
            gated = not (sc < 0.25 or frac < 0.02)
            hq = human.get(pid)
            xs = [p[0], p[2]] + ([pt[0] for pt in hq] if hq else [])
            ys = [p[1], p[3]] + ([pt[1] for pt in hq] if hq else [])
            cx0, cy0 = max(0, min(xs) - 0.25*(max(xs)-min(xs))), max(0, min(ys) - 0.25*(max(ys)-min(ys)))
            cx1 = min(img.shape[1], max(xs) + 0.25*(max(xs)-min(xs)))
            cy1 = min(img.shape[0], max(ys) + 0.25*(max(ys)-min(ys)))
            crop = img[int(cy0):int(cy1), int(cx0):int(cx1)].copy()
            if crop.size == 0:
                crop = img.copy()
                cx0 = cy0 = 0
            crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)   # 색은 BGR 위에
            sx = TILE_W / crop.shape[1]
            iou_txt = ""
            if hq:
                gx0, gy0 = min(pt[0] for pt in hq), min(pt[1] for pt in hq)
                gx1, gy1 = max(pt[0] for pt in hq), max(pt[1] for pt in hq)
                ix0, iy0 = max(p[0], gx0), max(p[1], gy0)
                ix1, iy1 = min(p[2], gx1), min(p[3], gy1)
                inter = max(0., ix1-ix0) * max(0., iy1-iy0)
                union = (p[2]-p[0])*(p[3]-p[1]) + (gx1-gx0)*(gy1-gy0) - inter
                iou_txt = f" IoU {inter/max(1.,union):.2f}"

            def to_px(pt):
                return (int((pt[0]-cx0)*sx), int((pt[1]-cy0)*sx))
            cv2.rectangle(crop, to_px((p[0], p[1])), to_px((p[2], p[3])),
                          (0, 140, 255), 3)                    # 주황=검출기
            if hq:
                pts = np.array([to_px(pt) for pt in hq], np.int32)
                cv2.polylines(crop, [pts], True, (90, 255, 90), 3)  # 초록=사람
            h = int(crop.shape[0] * TILE_W / crop.shape[1])
            tile = cv2.resize(crop, (TILE_W, min(h, 460)))
            er = e25.get(pid, {})
            cap = (f"#{pid} [{kind}] GT {labels.get(pid)} → 25k "
                   f"{er.get('pred', er.get('verdict'))}"
                   f" · sc {sc:.2f}{iou_txt}"
                   + ("" if hq else " · 사람상자없음"))
            tiles.append((tile, cap))
        rows_t.append((title, tiles))

rows_max = max(max(int((len(t)+COLS-1)//COLS) for _, t in rows_t), 1)
TH = 460
W = COLS * (TILE_W + 6) + 6
H = sum(HDR + ((len(t)+COLS-1)//COLS) * (TH + CAP) for _, t in rows_t)
sheet = Image.new("RGB", (W, H), (16, 16, 16))
d = ImageDraw.Draw(sheet)
y = 0
for title, tiles in rows_t:
    d.rectangle([0, y, W, y + HDR - 4], fill=(46, 44, 40))
    d.text((10, y + 6), title, font=FONT, fill=(250, 240, 210))
    y += HDR
    for i, (tile, cap) in enumerate(tiles):
        cx = 4 + (i % COLS) * (TILE_W + 6)
        cy = y + (i // COLS) * (TH + CAP)
        im = Image.fromarray(cv2.cvtColor(tile, cv2.COLOR_BGR2RGB))
        sheet.paste(im, (cx, cy))
        d.text((cx + 2, cy + tile.shape[0] + 4), cap, font=FONT_S,
               fill=(255, 220, 130))
    y += ((len(tiles)+COLS-1)//COLS) * (TH + CAP)
out = HERE / "det_err11_sheet.png"
sheet.save(out)
print(out, sheet.size)
for title, tiles in rows_t:
    print(f"  {title}: {len(tiles)}장")
