# 단위(mg/dL) 간격을 정하기 위한 실기기 vs 합성 대조 시트.
#
# 배경(2026-09-15): 단위가 숫자에 얼마나 바싹 붙는지는 **기기 속성**이다
# (unit 요소의 hug). 실물 중에는 밴드 상자가 단위를 자를 만큼 붙은 기기가
# 있다. 그 값을 내가 실사진에서 재서 정하면 안 된다 — 실사진 라벨은 기계적
# 일관성이 없고 촬영 변인이 얹힌다(사람 지침: "실사진에 자를 대지말자").
#
# 그래서 재지 않고 **나란히 보여 준다.** 사람이 보고 기기별 hug 를 정한다.
#
# 왼쪽이 실사진(화면 크롭), 오른쪽이 합성. 합성에는 밴드 쿼드(초록)와 단위
# 상자(하늘)를 그려 현재 간격을 눈에 보이게 한다.
#
# 사용:
#   python make_unit_gap_sheet.py --synth synth_fix_1200
#   python make_unit_gap_sheet.py --profile acura_plus --real 4 --synth-n 2
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

import eval_band_detector as E
from eval_reader import load_gray
from gm_quads import load_gm_quads
from synth_profiles import PROFILE_DEVICES

HERE = Path(__file__).resolve().parent
UP = HERE.parent / "upstream" / "datumo"
TILE = 300


def _label(img, lines, color=(235, 235, 235)):
    bar = np.zeros((14 + 14 * len(lines), img.shape[1], 3), np.uint8)
    for i, t in enumerate(lines):
        cv2.putText(bar, t, (4, 12 + 14 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.34,
                    color, 1, cv2.LINE_AA)
    return np.vstack([img, bar])


def real_tiles(dev_names, gm, devs, n):
    out = []
    for cid, d in devs.items():
        if len(out) >= n:
            break
        nm = f"{d.get('brand', '')} {d.get('model', '')}".strip()
        if nm not in dev_names or d.get("status") != "identified":
            continue
        G = gm.get(cid)
        if G is None:
            continue
        img = load_gray(E.UPSTREAM / "extracted" / "TILDE" / (cid + ".jpg"))
        if img is None:
            continue
        c = E.crop_photo(img, E._rect_of(G))
        if c is None:
            continue
        crop = cv2.cvtColor(c[0], cv2.COLOR_GRAY2BGR)
        s = TILE / crop.shape[1]
        crop = cv2.resize(crop, (TILE, max(1, int(crop.shape[0] * s))))
        out.append(_label(crop, [f"REAL {cid.split('/')[-1]}"], (120, 220, 255)))
    return out


def synth_tiles(rows, pid, root, n):
    out = []
    for r in rows:
        if len(out) >= n:
            break
        if r["profile"] != pid:
            continue
        u = [x for x in r["rects"] if x[4] == "unit"]
        if not u:
            continue
        im = cv2.imread(str(root / "images" / f"{r['id']}.png"), cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        c = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
        t = max(2, im.shape[1] // 210)
        q = np.asarray(r["quad_panel"], float)
        cv2.polylines(c, [np.int32(q)], True, (0, 230, 0), t, cv2.LINE_AA)
        cv2.rectangle(c, (int(u[0][0]), int(u[0][1])),
                      (int(u[0][2]), int(u[0][3])), (90, 200, 255), t)
        bh = q[:, 1].max() - q[:, 1].min()
        gap = (u[0][1] - q[:, 1].max()) / max(bh, 1.0)
        s = TILE / c.shape[1]
        c = cv2.resize(c, (TILE, max(1, int(c.shape[0] * s))))
        out.append(_label(c, [f"SYNTH {r['label']}", f"gap {gap:+.2f} x band_h"],
                          (140, 255, 140)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", default="synth_fix_1200")
    ap.add_argument("--profile", default=None, help="한 기기만 (생략하면 전부)")
    ap.add_argument("--real", type=int, default=3)
    ap.add_argument("--synth-n", type=int, default=2)
    ap.add_argument("--out", default="_diag/unit_gap_vs_real.png")
    args = ap.parse_args()

    root = HERE / args.synth
    rows = [json.loads(l) for l in
            (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    gm, _ = load_gm_quads()
    devs = {json.loads(l)["id"]: json.loads(l)
            for l in open(HERE / "device_labels.jsonl", encoding="utf-8")}

    pids = ([args.profile] if args.profile
            else [p for p in PROFILE_DEVICES if any(r["profile"] == p for r in rows)])
    blocks = []
    for pid in pids:
        tiles = real_tiles(PROFILE_DEVICES[pid], gm, devs, args.real) \
            + synth_tiles(rows, pid, root, args.synth_n)
        if len(tiles) < 2:
            print(f"  건너뜀 {pid} (표본 부족)")
            continue
        h = max(t.shape[0] for t in tiles)
        tiles = [np.vstack([t, np.zeros((h - t.shape[0], TILE, 3), np.uint8)])
                 for t in tiles]
        head = np.zeros((22, TILE * len(tiles), 3), np.uint8)
        cv2.putText(head, f"{pid}   (left: real photos)  |  (right: synth)",
                    (6, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (240, 240, 240), 1,
                    cv2.LINE_AA)
        blocks.append(np.vstack([head, np.hstack(tiles)]))

    if not blocks:
        raise SystemExit("낼 것이 없다")
    w = max(b.shape[1] for b in blocks)
    blocks = [np.hstack([b, np.zeros((b.shape[0], w - b.shape[1], 3), np.uint8)])
              for b in blocks]
    p = HERE / args.out
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), np.vstack(blocks))
    print(f"{p}  기기 {len(blocks)}종")


if __name__ == "__main__":
    raise SystemExit(main())
