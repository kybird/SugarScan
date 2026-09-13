# 글리프 평면 자가검사 잉크 문턱의 자 — 카드 「글리프 평면 자가검사의 잉크
# 문턱을 대비에 비례시킨다」(2026-09-13) AC#2·#3·#4.
#
# 시드를 고정해 한 번 렌더하고(validate_synth_panel.py 와 같은 시딩 — 렌더는
# np.random 까지 시드에 묶여 재현된다), 판마다 밴드 대비와 sel 픽셀의 |img-bg|
# 분포를 뽑아 여러 문턱 정책을 즉시 평가한다. 정책을 바꿔도 렌더 자체는
# 하나다 — 문턱은 렌더 뒤 계산이므로.
#
# 어긋뜨림 대조(AC#2)는 리뷰 2026-09-12·2026-09-13 의 방법(워프 직후
# glyph_warped = np.roll(glyph_warped, N, axis=0) 한 줄)을 렌더러 밖에서
# 같은 변환으로 적용한다 — 렌더러에 측정용 줄을 남기지 않기 위해서다.
#
#   python diag_gpc_threshold.py                          # 구판 대비 기본 실행
#   python diag_gpc_threshold.py --policies k0.20f8,k0.25f12 --compact
#
# 정책 문법: fixed:30(고정 문턱 — 구판) · k<K>f<F>(대비×K, 바닥 F) ·
# default(모듈 상수 GPC_INK_K·GPC_INK_FLOOR).
import argparse
import random

import numpy as np

import synth_panel as sp

BINS = [(0, 40, "0-40"), (40, 60, "40-60"), (60, 80, "60-80"),
        (80, 120, "80-120"), (120, 10 ** 9, "120+")]


def _parse_policy(tok):
    if tok == "default":
        return ("prop", sp.GPC_INK_K, sp.GPC_INK_FLOOR)
    if tok.startswith("fixed:"):
        return ("fixed", float(tok.split(":")[1]), None)
    if tok.startswith("k") and "f" in tok:
        k_s, f_s = tok[1:].split("f")
        return ("prop", float(k_s), float(f_s))
    raise ValueError(f"정책을 못 읽겠다: {tok}")


def _thr_of(pol, contrast):
    kind, a, b = pol
    return a if kind == "fixed" else max(b, a * contrast)


def _gpc_from_deltas(deltas, thr):
    if len(deltas) == 0:
        return 0.0
    return float(len(deltas) - np.searchsorted(deltas, thr, side="right")) \
        / len(deltas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=300)
    ap.add_argument("--seed", type=int, default=31000)
    ap.add_argument("--policies", default="fixed:30,default")
    ap.add_argument("--shifts", default="8,16,32")
    ap.add_argument("--compact", action="store_true")
    ap.add_argument("--failures", action="store_true",
                    help="각 정책에서 0.9 미만으로 떨어진 판의 대비·점수 인쇄")
    args = ap.parse_args()
    pols = [_parse_policy(t) for t in args.policies.split(",")]
    pol_names = args.policies.split(",")
    shifts = [int(s) for s in args.shifts.split(",") if s]

    rng = random.Random(args.seed)
    np.random.seed(args.seed)
    # gpc[pol_idx][shift_idx] = 판별 점수 목록. shift 0 이 어긋뜨리지 않은 판.
    gpc = [[[] for _ in range(len(shifts) + 1)] for _ in pols]
    contrasts, sel0 = [], 0
    for _ in range(args.count):
        val = sp.sample_value(rng)
        s = sp.render_panel(val, rng)
        img = s["panel"].astype(np.float32)
        gw = s["glyph_warped"]
        bg, contrast = sp._gpc_bg_contrast(
            s["panel"], s["quad"], _glass_rect(s))
        contrasts.append(contrast)
        absd = np.abs(img - bg)
        variants = [gw] + [np.roll(gw, n, axis=0) for n in shifts]
        for v_i, v in enumerate(variants):
            deltas = np.sort(absd[v > 127])
            if v_i == 0 and len(deltas) == 0:
                sel0 += 1
            for p_i, pol in enumerate(pols):
                gpc[p_i][v_i].append(_gpc_from_deltas(deltas,
                                                       _thr_of(pol, contrast)))
    contrasts = np.asarray(contrasts)
    print(f"n={args.count} seed={args.seed}  sel0(글리프 평면 빈 판)={sel0}")
    print(f"대비 bins: " + " ".join(
        f"{name}={int(((contrasts >= lo) & (contrasts < hi)).sum())}"
        for lo, hi, name in BINS))
    for p_i, (name, pol) in enumerate(zip(pol_names, pols)):
        base = np.asarray(gpc[p_i][0])
        if args.compact:
            b456 = _bin_mask(contrasts, 40, 60)
            b120 = _bin_mask(contrasts, 120, 10 ** 9)
            s8 = np.asarray(gpc[p_i][1 + shifts.index(8)]) if 8 in shifts else None
            print(f"{name:>12}  전체 median={np.median(base):.4f} "
                  f"<0.9={np.mean(base < 0.9) * 100:.1f}% | "
                  f"40-60 median={np.median(base[b456]):.4f} "
                  f"<0.9={np.mean(base[b456] < 0.9) * 100:.1f}% | "
                  f"120+ median={np.median(base[b120]):.4f} "
                  f"<0.9={np.mean(base[b120] < 0.9) * 100:.1f}%"
                  + (f" | shift8 120+={np.median(s8[b120]):.4f} "
                     f"40-60={np.median(s8[b456]):.4f}"
                     if s8 is not None else ""))
            continue
        print(f"\n== 정책 {name} ==")
        print(f"{'bin':>8} {'n':>4} {'median':>8} {'<0.9%':>7}")
        for lo, hi, bname in BINS + [(-1, 10 ** 9, "전체")]:
            m = (contrasts >= lo) & (contrasts < hi) if lo >= 0 \
                else np.ones_like(contrasts, bool)
            a = base[m]
            if len(a) == 0:
                continue
            print(f"{bname:>8} {len(a):>4} {np.median(a):>8.4f} "
                  f"{np.mean(a < 0.9) * 100:>6.1f}%")
        print("어긋뜨림 대조(np.roll, axis=0) — 구간별 median:")
        for s_i, n in enumerate(shifts):
            a = np.asarray(gpc[p_i][1 + s_i])
            cells = []
            for lo, hi, bname in BINS:
                m = (contrasts >= lo) & (contrasts < hi)
                if m.sum():
                    cells.append(f"{bname}={np.median(a[m]):.4f}")
            print(f"  shift {n:>2}px  전체 median={np.median(a):.4f} "
                  f"({', '.join(cells)})")
        if args.failures:
            for i, (c, g) in enumerate(zip(contrasts, gpc[p_i][0])):
                if g < 0.9:
                    print(f"  [미달] panel_{args.seed}_{i}  대비={c:.1f} "
                          f"gpc={g:.4f}")
    return 0


def _bin_mask(contrasts, lo, hi):
    return (contrasts >= lo) & (contrasts < hi)


def _glass_rect(s):
    """렌더 결과에서 유리 rect(px0,py0,px1,py1) 되살리기 — margins=[t,b,l,r]."""
    mg_t, mg_b, mg_l, mg_r = s["margins"]
    return (mg_l, mg_t, s["W"] - mg_r, s["H"] - mg_b)


if __name__ == "__main__":
    raise SystemExit(main())
