# 합성 홀드아웃 퇴행 감시를 임의의 팔에 낸다 — τ 게이트·프로파일 최저·미검출.
#
# 왜(2026-09-21): §16~§24 가 "자기 도메인 VC τ=1.2 · 프로파일 최저" 를
# 인용했는데 이를 내는 범용 자가 없었다(report_bg_arms 은 bg 팔 경로가
# 하드코딩). 팔이 늘 때마다 즉석 계산이 반복되지 않게 여기 둔다.
# 재는 것은 report_bg_arms.synth_tau 와 같다: digit_box 포함(pass) ∧
# 면적비 <= tau, 프로파일별 최저 통과율, 미검출 수.
import argparse

from report_bg_arms import synth_tau
from report_fail_mix import HERE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True,
                    help="이름:디렉터리:파일접두 — 예) astride8:_diag/fix8:synth_astride8")
    ap.add_argument("--seeds", default="0,1,2,3")
    ap.add_argument("--tau", type=float, default=1.2)
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]

    print(f"합성 홀드아웃 퇴행 감시 — tau {a.tau:g}")
    print(f"  {'팔':<12}{'tau 게이트%':>13}{'프로파일 최저%':>16}{'미검출':>8}{'시드':>5}")
    for spec in a.arms.split(","):
        nm, d, pfx = spec.split(":")
        vals, miss = [], 0
        for s in seeds:
            t = synth_tau(str(HERE / d / f"{pfx}_s{s}.jsonl"), a.tau)
            if t[0] is None:
                continue
            vals.append(t)
            miss += t[2]
        if not vals:
            print(f"  {nm:<12}결과 없음")
            continue
        gate = [v[0] for v in vals]
        prof = [v[1] for v in vals]
        print(f"  {nm:<12}{sum(gate)/len(gate):>11.2f}"
              f"{sum(prof)/len(prof):>16.2f}{miss:>8}{len(vals):>5}")


if __name__ == "__main__":
    main()
