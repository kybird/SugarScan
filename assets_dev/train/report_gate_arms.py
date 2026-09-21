# 팔 간 **배포 담음·게이트** 차이를 붓스트랩 구간과 함께 낸다.
#
# 왜(2026-09-21): §22.1·§24.2 가 담음/게이트 차이의 95% 구간을 인용했는데
# 그 수치를 내는 자가 저장소에 없었다 — 즉석으로 계산한 것. CLAUDE.md "자를
# 커밋한다"에 어긋난다. 이 스크립트가 그 자를 정식으로 세운다(8번 §25 보고에
# 쓰며, 위 두 절의 재현에도 쓴다).
#
# 방법은 report_fail_mix.boot_diff 와 같다 — **시드와 장을 둘 다 다시 뽑고
# 장은 팔 사이에 짝을 유지한다.** 다만 분류(통과/일부만/…)가 아니라 두
# 이값(담음, 게이트)을 잰다:
#   담음   배포 상자(pad) 가 숫자 칸(digit_cell) 을 온전히 담는다
#   게이트 담음 ∧ 배포넓이/라벨넓이 <= tau   (§21.1 — 담음 단독은 바닥이 54.3%)
import argparse
import json
from pathlib import Path

import numpy as np

from report_fail_mix import rows, digit_cell, pad, classify

HERE = Path(__file__).resolve().parent


def per_seed(paths, keep, tau):
    """시드마다 {장 id: (담음, 게이트)}."""
    out = []
    for p in paths:
        rs = rows(p)
        if not rs:
            continue
        m = {}
        for r in rs:
            if keep is not None and r["id"] not in keep:
                continue
            if classify(r) is None:
                continue
            dep = gate = False
            if r.get("det") and r.get("gt"):
                d = digit_cell(r["gt"])
                e = pad(r["pred"])
                dep = (e[0] <= d[0] and e[1] <= d[1]
                       and e[2] >= d[2] and e[3] >= d[3])
                ga = max(1.0, (r["gt"][2]-r["gt"][0]) * (r["gt"][3]-r["gt"][1]))
                ar = (max(0.0, e[2]-e[0]) * max(0.0, e[3]-e[1])) / ga
                gate = dep and ar <= tau
            m[r["id"]] = (dep, gate)
        if m:
            out.append(m)
    return out


def boot_pred(a, b, key, n=4000, rng=None):
    """b - a 의 이값 비율 차이(%). 시드·장을 함께 재표집하고 짝을 유지한다."""
    rng = rng or np.random.default_rng(12345)
    ids = np.array(sorted(set(a[0]) & set(b[0])), dtype=object)
    na, nb = len(a), len(b)
    out = np.empty(n)
    for k in range(n):
        sub = ids[rng.integers(0, len(ids), len(ids))]
        sa = rng.integers(0, na, na)
        sb = rng.integers(0, nb, nb)
        fa = np.mean([100.0 * np.mean([a[i][x][key] for x in sub]) for i in sa])
        fb = np.mean([100.0 * np.mean([b[i][x][key] for x in sub]) for i in sb])
        out[k] = fb - fa
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True,
                    help="이름:디렉터리,... — 첫 팔이 기준(baseline)이다")
    ap.add_argument("--seeds", default="0,1,2,3")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--corpus", default="roboflow",
                    choices=["roboflow", "datumo"])
    ap.add_argument("--tau", type=float, default=2.0)
    ap.add_argument("--boot", type=int, default=4000)
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    pfx = "" if a.corpus == "datumo" else "roboflow_"

    keep = None
    if a.corpus == "roboflow":
        a.split = {"all": "all"}.get(a.split, a.split)
        sp = HERE / "rf_split.json"
        if a.split != "all" and sp.exists():
            keep = set(json.loads(sp.read_text(encoding="utf-8"))[a.split])
    else:
        a.split = "all"

    label = {"dev": "Roboflow 개발", "test": "Roboflow 봉인 시험",
             "all": ("Datumo" if a.corpus == "datumo" else "Roboflow 전량")}
    print(f"배포 담음·게이트 — {label[a.split]} · tau {a.tau:g} · "
          f"붓스트랩 {a.boot}(시드·장 함께 재표집, 짝 유지)")
    print(f"  {'팔':<12}{'담음%':>12}{'(SD)':>7}{'게이트%':>12}{'(SD)':>7}{'n':>6}")

    arms = []
    for spec in a.arms.split(","):
        nm, d = spec.split(":")
        ss = per_seed([HERE / d / (pfx + f"{nm}_s{s}.jsonl") for s in seeds],
                      keep, a.tau)
        if not ss:
            print(f"  [{nm}] 결과 없음")
            continue
        arms.append((nm, ss))
        dep = np.array([100*np.mean([v[0] for v in m.values()]) for m in ss])
        gat = np.array([100*np.mean([v[1] for v in m.values()]) for m in ss])
        f = (lambda v: v.std(ddof=1)) if len(ss) > 1 else (lambda v: 0.0)
        print(f"  {nm:<12}{dep.mean():>10.1f}{f(dep):>8.2f}"
              f"{gat.mean():>10.1f}{f(gat):>8.2f}{len(ss[0]):>6}")

    base = arms[0]
    for nm, ss in arms[1:]:
        print(f"\n  [{nm} - {base[0]}]")
        for key, name in ((0, "담음"), (1, "게이트")):
            diff = boot_pred(base[1], ss, key, a.boot)
            lo, hi = np.percentile(diff, [2.5, 97.5])
            star = " *" if (lo > 0 or hi < 0) else ""
            print(f"    {name:<4}{np.mean(diff):>+8.2f}pt  "
                  f"95% [{lo:+.2f}, {hi:+.2f}]{star}")


if __name__ == "__main__":
    main()
