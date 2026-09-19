# 단계 2(절차적 배경) 결과표 — 사전 등록한 규칙대로만 판정한다.
#
# 계획: docs/BAND_EXP_PLAN.md §13. **규칙을 여기서 고치지 않는다.**
#
# 단계 1의 통계 결함을 여기서 고친다(§11.3): 그때 부트스트랩은 장마다 3시드
# 평균을 먼저 고정하고 기종만 재표집해서 **시드를 확률 변수로 넣지 않았다.**
# 여기서는 **시드 쌍과 기종 그룹을 각각 재표집하되 조건 간 짝을 유지**한다.
# 같은 시드 번호를 두 조건에 함께 뽑는다 — 짝을 깨면 조건 차이가 아니라
# 학습 재현성을 재게 된다.
#
# 보고는 **평균과 시드 표준편차**로 한다. 최대−최소 범위는 보조로만 쓴다 —
# 범위는 시드 수만 늘려도 커지므로 시드 수가 다른 실험과 나란히 놓을 수 없다.
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from eval_band_real import device_boxes

HERE = Path(__file__).resolve().parent
REAL = HERE / "_diag" / "band_real"
BG = HERE / "band_out" / "bg"
SEEDS = tuple(range(8))
UP = HERE.parent / "upstream" / "datacluster-glucometer-ocr"


