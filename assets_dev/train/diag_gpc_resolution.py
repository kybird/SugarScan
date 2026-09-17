# 글리프 평면 자가검사(gpc)의 **분해능**을 대비 구간별로 잰다.
#
# 카드 「글리프 평면 자가검사가 저대비 패널에서 분해능을 잃는다」 AC#1·#2·#3.
#
# 통과율만 보면 가드가 살아 있는지 알 수 없다. 살아 있다는 증거는 하나뿐이다 —
# **일부러 어긋뜨렸을 때 점수가 떨어지는가.** 그래서 같은 장을 두 번 잰다:
#   정상    글리프 마스크 그대로
#   어긋남  글리프 마스크를 8px 평행이동(카드 AC#2 가 지정한 크기)
# 두 점수의 차이가 그 구간의 분해능이다. 차이가 0 이면 그 구간에서 가드는 죽었다.
#
# 자를 다시 짜지 않는다 — synth_panel.glyph_plane_score 를 감싸서 인자를 그대로
# 받아 두 번 부른다. 점수 정의가 바뀌어도 이 진단이 따라간다.
#
# 사용:
#   python diag_gpc_resolution.py --count 400 --seed 23000 --shift 8
import argparse
import random

import numpy as np

import synth_panel as sp

# 대비 구간 — 밴드 p95-p5. 실측 기준선의 저대비 꼬리(40 미만 약 1%)와
# 문턱이 바닥(GPC_INK_FLOOR)에 눌리는 경계(대비 = FLOOR/K = 48)를 둘 다 담는다.
BINS = [(0, 30), (30, 48), (48, 70), (70, 100), (100, 140), (140, 10 ** 6)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=400)
    ap.add_argument("--seed", type=int, default=23000)
    ap.add_argument("--shift", type=int, default=8)
    args = ap.parse_args()

    rows = []
    real_score = sp.glyph_plane_score

    def wrapped(img, quad, glyph_warped, glass_rect, ink_thr=None):
        good = real_score(img, quad, glyph_warped, glass_rect, ink_thr)
        # 같은 자로, 마스크만 어긋뜨려 다시 잰다.
        bad_mask = np.roll(np.roll(glyph_warped, args.shift, 0),
                           args.shift, 1)
        bad = real_score(img, quad, bad_mask, glass_rect, ink_thr)
        bg, contrast = sp._gpc_bg_contrast(img, quad, glass_rect)
        rows.append({"gpc": good, "gpc_shift": bad, "contrast": float(contrast),
                     "thr": float(sp.gpc_ink_threshold(contrast))})
        return good

    sp.glyph_plane_score = wrapped
    try:
        rng = random.Random(args.seed)
        np.random.seed(args.seed)
        for _ in range(args.count):
            sp.render_panel(sp.sample_value(rng), rng)
    finally:
        sp.glyph_plane_score = real_score

    print(f"n={len(rows)} (seed {args.seed}) · 어긋뜨림 {args.shift}px")
    print(f"문턱 = max({sp.GPC_INK_FLOOR}, {sp.GPC_INK_K} x 대비) — "
          f"대비 {sp.GPC_INK_FLOOR / sp.GPC_INK_K:.0f} 아래에서는 바닥이 지배한다")
    # AC#3 — 바닥값과 광학 노이즈의 관계를 수치로. 바닥은 "배경 화소가 잉크로
    # 잘못 세어지는 비율"을 억누르는 값이라, σ 대비 몇 배인지가 근거다.
    # 배경이 N(0,σ) 면 |배경-bg| > 바닥 일 확률 = 2*(1 - Φ(바닥/σ)).
    from math import erf, sqrt
    print(f"광학 노이즈 σ 는 uniform(2, 9) (synth_panel 광학 단) — "
          f"바닥 {sp.GPC_INK_FLOOR} 이 σ 대비 몇 배이고, 배경이 잉크로 "
          f"잘못 세어질 확률은:")
    for s in (2, 4, 6, 9):
        z = sp.GPC_INK_FLOOR / s
        p_false = 1.0 - erf(z / sqrt(2.0))
        print(f"    σ={s}: 바닥 = {z:.2f}σ · 거짓 잉크 {100 * p_false:.2f}%")
    print("    σ 가 큰 쪽에서 거짓 잉크가 는다 — 어긋뜨려도 점수가 덜 떨어지는 "
          "꼬리의 원인 후보다.")

    print(f"\n{'대비 구간':<14}{'n':>5}{'gpc p50':>9}{'gpc p10':>9}"
          f"{'<0.9':>7}{'어긋 p50':>10}{'분해능 p50':>11}{'분해능 p10':>11}"
          f"{'분해능<.05':>11}")
    dead = []
    for lo, hi in BINS:
        sel = [r for r in rows if lo <= r["contrast"] < hi]
        if not sel:
            print(f"{f'{lo}~{hi}':<14}{0:>5}")
            continue
        g = np.array([r["gpc"] for r in sel])
        b = np.array([r["gpc_shift"] for r in sel])
        d = g - b
        name = f"{lo}~{hi}" if hi < 10 ** 5 else f"{lo}+"
        print(f"{name:<14}{len(sel):>5}{np.median(g):>9.3f}"
              f"{np.percentile(g,10):>9.3f}"
              f"{100*np.mean(g<0.9):>6.1f}%{np.median(b):>10.3f}"
              f"{np.median(d):>11.3f}{np.percentile(d,10):>11.3f}"
              f"{100*np.mean(d<0.05):>10.1f}%")
        dead.append((name, float(np.median(d)), float(np.mean(d < 0.05)),
                     len(sel)))

    print("\n판정 — 분해능은 '정상 gpc - 어긋뜨린 gpc' 다. 이 값이 0 에 가까우면"
          " 그 구간에서 가드는 어긋남을 못 본다.")
    for name, med, frac, n in dead:
        if med < 0.05:
            print(f"  구간 {name} (n={n}): 분해능 중앙값 {med:.3f} — "
                  f"이 구간에서 가드는 죽었다")
        else:
            print(f"  구간 {name} (n={n}): 분해능 중앙값 {med:.3f} 로 살아 있다. "
                  f"다만 장 단위로는 {100*frac:.1f}% 가 분해능 0.05 미만이다")
    print("  구간 중앙값과 장 단위 꼬리는 다른 이야기다 — 중앙값만 보면 "
          "꼬리가 안 보이고, 꼬리만 보면 구간을 싸잡게 된다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
