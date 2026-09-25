# 세그먼트 끝단 절단각 실측 — 사람 지시 2026-09-25:
# "일반 폰트는 90도로 아래쪽으로 깎는다(→ 직각 절단). 이탤릭은 기울어진
# 각도만큼 기울여서 깎는다. 자르는 각도는 실측을 해야 한다 — 45도가 아니다."
#
# 잴 것: 세로획의 아래·위 끝 가장자리가 수평선과 이루는 각(도).
#   0°=수평(획축에 수직인 직각 절단) · ±각=기울어진 절단(이탤릭 기대치).
# 가로획의 좌·우 끝은 수직선과 이루는 각으로 대칭 측정.
# 표본: 실사진(사람 밴드 라벨 슬롯, make_glyph_compare_sheet.collect_raw 와
# 동일 규약)과 DSEG 원본(Light/Regular/Bold/Italic '0','1','2','7','8').
# 방법: 이진 잉크의 연결요소별로, 끝 단면의 열(또는 행)별 최외곽 좌표를
# 중앙 80% 폭에서 1차 직선 피팅 — 기울기 = 절단각.
#
# 사용: python measure_endcut_angle.py [--per-digit 16]
import argparse

import cv2
import numpy as np

HERE = __import__("pathlib").Path(__file__).resolve().parent

from make_glyph_compare_sheet import collect_real            # noqa: E402
from synth_profiles import _dseg_raster                      # noqa: E402

H = 200


def ink(gray):
    g = cv2.resize(gray.astype(np.float32), (max(8, int(round(
        gray.shape[1] * H / gray.shape[0]))), H))
    g = (g - g.min()) / max(1e-6, g.max() - g.min())
    b = (g < 0.5).astype(np.uint8)
    if b.mean() > 0.5:
        b = 1 - b
    return b


def end_angles(b):
    """연결요소별 끝 절단각(도) — 끝단 두 극점의 현(chord) 기준.
    세로획 아래/위 끝은 수평 기준각(0=획축 수직 절단), 가로획 좌/우 끝은
    수직 기준각. V-테이퍼 끝에서도 현은 안정적이다(사람은 각을 부르는
    기준면으로 현을 본다)."""
    out = {"v_bottom": [], "v_top": [], "h_left": [], "h_right": []}
    n, lab = cv2.connectedComponents(b)
    for i in range(1, n):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 40:
            continue
        w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        x0, x1 = xs.min(), xs.max()
        y0, y1 = ys.min(), ys.max()
        m = max(3, min(w, h) // 4)          # 끝단 극점 잡는 폭

        def chord(ptsL, ptsR, span):
            (xa, ya), (xb, yb) = ptsL, ptsR
            if xb - xa < span * 0.5:
                return None
            return float(np.degrees(np.arctan2(abs(yb - ya), xb - xa)))

        if h > 1.3 * w:                      # 세로획
            L = ys[xs <= x0 + m].max()
            R = ys[xs >= x1 - m].max()
            a = chord((x0, L), (x1, R), w)
            if a is not None:
                out["v_bottom" if L >= R else "v_top"].append(a)
            # 위 끝
            L2 = ys[xs <= x0 + m].min()
            R2 = ys[xs >= x1 - m].min()
            a2 = chord((x0, L2), (x1, R2), w)
            if a2 is not None:
                out["v_top" if L2 <= R2 else "v_bottom"].append(a2)
        elif w > 1.3 * h:                    # 가로획 — 수직 기준각
            T = xs[ys <= y0 + m].min()
            B = xs[ys >= y1 - m].min()
            a = chord((y0, T), (y1, B), h)
            if a is not None:
                out["h_left" if T <= B else "h_right"].append(a)
            T2 = xs[ys <= y0 + m].max()
            B2 = xs[ys >= y1 - m].max()
            a2 = chord((y0, T2), (y1, B2), h)
            if a2 is not None:
                out["h_right" if T2 >= B2 else "h_left"].append(a2)
    return out


def report(name, agg):
    parts = []
    for k in ("v_bottom", "v_top", "h_left", "h_right"):
        v = agg[k]
        if not v:
            continue
        q = np.percentile(v, (25, 50, 75))
        parts.append(f"{k} n={len(v)} 중앙 {q[1]:+.1f}° (p25 {q[0]:+.1f}"
                     f"/p75 {q[2]:+.1f})")
    print(f"{name}: " + " | ".join(parts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-digit", type=int, default=16)
    args = ap.parse_args()

    real = collect_real(args.per_digit)
    agg = {k: [] for k in ("v_bottom", "v_top", "h_left", "h_right")}
    for d, crops in sorted(real.items()):
        for _, c in crops:
            for k, v in end_angles(ink(c)).items():
                agg[k] += v
    report(f"실사진(사람 라벨 슬롯, 자릿수 0-9 × {args.per_digit} 상한)", agg)

    for variant in ("Light", "Regular", "Bold", "Italic", "BoldItalic"):
        a2 = {k: [] for k in agg}
        for ch in "01278":
            r = _dseg_raster(ch, variant, 300)
            if r is None:
                continue
            for k, v in end_angles((np.asarray(r) > 0).astype(np.uint8)).items():
                a2[k] += v
        report(f"DSEG {variant}('0','1','2','7','8')", a2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
