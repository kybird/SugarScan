# TE 재학습 판정 자 — 카드 'atone 레시피로 TE 재학습'(2026-09-22)의
# 사전등록 판정을 낸다.
#
# 입력: _diag/tone2te/ve_atone_s*.jsonl(대조) · ve_tone2te_s*.jsonl(실험).
# 둘 다 eval_band.py --out 산출이고 같은 VE 1000장을 짝으로 갖는다.
# frac(밴드가 프레임에서 차지하는 선형 비)은 GT 속성이라 팔과 무관하다 —
# 3분위 소속도 팔과 무관하다.
#
# 판정(카드 Note 사전등록 — 결과를 보고 고치지 않는다):
#   작음 3분위 합격률 차이, 이미지 짝 붓스트랩 95% CI
#     CI 하단 > 0             → 분포 뒤짐 — 재학습이 처방이다
#     CI 가 0 포함 + 상승<2pt → 화소 한계 — §24(해상도·접근 순서 문제)
#     그 사이                 → 판정보류, 구간만 기록한다
import argparse
import glob
import json
import random
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
# VE frac 3분위 경계(2026-09-22 eval_band 출력값 고정). 새 경계를 만들지 않는다.
TERC_EDGES = (0.171, 0.297)


def tercile_of(frac):
    if frac > TERC_EDGES[1]:
        return "큼"
    return "중간" if frac > TERC_EDGES[0] else "작음"


def load(fp):
    rows = (json.loads(l) for l in
            Path(fp).read_text(encoding="utf-8").splitlines() if l.strip())
    return {r["file_name"]: r for r in rows}


def seed_table(name, files):
    print(f"\n[{name}] 시드별")
    print("  시드    합격%   상자없음   IoU중앙   과대(p90)")
    per_seed = {}
    for f in sorted(files):
        rows = load(f)
        n = len(rows)
        npass = sum(r["pass"] for r in rows.values())
        nmiss = sum(not r["det"] for r in rows.values())
        ious = [r["iou"] for r in rows.values() if r["det"]]
        ars = [r["area_ratio"] for r in rows.values() if r["det"]]
        s = Path(f).stem.rsplit("_s", 1)[-1]
        print(f"  s{s}   {100*npass/n:6.2f}   {nmiss:6d}   "
              f"{np.median(ious):7.3f}   {np.percentile(ars, 90):8.2f}")
        per_seed[s] = rows
    return per_seed


def pass_prob(per_seed):
    """이미지별 합격 확률(시드 평균) — 팔 가족의 대표 값."""
    files = None
    for rows in per_seed.values():
        files = files or set(rows)
        files &= set(rows)
    return {fn: np.mean([s[fn]["pass"] for s in per_seed.values()])
            for fn in files}


def tercile_stats(name, per_seed, fracs):
    prob = pass_prob(per_seed)
    print(f"\n[{name}] 3분위(시드 평균)")
    out = {}
    for t in ("큼", "중간", "작음"):
        ids = [fn for fn in prob if tercile_of(fracs[fn]) == t]
        p = float(np.mean([prob[fn] for fn in ids]))
        nmiss = float(np.mean([np.mean([s[fn]["det"] for s in per_seed.values()])
                               for fn in ids]))
        ars = [s[fn]["area_ratio"] for fn in ids for s in per_seed.values()
               if s[fn]["det"]]
        out[t] = (ids, p)
        print(f"  {t:2s} n={len(ids):4d}  합격 {100*p:6.2f}%  "
              f"검출 {100*nmiss:6.2f}%  과대 p90 {np.percentile(ars, 90):.2f}")
    out["전체"] = (list(prob), float(np.mean(list(prob.values()))))
    return out


def paired_bootstrap(ids, a_prob, t_prob, b=4000, seed=20260922):
    d = np.array([t_prob[fn] - a_prob[fn] for fn in ids])
    rng = random.Random(seed)
    n = len(d)
    boots = []
    for _ in range(b):
        s = sum(d[i] for i in (rng.randrange(n) for _ in range(n)))
        boots.append(s / n)
    boots.sort()
    lo, hi = boots[int(0.025 * b)], boots[int(0.975 * b) - 1]
    return float(d.mean()), lo, hi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(HERE / "_diag" / "tone2te"))
    args = ap.parse_args()
    atone = sorted(glob.glob(f"{args.dir}/ve_atone_s*.jsonl"))
    te = sorted(glob.glob(f"{args.dir}/ve_tone2te_s*.jsonl"))
    if not atone or not te:
        raise SystemExit(f"비교 파일이 없다: atone {len(atone)} · te {len(te)}")
    # frac 은 두 팔 어느 파일에서나 같아야 한다(GT 속성). 어긋나면 짝이 깨진 것.
    fracs = {fn: r["frac"] for fn, r in load(atone[0]).items()}
    for f in atone[1:] + te:
        other = load(f)
        assert {k: v["frac"] for k, v in other.items()} == fracs, \
            f"frac 불일치 — {f} 는 같은 VE 짝이 아니다"

    a = seed_table("atone(TC 학습)", atone)
    t = seed_table("tone2te(TE 재학습)", te)
    ta = tercile_stats("atone", a, fracs)
    tt = tercile_stats("tone2te", t, fracs)

    print("\n[짝비교] atone → tone2te (이미지 짝 붓스트랩 4000회, 95% CI)")
    for terc in ("작음", "중간", "큼", "전체"):
        ids = ta[terc][0]
        diff, lo, hi = paired_bootstrap(ids, pass_prob(a), pass_prob(t))
        print(f"  {terc:2s} Δ합격 {100*diff:+6.2f}pt  "
              f"CI [{100*lo:+.2f}, {100*hi:+.2f}]")

    ids = ta["작음"][0]
    diff, lo, hi = paired_bootstrap(ids, pass_prob(a), pass_prob(t))
    print("\n[사전등록 판정 — 작음 3분위]")
    if lo > 0:
        print(f"  분포 뒤짐: CI 하단 {100*lo:+.2f}pt > 0 — 재학습이 처방이다")
    elif lo <= 0 and hi >= 0 and 100 * diff < 2.0:
        print(f"  화소 한계: CI 가 0 을 포함하고 상승 {100*diff:+.2f}pt < 2pt — "
              "§24(해상도·접근 순서) 문제다")
    else:
        print(f"  판정보류: Δ {100*diff:+.2f}pt, CI [{100*lo:+.2f}, {100*hi:+.2f}] — "
              "구간만 기록한다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
