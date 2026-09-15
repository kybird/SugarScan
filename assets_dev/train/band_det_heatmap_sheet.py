# heat 구조의 중간 단계(모서리 히트맵)를 눈으로 본다 — 합성 vs 실사진.
#
# 배경(2026-09-14): heat 머리부는 합성 홀드아웃 지표를 전부 이기고(모서리
# 0.87% vs 1.15%, 기울기 0.139deg vs 0.194deg, corr 0.948) 실사진 게이트에서만
# 졌다(0.805 vs 0.830, 세로형 0.818 vs 0.851). 라벨을 전수 수정한 뒤에도 그대로다.
#
# fc 는 중간 표현이 Flatten 된 벡터라 볼 것이 없지만, heat 는 모서리마다
# 히트맵 한 장을 내므로 **어디를 보고 있는지 그림으로 나온다.** soft-argmax 는
# 히트맵의 무게중심이므로, 분포가 퍼지거나 봉우리가 둘이면 좌표가 그 사이
# 엉뚱한 곳에 찍힌다 — 지표로는 '조금 틀렸다'로만 보이는 것이 여기서는
# '무엇을 헷갈렸는지'로 보인다.
#
# 같이 인쇄하는 수치:
#   peak    히트맵 최대 확률 — 1 에 가까울수록 한 점을 확신한다
#   top1%   상위 1% 칸이 가진 확률 질량
#   ent     정규화 엔트로피(0=한 점, 1=완전 균일)
# 합성과 실사진에서 이 값이 갈리면 '실사진의 노이즈가 이 구조와 안 맞는다'는
# 가설에 증거가 된다.
#
# 사용:
#   python band_det_heatmap_sheet.py --ckpt band_det_heat40k.pt --n 6
#   python band_det_heatmap_sheet.py --stats-only
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch

import eval_band_detector as E
from eval_reader import load_gray
from train_band_detector import load_detector, letterbox, IMG_SIZE
from gm_quads import load_gm_quads
from band_exclusions import load_excluded

HERE = Path(__file__).resolve().parent
CORNER = ("TL", "TR", "BR", "BL")


def heatmaps(model, gray, dev):
    """(히트맵 [4,G,G] 확률, 레터박스 입력 [256,256])."""
    x, sc, px, py = letterbox(gray)
    xt = torch.from_numpy(x)[None, None].to(dev)
    with torch.no_grad():
        h = model.head(model.features(xt))
        n, c, gh, gw = h.shape
        p = torch.softmax(h.reshape(n, c, gh * gw) / model.temp, dim=-1)
        p = p.reshape(c, gh, gw).cpu().numpy()
    return p, x


def stats(p):
    """히트맵 한 장의 집중도."""
    f = p.reshape(-1)
    k = max(1, int(round(len(f) * 0.01)))
    top = np.sort(f)[::-1][:k].sum()
    ent = -(f * np.log(f + 1e-12)).sum() / np.log(len(f))
    return float(f.max()), float(top), float(ent)