def rows(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def groups():
    g = {}
    for line in (HERE / "device_labels.jsonl").read_text(
            encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            g[j["id"]] = (j.get("brand", "?") + " " + j.get("model", "")).strip()
    return g


def real_pass(rs, tau):
    return {r["id"]: float(r["det"] and r["contain"] >= 0.999
                           and r["area_ratio"] <= tau) for r in rs}


def synth_tau(p, tau):
    rs = rows(p)
    if not rs:
        return None, None, None
    ar = np.array([r["area_ratio"] for r in rs])
    ok = np.array([r["pass"] for r in rs])
    per = defaultdict(list)
    for r in rs:
        per[r["profile"]].append(r["pass"])
    return (100 * (ok & (ar <= tau)).mean(),
            100 * min(np.mean(v) for v in per.values()),
            sum(1 for r in rs if not r["det"]))


def boot(A, B, gmap, ids, n=5000, seed=11):
    """짝 차이의 95% 구간. **시드 쌍과 기종 그룹을 각각 재표집한다.**

    A[s][id], B[s][id] 는 조건별·시드별 통과 여부. 같은 시드 번호를 두 조건에
    함께 뽑아 **짝을 유지**한다.
    """
    by = defaultdict(list)
    for i in ids:
        by[gmap.get(i, "미상")].append(i)
    keys = list(by)
    ss = sorted(set(A) & set(B))
    rng = np.random.default_rng(seed)
    point = float(np.mean([B[s][i] - A[s][i] for s in ss for i in ids]))
    out = np.empty(n)
    for k in range(n):
        sp = rng.integers(0, len(ss), len(ss))
        gp = rng.integers(0, len(keys), len(keys))
        pick = [i for j in gp for i in by[keys[j]]]
        out[k] = np.mean([B[ss[j]][i] - A[ss[j]][i] for j in sp for i in pick])
    return point * 100, float(np.percentile(out, 2.5)) * 100, \
        float(np.percentile(out, 97.5)) * 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tau", type=float, default=2.0)
    a = ap.parse_args()
    gmap = groups()

    # ── 합성 게이트 — **각 조건의 자기 도메인**(§13.8). 퇴행 감시다 ──
    print("합성 게이트 — 자기 도메인 (대조군=V 단색 · 개입군=VB 절차적배경)")
    print(f"  {'조건':<10}{'τ=1.2':>10}{'±SD':>7}{'프로파일최저':>13}"
          f"{'검출실패':>9}")
    sv = {}
    for arm, pat in (("bce", BG / "synth_bce_s{}.jsonl"),
                     ("bg", BG / "synth_bg_s{}.jsonl")):
        v = [synth_tau(str(pat).format(s), 1.2) for s in SEEDS]
        v = [x for x in v if x[0] is not None]
        t = np.array([x[0] for x in v]); w = np.array([x[1] for x in v])
        sv[arm] = (t.mean(), w.mean())
        print(f"  {arm:<10}{t.mean():>9.2f}%{t.std(ddof=1):>7.2f}"
              f"{w.mean():>12.2f}%{np.mean([x[2] for x in v]):>9.1f}")
    cr = [synth_tau(BG / f"cross_bg_on_V_s{s}.jsonl", 1.2) for s in SEEDS]
    cr = [x[0] for x in cr if x[0] is not None]
    if cr:
        print(f"  (교차: 개입군을 단색 V 로 재면 {np.mean(cr):.2f}% "
              f"— **판정에 쓰지 않는다**)")

    # ── 실촬 코퍼스 A — 주 지표 ──
    print(f"\n실촬 코퍼스 A — **주 지표** τ={a.tau} (8시드)")
    P = {}
    for arm, pat in (("bce", REAL / "bce_s{}.jsonl"),
                     ("bg", REAL / "bg_s{}.jsonl")):
        P[arm] = {}
        for s in SEEDS:
            r = rows(str(pat).format(s))
            if r:
                P[arm][s] = real_pass(r, a.tau)
    ids = sorted(set.intersection(*[set(d) for arm in P for d in P[arm].values()]))
    for arm in ("bce", "bg"):
        v = np.array([100 * np.mean([P[arm][s][i] for i in ids])
                      for s in sorted(P[arm])])
        print(f"  {arm:<10} 평균 {v.mean():6.2f}%  SD {v.std(ddof=1):5.2f}  "
              f"n_seed={len(v)}  (범위 {v.min():.1f}~{v.max():.1f}, 보조)")
    d, lo, hi = boot(P["bce"], P["bg"], gmap, ids)
    print(f"\n  짝 차이 {d:+.2f}점  95% [{lo:+.2f}, {hi:+.2f}]")
    print(f"  (시드 쌍 + 기종 {len(set(gmap.get(i,'미상') for i in ids))}그룹을 "
          f"각각 재표집 · 조건 간 짝 유지 · 장 {len(ids)})")
    ds = [100 * np.mean([P["bg"][s][i] - P["bce"][s][i] for i in ids])
          for s in sorted(set(P["bce"]) & set(P["bg"]))]
    print(f"  시드별 개선 {' '.join(f'{x:+.1f}' for x in ds)}  "
          f"(차이의 SD {np.std(ds, ddof=1):.2f})")

    # ── 실패 분해 — 좋은 후보가 는 것인가, 잘 고르는 것인가 ──
    print("\n실패 분해 — 평균이 오르면 **어느 쪽인가**")
    print(f"  {'조건':<10}{'sel':>9}{'±SD':>7}{'gt_best':>10}{'±SD':>7}"
          f"{'격차':>8}")
    for arm in ("bce", "bg"):
        se, gb = [], []
        for s in SEEDS:
            r = rows(REAL / f"cells_{arm}_s{s}.jsonl")
            if not r:
                continue
            se.append(100 * np.mean([x["sel_ok"] for x in r]))
            gb.append(100 * np.mean([x["gt_best_ok"] for x in r]))
        se, gb = np.array(se), np.array(gb)
        print(f"  {arm:<10}{se.mean():>8.1f}%{se.std(ddof=1):>7.2f}"
              f"{gb.mean():>9.1f}%{gb.std(ddof=1):>7.2f}"
              f"{gb.mean()-se.mean():>7.1f}점")

    # ── 코퍼스 B — **밴드 정확도가 아니다** ──
    print("\n코퍼스 B (CC0) ≥90% 기기 안 — **밴드 정확도가 아니다**")
    dev = device_boxes(UP / "Annotations")
    print(f"  {'조건':<10}{'원본':>10}{'단색':>10}{'교체':>10}")
    for arm in ("bce", "bg"):
        cols = []
        for suf in ("", "_flatbg", "_swapbg0"):
            v = []
            for s in SEEDS:
                r = rows(REAL / f"datacluster_{arm}_s{s}{suf}.jsonl")
                hit = []
                for x in r:
                    if not x["det"]:
                        continue
                    dd = dev.get(x["id"].split("/", 1)[-1])
                    if dd is None:
                        continue
                    p = x["pred"]
                    pa = max(0.0, p[2]-p[0]) * max(0.0, p[3]-p[1])
                    if pa <= 0:
                        continue
                    ix = max(0.0, min(p[2], dd[2]) - max(p[0], dd[0]))
                    iy = max(0.0, min(p[3], dd[3]) - max(p[1], dd[1]))
                    hit.append(ix * iy / pa >= 0.9)
                if hit:
                    v.append(100 * np.mean(hit))
            cols.append(np.mean(v) if v else float("nan"))
        print(f"  {arm:<10}{cols[0]:>9.1f}%{cols[1]:>9.1f}%{cols[2]:>9.1f}%")

    # ── 사전 등록한 판정 (§13.5) ──
    print("\n판정 — docs/BAND_EXP_PLAN.md §13.5")
    reg1 = sv["bce"][0] - sv["bg"][0] <= 1.0
    reg2 = sv["bce"][1] - sv["bg"][1] < 5.0
    print(f"  퇴행 감시  합성 τ=1.2 하락 {sv['bce'][0]-sv['bg'][0]:+.2f}점 "
          f"{'O' if reg1 else 'X'} · 프로파일최저 하락 "
          f"{sv['bce'][1]-sv['bg'][1]:+.2f}점 {'O' if reg2 else 'X'}")
    if not (reg1 and reg2):
        print("  => **기각** (퇴행)")
    elif d >= 10.0 and lo > 0:
        print("  => **배경을 SPEC 에 넣는다** (개선 >= +10점, 구간 하한 > 0)")
    elif d > 0:
        print("  => **방향은 맞다. 축을 더 얹는다**(광학 열화) — "
              "0 < 개선 < 10점이거나 구간이 0 을 포함")
    else:
        print("  => **배경 가설을 재검토한다** (개선 <= 0)")


if __name__ == "__main__":
    main()
