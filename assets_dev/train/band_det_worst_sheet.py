# 밴드 검출 실패를 층을 갈라 눈으로 본다 — 세로형/가로형, 잘린 장 제외.
#
# 배경(2026-09-12): v0 재평가에서 하위 기기 목록에 가로형(OneTouch UltraMini)과
# 세로형(On Call Extra · KOOKMIN Check · GluNEO plus)이 섞여 있었다. 기본
# 눈검증 시트(eval_band_detector.py 의 gate_worst.png)는 최저 6장을 그냥 뽑는데
# 그 6장이 전부 '크롭이 밴드를 잘라낸' 장이라 다른 실패 유형이 가려진다.
# 이 스크립트는 층을 고정하고 잘린 장을 빼서 그 층의 고유 실패를 보여 준다.
#
# 자와 예측 경로를 새로 만들지 않는다 — eval_band_detector 의 det_predict ·
# crop_photo · _rect_of 와 train_band_detector 의 BandQuadNet 을 그대로 쓴다.
#
# 사용:
#   python band_det_worst_sheet.py --layer portrait --n 12
#   python band_det_worst_sheet.py --layer wide --include-clipped
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch

import eval_band_detector as E
from eval_reader import load_gray
from train_band_detector import BandQuadNet

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE.parent / "upstream" / "datumo"
RESULTS = HERE / "_diag" / "band_det_v0" / "gate_results.jsonl"
OUT = HERE / "_diag" / "band_det_v0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", choices=("portrait", "wide", "all"),
                    default="portrait")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--ckpt", default=str(HERE / "band_det_v0.pt"))
    ap.add_argument("--include-clipped", action="store_true",
                    help="크롭이 밴드를 잘라낸 장도 포함(기본은 제외)")
    ap.add_argument("--clip-thresh", type=float, default=0.95)
    a = ap.parse_args()

    res = {json.loads(l)["id"]: json.loads(l)
           for l in Path(RESULTS).read_text(encoding="utf-8").splitlines()
           if l.strip()}
    quads = {r["id"]: r for r in E._load_jsonl(E.QUADS_ORIENTED)}
    bands = {r["id"]: r for r in E._load_jsonl(E.BAND_BOXES)}

    picks = []
    for pid, r in res.items():
        g, b = quads.get(pid), bands.get(pid)
        if g is None or b is None:
            continue
        gx = E._rect_of(np.asarray(g["quad"], np.float32))
        bx = E._rect_of(np.asarray(b["quad"], np.float32))
        gw, gh = gx[2] - gx[0], gx[3] - gx[1]
        layer = "portrait" if gw / gh < 1.0 else "wide"
        if a.layer != "all" and layer != a.layer:
            continue
        ix0, iy0 = max(gx[0], bx[0]), max(gx[1], bx[1])
        ix1, iy1 = min(gx[2], bx[2]), min(gx[3], bx[3])
        inside = (max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0) /
                  max(1e-9, (bx[2] - bx[0]) * (bx[3] - bx[1])))
        if not a.include_clipped and inside < a.clip_thresh:
            continue
        picks.append((r["iou_det"], pid, r.get("device", "?"), inside))
    picks.sort()
    all_rows = list(picks)      # 층 전체(치우침 통계용)
    picks = picks[:a.n]
    if not picks:
        print("해당 층에 표본 없음")
        return 1

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = BandQuadNet().to(dev)
    model.load_state_dict(torch.load(a.ckpt, map_location=dev))
    model.eval()

    tiles = []
    for iou, pid, device, inside in picks:
        img = load_gray(UPSTREAM / "extracted" / "TILDE" / (pid + ".jpg"))
        if img is None:
            continue
        gx = E._rect_of(np.asarray(quads[pid]["quad"], np.float32))
        crop, cx0, cy0 = E.crop_photo(img, gx)
        w = 260
        vis = cv2.cvtColor(
            cv2.resize(crop, (w, max(1, int(crop.shape[0] * w / crop.shape[1])))),
            cv2.COLOR_GRAY2BGR)
        s = np.array([vis.shape[1] / crop.shape[1],
                      vis.shape[0] / crop.shape[0]], np.float32)
        pred = E.det_predict(model, crop, dev) * s
        hu = (np.asarray(bands[pid]["quad"], np.float32) - [cx0, cy0]) * s
        cv2.polylines(vis, [pred.reshape(-1, 1, 2).astype(np.int32)], True,
                      (0, 0, 255), 2)          # 빨강 = 검출기 제안
        cv2.polylines(vis, [hu.reshape(-1, 1, 2).astype(np.int32)], True,
                      (0, 255, 0), 2)          # 초록 = 사람 라벨
        vis = cv2.copyMakeBorder(vis, 30, 2, 2, 2, cv2.BORDER_CONSTANT,
                                 value=(0, 0, 0))
        cv2.putText(vis, f"{pid.split('/')[-1]}  IoU {iou:.2f}", (4, 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)
        cv2.putText(vis, device[:30], (4, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 220, 255), 1)
        tiles.append(vis)

    # 층 전체의 체계적 치우침 — 시트에 보이는 '빨강이 아래로 밀리고 작다' 가
    # 눈의 착각인지 전체 경향인지 가른다. 사람 라벨 기준 상대값이다.
    dy, dx, rh, rw = [], [], [], []
    for iou, pid, device, inside in all_rows:
        img = load_gray(UPSTREAM / "extracted" / "TILDE" / (pid + ".jpg"))
        if img is None:
            continue
        gx = E._rect_of(np.asarray(quads[pid]["quad"], np.float32))
        crop, cx0, cy0 = E.crop_photo(img, gx)
        p = E.det_predict(model, crop, dev)
        h = np.asarray(bands[pid]["quad"], np.float32) - [cx0, cy0]
        pw, ph = p[:, 0].ptp(), p[:, 1].ptp()
        hw, hh = h[:, 0].ptp(), h[:, 1].ptp()
        if hw < 4 or hh < 4:
            continue
        dy.append((p[:, 1].mean() - h[:, 1].mean()) / hh)
        dx.append((p[:, 0].mean() - h[:, 0].mean()) / hw)
        rh.append(ph / hh)
        rw.append(pw / hw)
    if dy:
        f = lambda v: f"median={np.median(v):+.3f} p10={np.percentile(v, 10):+.3f} p90={np.percentile(v, 90):+.3f}"
        print(f"\n== {a.layer} 층 전체 체계적 치우침 (n={len(dy)}, 사람 라벨 기준) ==")
        print(f"  세로 중심 이동 / 라벨 높이  {f(dy)}   (+ 는 아래로)")
        print(f"  가로 중심 이동 / 라벨 폭    {f(dx)}   (+ 는 오른쪽)")
        print(f"  높이 비 (제안/라벨)         {f(rh)}")
        print(f"  폭   비 (제안/라벨)         {f(rw)}")

    H = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 0,
                                cv2.BORDER_CONSTANT, value=(40, 40, 40))
             for t in tiles]
    cols = 4
    while len(tiles) % cols:
        tiles.append(np.full_like(tiles[0], 40))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    sheet = np.vstack(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    tag = a.layer + ("_withclip" if a.include_clipped else "")
    p = OUT / f"worst_{tag}.png"
    cv2.imwrite(str(p), sheet)
    print(f"{a.layer} 최저 {len(picks)}장 "
          f"(잘린 장 {'포함' if a.include_clipped else '제외'}) → {p}")
    for iou, pid, device, inside in picks:
        print(f"  {pid:<24} IoU {iou:.3f}  크롭안 {inside:.3f}  {device}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
