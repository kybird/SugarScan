# 극성 자의 배경 기준(bg)을 기기별로 열어 본다 — 2026-09-13.
#
# measure_polarity.polarity_of 는 bg 를 'GM 크롭 전체의 중앙값'으로 잡는다.
# 크롭에 어두운 베젤 링이 섞이면 중앙값이 몸체 쪽으로 끌려가 액정 바탕보다
# 어두워지고, 그러면 밝은 꼬리가 더 멀어져 정상 패널이 '반전'으로 뒤집힌다.
# synth_panel._gpc_bg_contrast 는 같은 함정을 이미 겪고 '쿼드 바깥 유리'로
# 옮겼다(2026-09-12 주석) — 이 자는 옮기지 않았다.
#
# 이 스크립트는 판정을 바꾸지 않는다. 자의 중간값(bg·p5·p95)과, bg 를 '밴드
# 바깥 화면'으로 바꿨을 때의 판정을 나란히 찍어 어긋나는 기기를 보여 준다.
#
#   conda run -n sugartrain python diag_polarity_bg.py "ACURA PLUS" "도루코S Premium"
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import measure_polarity as mp  # noqa: E402
from eval_reader import load_gray  # noqa: E402


def rows_for(names):
    quads = {r["id"]: r for r in mp._load_jsonl(mp.QUADS_ORIENTED)}
    devices = {r["id"]: r for r in mp._load_jsonl(mp.DEVICE_LABELS)}
    out = []
    for b in mp._load_jsonl(mp.BAND_BOXES):
        d = devices.get(b["id"])
        if not d or d.get("status") != "identified":
            continue
        name = f"{d['brand']} {d['model']}".strip()
        if names and name not in names:
            continue
        g = quads.get(b["id"])
        if g is None:
            continue
        p = mp.UPSTREAM / "extracted" / "TILDE" / (b["id"] + ".jpg")
        if not p.exists():
            continue
        img = load_gray(p)
        if img is None:
            continue
        gx0, gy0, gx1, gy1 = mp._rect_of(g["quad"])
        crop = img[max(0, int(gy0)):int(gy1), max(0, int(gx0)):int(gx1)]
        if min(crop.shape) < 24:
            continue
        gw, gh = gx1 - gx0, gy1 - gy0
        bx0, by0, bx1, by1 = mp._rect_of(b["quad"])
        frac = ((bx0 - gx0) / gw, (by0 - gy0) / gh,
                (bx1 - gx0) / gw, (by1 - gy0) / gh)
        r = mp.polarity_of(crop, frac)
        if r is None:
            continue
        inv_ruler, contrast = r
        H, W = crop.shape
        x0, y0 = max(0, int(frac[0] * W)), max(0, int(frac[1] * H))
        x1, y1 = min(W, int(np.ceil(frac[2] * W))), min(H, int(np.ceil(frac[3] * H)))
        f = crop.astype(np.float32)
        bg_crop = float(np.median(f))
        m = f.copy()
        m[y0:y1, x0:x1] = np.nan          # 밴드를 뺀 나머지 = 화면 바탕
        bg_out = float(np.nanmedian(m))
        band = f[y0:y1, x0:x1]
        p5, p95 = (float(np.percentile(band, q)) for q in (5, 95))
        inv_out = abs(p95 - bg_out) > abs(p5 - bg_out)
        # 셋째 기준 — 밴드 '안'의 중앙값. 7-세그 밴드는 면적의 대부분이
        # 바탕이라 중앙값이 곧 액정 바탕이다. 베젤이 크롭에 얼마나 섞였든
        # 영향을 받지 않는다(국소 기준).
        bg_band = float(np.median(band))
        inv_band = abs(p95 - bg_band) > abs(p5 - bg_band)
        # 넷째·다섯째 후보(2026-09-13, 사람 정답 채점에서 밴드중앙이 저대비
        # 패널 셋을 놓친 뒤 추가). 둘 다 '잉크는 소수파'라는 물리에서 온다 —
        # 7-세그 밴드는 면적의 대부분이 바탕이고 켜진 획은 일부다.
        #   mode  바탕 = 밴드 히스토그램의 봉우리(중앙값보다 잉크에 덜 끌린다)
        #   minority  p5~p95 중점을 기준으로 화소가 적은 쪽이 잉크다
        hist = np.bincount(band.astype(np.uint8).ravel(), minlength=256)
        k = np.ones(9) / 9.0
        bg_mode = float(np.argmax(np.convolve(hist.astype(np.float64), k, "same")))
        mid = (p5 + p95) / 2.0
        bright_frac = float((band > mid).mean())
        out.append((b["id"], name, bg_crop, bg_out, p5, p95,
                    bool(inv_ruler), bool(inv_band), contrast, bg_band,
                    bg_mode, bright_frac))
    return out


if __name__ == "__main__":
    from collections import defaultdict
    names = set(sys.argv[1:])
    rows = rows_for(names)
    per = defaultdict(lambda: [0, 0, 0])   # name -> [자 반전, 밴드중앙 반전, n]
    flips = 0
    for i, n, bc, bo, p5, p95, ir, ib, c, bb, bm, bf in rows:
        flips += int(ir != ib)
        per[n][0] += int(ir)
        per[n][1] += int(ib)
        per[n][2] += 1
    print(f"{'기기':32} {'n':>3} {'자 반전':>8} {'밴드중앙 반전':>14}")
    for n in sorted(per, key=lambda k: -per[k][2]):
        a, b_, c_ = per[n]
        print(f"{n:32} {c_:3d} {a:8d} {b_:14d}"
              f"{'   <- 갈림' if a != b_ else ''}")
    print()
    print(f"n={len(rows)} · 두 기준이 갈린 장 {flips}")
