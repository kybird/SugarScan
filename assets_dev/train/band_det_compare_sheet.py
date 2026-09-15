# 두 검출기의 예측을 같은 사진 위에 겹쳐 눈으로 가른다.
#
# 배경(2026-09-14): heat 구조가 합성 지표를 전부 이기고(모서리 0.87% vs 1.15%,
# 기울기 0.139deg vs 0.194deg) 실사진 게이트에서만 졌다(0.798 vs 0.824).
# 두 해석이 가능한데 지금 자로는 못 가른다:
#   A 헛기울기를 낸다 — 진짜 퇴보
#   B 진짜 기울기를 잡는데 라벨이 축정렬이라 손해로 잡힌다 — 자의 착시
# 사람 라벨이 기울기를 담지 못하므로(band_det_orient_split.py 머리말) 남은
# 방법은 사람이 보는 것이다. 각도를 재게 하는 게 아니라 '숫자줄을 감쌌나'만
# 보면 되므로 정밀도 요구가 없다.
#
# 자와 예측 경로를 새로 만들지 않는다 — eval_band_detector 의 det_predict ·
# crop_photo · _rect_of 를 그대로 쓴다.
#
# 사용:
#   python band_det_compare_sheet.py --a band_det_n40k_ep60.pt \
#          --b band_det_heat40k.pt --n 12 --pick disagree --out cmp.png
import argparse
from pathlib import Path

import cv2
import numpy as np

import eval_band_detector as E
from eval_reader import load_gray
from train_band_detector import load_detector
from gm_quads import load_gm_quads

HERE = Path(__file__).resolve().parent
UPSTREAM = E.UPSTREAM
TILE_W = 460


def dashed_poly(img, q, color, thick=2, dash=12, gap=8):
    """점선 사각형 — 실선(사람 라벨)과 한눈에 구분되게."""
    q = np.asarray(q, np.float32)
    for i in range(4):
        p0, p1 = q[i], q[(i + 1) % 4]
        L = float(np.hypot(*(p1 - p0)))
        if L < 1:
            continue
        d = (p1 - p0) / L
        t = 0.0
        while t < L:
            a = p0 + d * t
            b = p0 + d * min(t + dash, L)
            cv2.line(img, tuple(np.int32(a)), tuple(np.int32(b)),
                     color, thick, cv2.LINE_AA)
            t += dash + gap


def tilt(q):
    q = np.asarray(q, float)
    a = np.degrees(np.arctan2(q[1, 1] - q[0, 1], q[1, 0] - q[0, 0]))
    b = np.degrees(np.arctan2(q[2, 1] - q[3, 1], q[2, 0] - q[3, 0]))
    return (a + b) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="band_det_n40k_ep60.pt")
    ap.add_argument("--b", default="band_det_heat40k.pt")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--pick", default="disagree",
                    choices=["disagree", "worst-b", "random"])
    ap.add_argument("--layer", default="all", choices=["all", "portrait", "wide"])
    ap.add_argument("--out", default="_diag/band_det_compare.png")
    args = ap.parse_args()

    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ma, _ = load_detector(HERE / args.a, dev)
    mb, _ = load_detector(HERE / args.b, dev)

    gm, _ = load_gm_quads()
    bands = E._load_jsonl(E.BAND_BOXES)
    rows = []
    for bd in bands:
        pid = bd["id"]
        g = gm.get(pid)
        if g is None:
            continue
        ar = (g[:, 0].max() - g[:, 0].min()) / max(1.0, g[:, 1].max() - g[:, 1].min())
        if args.layer == "portrait" and ar > 1:
            continue
        if args.layer == "wide" and ar <= 1:
            continue
        rows.append((pid, np.asarray(bd["quad"], np.float32), g))

    out = []
    for pid, lab, g in rows:
        img = load_gray(UPSTREAM / "extracted" / "TILDE" / (pid + ".jpg"))
        if img is None:
            continue
        rect = E._rect_of(g)
        c = E.crop_photo(img, rect)
        if c is None:
            continue
        crop, cx, cy = c
        qa = E.det_predict(ma, crop, dev)
        qb = E.det_predict(mb, crop, dev)
        labc = lab - np.array([cx, cy], np.float32)
        out.append(dict(id=pid, crop=crop, lab=labc, qa=qa, qb=qb,
                        ia=E.poly_iou(qa, labc), ib=E.poly_iou(qb, labc)))

    if args.pick == "disagree":
        out.sort(key=lambda r: -abs(tilt(r["qa"]) - tilt(r["qb"])))
    elif args.pick == "worst-b":
        out.sort(key=lambda r: r["ib"])
    picks = out[:args.n]

    tiles = []
    for r in picks:
        crop = cv2.cvtColor(r["crop"], cv2.COLOR_GRAY2BGR)
        sc = TILE_W / crop.shape[1]
        crop = cv2.resize(crop, (TILE_W, int(crop.shape[0] * sc)))
        cv2.polylines(crop, [np.int32(r["lab"] * sc)], True, (0, 220, 0), 2,
                      cv2.LINE_AA)                                  # 사람: 실선 초록
        dashed_poly(crop, r["qa"] * sc, (255, 200, 0))              # A: 점선 하늘
        dashed_poly(crop, r["qb"] * sc, (0, 120, 255))              # B: 점선 주황
        bar = np.zeros((58, TILE_W, 3), np.uint8)
        cv2.putText(bar, r["id"], (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (230, 230, 230), 1, cv2.LINE_AA)
        cv2.putText(bar, f"A IoU {r['ia']:.3f}  tilt {tilt(r['qa']):+.2f}",
                    (6, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(bar, f"B IoU {r['ib']:.3f}  tilt {tilt(r['qb']):+.2f}",
                    (6, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 120, 255), 1,
                    cv2.LINE_AA)
        tiles.append(np.vstack([crop, bar]))

    if not tiles:
        raise SystemExit("고를 장이 없다")
    h = max(t.shape[0] for t in tiles)
    tiles = [np.vstack([t, np.zeros((h - t.shape[0], TILE_W, 3), np.uint8)])
             for t in tiles]
    cols = 4
    grid = [np.hstack(tiles[i:i + cols] + [np.zeros((h, TILE_W, 3), np.uint8)]
                      * ((cols - len(tiles[i:i + cols])) % cols))
            for i in range(0, len(tiles), cols)]
    sheet = np.vstack(grid)
    head = np.zeros((34, sheet.shape[1], 3), np.uint8)
    cv2.putText(head, f"green solid = human label   A(cyan dash) = {args.a}"
                f"   B(orange dash) = {args.b}", (8, 23),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1, cv2.LINE_AA)
    sheet = np.vstack([head, sheet])
    p = HERE / args.out
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), sheet)
    print(f"{p}  ({len(picks)}장, pick={args.pick}, layer={args.layer})")


if __name__ == "__main__":
    raise SystemExit(main())
