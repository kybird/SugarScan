# 기기 편중 A/B 짝비교 — 「기기 편중을 줄이면 미학습 기기 성적이 오르는지」.
#
# 대조군(기기 단절 자연 분포)과 실험팔(절단/균등화)의 reader_preds_tta.json 을
# 같은 홀드아웃 사진끼리 짝지어 비교한다. 두 팔의 홀드아웃은 동일 배열을
# 복사한 것이라 짝이 구조적으로 성립한다. McNemar 정확검정(이항)으로
# 오답↔정답 교차 수의 대칭성을 본다 — 층을 합치지 않고 완전일치·위험군을
# 나눠 각각 계산한다.
import argparse
import json
import math
from pathlib import Path

from device_eval_report import layers_of, device_of  # 재사용, 재구현 금지


def binom_two_sided(k, n, p=0.5):
    """정확 이항 검정 양측 p — 작은 n 이항은 직접 합산."""
    def pmf(i):
        return math.comb(n, i) * p ** i * (1 - p) ** (n - i)
    if n == 0:
        return 1.0
    pk = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1) if pmf(i) <= pk + 1e-12))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--name", default="arm")
    args = ap.parse_args()
    ctl = json.loads(Path(args.control).read_text(encoding="utf-8"))
    arm_full = json.loads(Path(args.arm).read_text(encoding="utf-8"))
    # 팔의 eval 은 "팔 학습셋만 제외한 풀"을 평가한다(절단 팔은 1,891장처럼
    # 커진다). 비교의 정본은 대조군 홀드아웃(기기 단절 1,138장)이므로 팔을
    # 이 키 집합으로 제한한다 — 짝비교의 전제.
    missing = set(ctl) - set(arm_full)
    assert not missing, f"팔 preds 가 대조군 홀드아웃을 덮지 못한다: {len(missing)}장"
    arm = {k: arm_full[k] for k in ctl}

    def stats(preds):
        n = len(preds)
        c = {"exact": 0, "risky": 0, "safe": 0, "blank": 0}
        for pred, gt, _ in preds.values():
            c[layers_of(pred, gt)] += 1
        return c, n

    for label, preds in (("대조군(자연 분포)", ctl), (args.name, arm)):
        c, n = stats(preds)
        print(f"{label}: {n}장 — exact {c['exact']} ({100*c['exact']/n:.2f}%) "
              f"risky {c['risky']} ({100*c['risky']/n:.2f}%) "
              f"safe {c['safe']} blank {c['blank']}")

    # 짝비교: 정답 여부(완전일치)의 교차 표.
    b = sum(1 for i in ctl if ctl[i][0] == ctl[i][1] and arm[i][0] != arm[i][1])
    c_ = sum(1 for i in ctl if ctl[i][0] != ctl[i][1] and arm[i][0] == arm[i][1])
    p = binom_two_sided(b, b + c_)
    print(f"\n완전일치 교차: 대조만 정답 {b} / 팔만 정답 {c_} "
          f"→ McNemar p={p:.4f}")

    # 위험군도 짝으로: 위험→비위험 이동.
    r_ctl = sum(1 for i in ctl if layers_of(*ctl[i][:2]) == "risky")
    r_arm = sum(1 for i in arm if layers_of(*arm[i][:2]) == "risky")
    print(f"위험군: 대조 {r_ctl}건 → 팔 {r_arm}건")

    by_dev = {}
    for i in ctl:
        dev = device_of(i)
        e_c = ctl[i][0] == ctl[i][1]
        e_a = arm[i][0] == arm[i][1]
        d = by_dev.setdefault(dev, [0, 0, 0])  # n, ctl_exact, arm_exact
        d[0] += 1
        d[1] += e_c
        d[2] += e_a
    print(f"\n{'사진':>4} {'대조%':>6} {'팔%':>6} {'Δpp':>6}  기기")
    for dev, (n, ec, ea) in sorted(by_dev.items(), key=lambda kv: -kv[1][0]):
        name = " / ".join(p for p in dev if p) or "(무명)"
        print(f"{n:4d} {100*ec/n:6.1f} {100*ea/n:6.1f} "
              f"{100*(ea-ec)/n:+6.1f}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
