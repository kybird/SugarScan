# 단계 3 결과 — **숫자 칸을 자르지 않는가**가 주 지표다.
#
# 숫자 칸은 사람 밴드 라벨에서 역산한다. 라벨 규약(webtool 밴드 모드)과
# 생성기(lcd_layout.BAND_MARGIN)가 **같은 값**을 쓴다: 숫자 칸 + 사방
# `BAND_MARGIN * 숫자높이`. 따라서 라벨을 사방으로 라벨높이의
# `BAND_MARGIN/(1+2*BAND_MARGIN)` 만큼 줄이면 숫자 칸이 나온다.
#
# 합성에서 검증했다(세트 V n=1000, 참 digit_box 와 대조):
#   변 오차/숫자크기  p10 -0.001 · 중앙 +0.006 · p90 +0.017
# 즉 숫자 크기의 1~2% 안쪽이다. **잉크 추출로 추정하려던 앞선 시도(600장 중
# 143장 실패)와 달리 규약에서 곧장 나오므로 실패하지 않는다.**
#
# 배포 상자는 build_cache_v2.BOX_MARGIN 을 import 해서 쓴다 — 베끼지 않는다.
import argparse
import json
from pathlib import Path

import numpy as np

from lcd_layout import BAND_MARGIN
from build_cache_v2 import BOX_MARGIN

HERE = Path(__file__).resolve().parent
REAL = HERE / "_diag" / "band_real"
FIX = HERE / "band_out" / "fix"
K = BAND_MARGIN / (1.0 + 2.0 * BAND_MARGIN)


def rows(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def digit_cell(gt):
    """사람 밴드 라벨 -> 숫자 칸 (규약에서 역산)."""
    m = (gt[3] - gt[1]) * K
    return [gt[0] + m, gt[1] + m, gt[2] - m, gt[3] - m]


def pad(q):
    w, h = q[2] - q[0], q[3] - q[1]
    ml, mr, mt, mb = BOX_MARGIN
    return [q[0] - w * ml, q[1] - h * mt, q[2] + w * mr, q[3] + h * mb]


def covers(box, inner):
    return (box[0] <= inner[0] and box[1] <= inner[1]
            and box[2] >= inner[2] and box[3] >= inner[3])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="bg,grow,under,both")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--tau", type=float, default=2.0)
    a = ap.parse_args()
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    seeds = [int(x) for x in a.seeds.split(",")]

    print(f"실촬 코퍼스 A 272장 · τ={a.tau} · BOX_MARGIN={BOX_MARGIN}")
    print(f"  {'조건':<7}{'원시가 숫자칸':>14}{'±SD':>7}{'배포가 숫자칸':>14}"
          f"{'±SD':>7}{'배포+면적≤τ':>13}{'검출실패':>9}")
    base = None
    for arm in arms:
        raw, dep, gate, miss = [], [], [], []
        for s in seeds:
            rs = rows(REAL / f"{arm}_s{s}.jsonl")
            if not rs:
                continue
            r1, d1, g1 = [], [], []
            for r in rs:
                if not r["det"] or not r.get("gt"):
                    r1.append(False); d1.append(False); g1.append(False)
                    continue
                dc = digit_cell(r["gt"])
                e = pad(r["pred"])
                ga = max(1.0, (r["gt"][2]-r["gt"][0]) * (r["gt"][3]-r["gt"][1]))
                ea = max(0.0, e[2]-e[0]) * max(0.0, e[3]-e[1])
                r1.append(covers(r["pred"], dc))
                d1.append(covers(e, dc))
                g1.append(covers(e, dc) and ea / ga <= a.tau)
            raw.append(100*np.mean(r1)); dep.append(100*np.mean(d1))
            gate.append(100*np.mean(g1))
            miss.append(sum(1 for r in rs if not r["det"]))
        if not raw:
            continue
        raw, dep, gate = np.array(raw), np.array(dep), np.array(gate)
        if base is None:
            base = (raw.mean(), dep.mean(), gate.mean())
        print(f"  {arm:<7}{raw.mean():>13.1f}%{raw.std(ddof=1):>7.2f}"
              f"{dep.mean():>13.1f}%{dep.std(ddof=1):>7.2f}"
              f"{gate.mean():>12.1f}%{np.mean(miss):>9.1f}")

    print("\n합성 세트 VB (퇴행 감시) — 숫자 필드 포함 ∧ 면적비")
    print(f"  {'조건':<7}{'τ=1.2':>9}{'τ=2.0':>9}{'프로파일최저':>13}")
    for arm in arms:
        pat = (FIX / f"synth_{arm}_s{{}}.jsonl" if arm != "bg"
               else HERE / "band_out" / "bg" / f"synth_{arm}_s{{}}.jsonl")
        t12, t20, worst = [], [], []
        for s in seeds:
            rs = rows(str(pat).format(s))
            if not rs:
                continue
            ar = np.array([r["area_ratio"] for r in rs])
            ok = np.array([r["pass"] for r in rs])
            t12.append(100*(ok & (ar <= 1.2)).mean())
            t20.append(100*(ok & (ar <= 2.0)).mean())
            per = {}
            for r in rs:
                per.setdefault(r["profile"], []).append(r["pass"])
            worst.append(100*min(np.mean(v) for v in per.values()))
        if t12:
            print(f"  {arm:<7}{np.mean(t12):>8.2f}%{np.mean(t20):>8.2f}%"
                  f"{np.mean(worst):>12.2f}%")

    print("\n판정 기준(돌리기 전에 적음, BAND_EXP_PLAN §15)")
    print("  주 지표: **배포 상자가 숫자 칸을 담고 면적비<=τ** — 3점 이상 개선")
    print("  안전 조건: 원시가 숫자 칸을 담는 비율이 대조군보다 낮아지면 기각")
    print("  퇴행 감시: 합성 VB τ=1.2 하락 1점 이내 · 프로파일 최저 5점 이내")


if __name__ == "__main__":
    main()
