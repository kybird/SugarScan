# 여백(크롭 여유) 정책의 선언값과 출력값을 나란히 인쇄한다.
#
# 카드 「밀도 최대 선택이 여백 분포를 왜곡한다」 AC#1·#2 의 자.
#
# 왜 필요한가: 샘플러는 타이트 크롭을 30% 뽑겠다고 선언하는데, 예전에는
# render_panel 이 최대 3회 렌더해 **밀도가 가장 높은 장**을 골랐다. 몸체가
# 두꺼울수록 밀도가 높으니 타이트 크롭이 계통적으로 탈락해 출력이 15.3% 로
# 반토막 났다. 선언과 출력을 나란히 놓지 않으면 이런 편향은 안 보인다.
#
# **분모를 조심한다.** 30% 선언은 `layout` 이 선언되지 않은 프로파일
# (generic_v1)에만 적용된다. layout 이 있는 기기는 여백이 기기 형질이라
# 샘플러가 손대지 않는다. 전체 코퍼스를 분모로 쓰면 30% 와 비교할 수 없다
# ([[comparison-across-different-denominators]]).
#
# 타이트 판정: 상·하 여백이 둘 다 캔버스의 2% 이하.
#   타이트 가지는 네 변 모두 uniform(0.005, 0.02),
#   느슨 가지는 상 uniform(0.03, 0.12) · 하 uniform(0.03, 0.14) 이라
#   상·하 2% 이하는 타이트 가지에서만 나온다(좌우는 두 가지가 겹친다).
#
# 사용:
#   python check_margin_policy.py --count 300 --seed 31000
import argparse
import random
from collections import Counter

import numpy as np

import synth_panel as sp
import synth_profiles as sprof

DECLARED_TIGHT_P = 0.30      # synth_panel.py 의 `rng.random() < 0.30`
TIGHT_FRAC = 0.02            # 타이트 가지의 여백 상한(캔버스 비율)
TOL_PP = 3.0                 # AC#1 의 허용 오차


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=300)
    ap.add_argument("--seed", type=int, default=31000)
    args = ap.parse_args()

    no_layout = {p["id"] for p in sprof.PROFILES if not p.get("layout")}
    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    rows = []
    for _ in range(args.count):
        s = sp.render_panel(sp.sample_value(rng), rng)
        t, b, l, r = s["margins"]
        rows.append({"pid": s["profile"], "H": s["H"], "W": s["W"],
                     "t": t / s["H"], "b": b / s["H"],
                     "l": l / s["W"], "r": r / s["W"]})

    gov = [x for x in rows if x["pid"] in no_layout]
    fixed = [x for x in rows if x["pid"] not in no_layout]
    print(f"렌더 n={len(rows)} (seed {args.seed})")
    print(f"  샘플러가 정하는 장(layout 선언 없음: {sorted(no_layout)}) "
          f"n={len(gov)}")
    print(f"  기기가 정하는 장(layout 선언 있음) n={len(fixed)} — "
          f"30% 선언의 분모가 아니다")
    if not gov:
        print("샘플러가 정하는 장이 0 — 비교할 수 없다")
        return 1

    tight = [x for x in gov if x["t"] <= TIGHT_FRAC and x["b"] <= TIGHT_FRAC]
    got = 100.0 * len(tight) / len(gov)
    dec = 100.0 * DECLARED_TIGHT_P
    ok = abs(got - dec) <= TOL_PP
    print(f"\n타이트 크롭  선언 {dec:.1f}%  출력 {got:.1f}% "
          f"({len(tight)}/{len(gov)})  차이 {got - dec:+.1f}pp  "
          f"[{'OK' if ok else 'FAIL'} 허용 {TOL_PP}pp]")

    print("\n여백 분포 (캔버스 비율, 샘플러가 정하는 장만)")
    print(f"{'변':<6}{'선언 범위':<26}{'출력 p10':>10}{'p50':>9}{'p90':>9}")
    decl = {"t": "타이트 .005~.02 / 느슨 .03~.12",
            "b": "타이트 .005~.02 / 느슨 .03~.14",
            "l": "타이트 .005~.02 / 느슨 .01~.07",
            "r": "타이트 .005~.02 / 느슨 .01~.07"}
    for k in ("t", "b", "l", "r"):
        v = np.array([x[k] for x in gov])
        print(f"{k:<6}{decl[k]:<26}{np.percentile(v,10):>10.4f}"
              f"{np.median(v):>9.4f}{np.percentile(v,90):>9.4f}")

    print("\n기기가 정하는 장의 프로파일 분포: "
          + ", ".join(f"{k} {v}" for k, v in
                      Counter(x["pid"] for x in fixed).most_common()))
    print("\n※ 이 수치는 현재 코드의 것이다. 카드 Goal 에 적힌 15.3%/31.7% 는 "
          "2026-09-12 측정이고, 그 뒤 렌더러가 여러 번 바뀌어 rng 소비가 "
          "달라졌다 — 같은 시드라도 같은 장이 아니다. 나란히 놓지 말 것.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