def tile(gray, p, title, cell=150):
    """왼쪽에 입력, 오른쪽에 모서리 4장."""
    x, _, _, _ = letterbox(gray)
    base = cv2.cvtColor((x * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    base = cv2.resize(base, (cell * 2, cell * 2))
    cols = [base]
    for i in range(4):
        m = p[i]
        m = (m / max(m.max(), 1e-9) * 255).astype(np.uint8)
        m = cv2.resize(m, (cell, cell), interpolation=cv2.INTER_NEAREST)
        m = cv2.applyColorMap(m, cv2.COLORMAP_INFERNO)
        pk, t1, en = stats(p[i])
        cv2.putText(m, CORNER[i], (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(m, f"pk{pk:.2f}", (4, cell - 16), cv2.FONT_HERSHEY_SIMPLEX,
                    0.38, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(m, f"e{en:.2f}", (4, cell - 4), cv2.FONT_HERSHEY_SIMPLEX,
                    0.38, (255, 255, 255), 1, cv2.LINE_AA)
        cols.append(m)
    grid = np.vstack([np.hstack(cols[1:3]), np.hstack(cols[3:5])])
    row = np.hstack([base, grid])
    bar = np.zeros((24, row.shape[1], 3), np.uint8)
    cv2.putText(bar, title, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (235, 235, 235), 1, cv2.LINE_AA)
    return np.vstack([row, bar])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="band_det_heat40k.pt")
    ap.add_argument("--synth", default="synth_night_5000")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--stats-n", type=int, default=200)
    ap.add_argument("--stats-only", action="store_true")
    ap.add_argument("--out", default="_diag/heat_stages.png")
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model, arch = load_detector(HERE / args.ckpt, dev)
    if arch != "heat":
        raise SystemExit(f"{args.ckpt} 는 arch={arch} 다 — 히트맵이 없다")

    root = HERE / args.synth
    srows = [json.loads(l) for l in open(root / "manifest.jsonl", encoding="utf-8")]
    gm, _ = load_gm_quads()
    ex = load_excluded()
    rrows = [json.loads(l) for l in open(HERE / "band_boxes.jsonl", encoding="utf-8")]
    rrows = [r for r in rrows if r["id"] not in ex and r["id"] in gm]

    def synth_gray(r):
        return cv2.imread(str(root / "images" / f"{r['id']}.png"), cv2.IMREAD_GRAYSCALE)

    def real_gray(r):
        img = load_gray(E.UPSTREAM / "extracted" / "TILDE" / (r["id"] + ".jpg"))
        if img is None:
            return None
        c = E.crop_photo(img, E._rect_of(gm[r["id"]]))
        return None if c is None else c[0]

    # ── 집중도 통계
    print(f"{args.ckpt}  (arch={arch})")
    print(f"{'집단':<8} {'n':>5} {'peak':>8} {'top1%':>8} {'entropy':>9}")
    acc = {}
    for name, rows, getter in (("합성", srows, synth_gray), ("실사진", rrows, real_gray)):
        pk, t1, en = [], [], []
        for r in rows[:args.stats_n]:
            g = getter(r)
            if g is None:
                continue
            p, _ = heatmaps(model, g, dev)
            for i in range(4):
                a, b, c = stats(p[i])
                pk.append(a); t1.append(b); en.append(c)
        acc[name] = (np.median(pk), np.median(t1), np.median(en), len(pk) // 4)
        print(f"{name:<8} {acc[name][3]:>5} {acc[name][0]:>8.3f} "
              f"{acc[name][1]:>8.3f} {acc[name][2]:>9.3f}")
    if "합성" in acc and "실사진" in acc:
        s, r = acc["합성"], acc["실사진"]
        print(f"\npeak 이 합성 {s[0]:.3f} -> 실사진 {r[0]:.3f} "
              f"({100 * (r[0] / max(s[0], 1e-9) - 1):+.0f}%), "
              f"entropy {s[2]:.3f} -> {r[2]:.3f}")
        print("실사진에서 peak 가 낮고 entropy 가 높으면 히트맵이 퍼진 것이다 —"
              " soft-argmax 가 봉우리 사이를 평균해 엉뚱한 점을 찍는다.")
    if args.stats_only:
        return

    tiles = []
    for r in srows[:args.n]:
        g = synth_gray(r)
        if g is None:
            continue
        p, _ = heatmaps(model, g, dev)
        tiles.append(tile(g, p, f"SYNTH {r['id']}"))
    for r in rrows[:args.n]:
        g = real_gray(r)
        if g is None:
            continue
        p, _ = heatmaps(model, g, dev)
        tiles.append(tile(g, p, f"REAL  {r['id']}"))

    w = max(t.shape[1] for t in tiles)
    tiles = [np.hstack([t, np.zeros((t.shape[0], w - t.shape[1], 3), np.uint8)])
             for t in tiles]
    rows_ = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles) - 1, 2)]
    w2 = max(r.shape[1] for r in rows_)
    rows_ = [np.hstack([r, np.zeros((r.shape[0], w2 - r.shape[1], 3), np.uint8)])
             for r in rows_]
    head = np.zeros((30, w2, 3), np.uint8)
    cv2.putText(head, "left = letterboxed input   right 2x2 = corner heatmaps "
                "(TL TR / BL BR)   pk=peak prob  e=normalized entropy",
                (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1,
                cv2.LINE_AA)
    p = HERE / args.out
    p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(p), np.vstack([head] + rows_))
    print(f"\nsaved {p}")


if __name__ == "__main__":
    raise SystemExit(main())
