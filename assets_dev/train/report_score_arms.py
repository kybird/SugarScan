# 단계 1(점수 감독) 결과표 — 사전 등록한 규칙대로만 판정한다.
#
# 계획과 판정 규칙: docs/BAND_EXP_PLAN.md §5·§6. **규칙을 여기서 고치지
# 않는다.** 고쳐야 할 이유가 생기면 그 문서에 이유와 날짜를 적고 고친다.
#
# 주 지표  실촬 코퍼스 A, τ=2.0 통과율 (밴드 전체 포함 ∧ 면적비 <= 2.0)
#          3시드 평균. 미리 하나로 고정했다 — 여러 지표 중 좋은 것을
#          사후에 고르지 않기 위해서다.
# 불확실성 **기종 그룹 단위** 부트스트랩. 장 단위로 재표집하면 같은 기종
#          28장이 독립 표본인 척한다(코퍼스 A 는 272장/51그룹).
#          조건 간 비교는 **같은 이미지의 짝 차이**로 본다.
#
# 입력은 전부 각 스크립트가 직접 쓴 jsonl 이다. 로그를 파싱하지 않는다 —
# tee 로 흘린 로그는 중복·누락이 있었다(2026-09-18).
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REAL = HERE / "_diag" / "band_real"
SCORE = HERE / "band_out" / "score"
ARMS = ("bce", "iou", "centerness")
SEEDS = (0, 1, 2)


def rows(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8")
            .splitlines() if l.strip()]


def groups():
    """코퍼스 A 의 기종 그룹. 부트스트랩 단위다."""
    g = {}
    for line in (HERE / "device_labels.jsonl").read_text(
            encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            g[j["id"]] = (j.get("brand", "?") + " " + j.get("model", "")).strip()
    return g


def real_pass(rs, tau):
    """장마다 통과 여부 (밴드 전체 포함 ∧ 면적비 <= τ). 미검출은 실패."""
    return {r["id"]: bool(r["det"] and r["contain"] >= 0.999
                          and r["area_ratio"] <= tau) for r in rs}


def boot_delta(base, arm, gmap, n=5000, seed=7):
    """짝 차이의 95% 부트스트랩 구간. **기종 그룹을 재표집한다.**"""
    ids = sorted(set(base) & set(arm))
    by = defaultdict(list)
    for i in ids:
        by[gmap.get(i, "미상")].append(float(arm[i]) - float(base[i]))
    keys = list(by)
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for k in range(n):
        pick = rng.integers(0, len(keys), len(keys))
        v = np.concatenate([by[keys[i]] for i in pick])
        out[k] = v.mean()
    d = float(np.mean([x for k in keys for x in by[k]]))
    return d * 100, float(np.percentile(out, 2.5)) * 100, \
        float(np.percentile(out, 97.5)) * 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tau", type=float, default=2.0, help="주 지표의 τ")
    a = ap.parse_args()
    gmap = groups()

    # ── 합성 게이트 (퇴행 감시) ──
    print("합성 세트 V — 굽는 시드가 다른 홀드아웃 (퇴행 감시)")
    print(f"  {'조건':<12}{'τ=1.2':>9}{'τ=2.0':>9}{'검출실패':>9}"
          f"{'프로파일최저':>13}")
    synth = {}
    for t in ARMS:
        a12, a20, miss, worst = [], [], [], []
        for s in SEEDS:
            p = SCORE / f"synth_{t}_s{s}.jsonl"
            if not p.exists():
                continue
            rs = rows(p)
            ar = np.array([r["area_ratio"] for r in rs])
            ok = np.array([r["pass"] for r in rs])
            a12.append(100 * (ok & (ar <= 1.2)).mean())
            a20.append(100 * (ok & (ar <= 2.0)).mean())
            miss.append(sum(1 for r in rs if not r["det"]))
            per = defaultdict(list)
            for r in rs:
                per[r["profile"]].append(r["pass"])
            worst.append(100 * min(np.mean(v) for v in per.values()))
        if not a12:
            continue
        synth[t] = (np.mean(a12), np.mean(worst))
        print(f"  {t:<12}{np.mean(a12):>8.2f}%{np.mean(a20):>8.2f}%"
              f"{np.mean(miss):>9.1f}{np.mean(worst):>12.2f}%")

    # ── 실촬 코퍼스 A (주 지표) ──
    print(f"\n실촬 코퍼스 A — **주 지표** τ={a.tau} 통과율 (3시드)")
    per_seed, per_id = {}, {}
    for t in ARMS:
        vals, merged = [], []
        for s in SEEDS:
            p = REAL / f"{t}_s{s}.jsonl"
            if not p.exists():
                continue
            d = real_pass(rows(p), a.tau)
            merged.append(d)
            vals.append(100 * np.mean(list(d.values())))
        if not vals:
            continue
        per_seed[t] = vals
        ids = sorted(set().union(*[set(m) for m in merged]))
        # 시드 평균을 장마다 낸다 — 짝 비교의 단위
        per_id[t] = {i: np.mean([m[i] for m in merged if i in m]) for i in ids}
        print(f"  {t:<12} 평균 {np.mean(vals):6.2f}%  "
              f"시드별 {' '.join(f'{v:.2f}' for v in vals)}  "
              f"(퍼짐 {max(vals)-min(vals):.2f}점)")

    print("\n  대조군(bce) 대비 짝 차이 · 95% 부트스트랩(**기종 51그룹** 재표집)")
    verdict = {}
    for t in ARMS[1:]:
        if t not in per_id or "bce" not in per_id:
            continue
        d, lo, hi = boot_delta(per_id["bce"], per_id[t], gmap)
        verdict[t] = (d, lo, hi)
        print(f"  {t:<12} {d:+6.2f}점  [{lo:+.2f}, {hi:+.2f}]")

    # ── 실패 분해 (기전 확인) ──
    print("\n실패 분해 — **기전 확인** (계획 §6.2)")
    print(f"  {'조건':<12}{'sel':>9}{'gt_top':>9}{'gt_best':>9}{'any':>9}")
    dec = {}
    for t in ARMS:
        acc = defaultdict(list)
        for s in SEEDS:
            p = REAL / f"cells_{t}_s{s}.jsonl"
            if not p.exists():
                continue
            rs = rows(p)
            for k in ("sel_ok", "gt_top_ok", "gt_best_ok", "any_ok"):
                acc[k].append(100 * np.mean([r[k] for r in rs]))
        if not acc:
            continue
        dec[t] = {k: np.mean(v) for k, v in acc.items()}
        print(f"  {t:<12}{dec[t]['sel_ok']:>8.1f}%{dec[t]['gt_top_ok']:>8.1f}%"
              f"{dec[t]['gt_best_ok']:>8.1f}%{dec[t]['any_ok']:>8.1f}%")

    # ── 사전 등록한 판정 (§6.1) ──
    print("\n판정 — docs/BAND_EXP_PLAN.md §6.1 (셋 다 만족해야 채택)")
    base12 = synth.get("bce", (0, 0))[0]
    base_worst = synth.get("bce", (0, 0))[1]
    for t in ARMS[1:]:
        if t not in verdict or t not in synth:
            continue
        d, lo, hi = verdict[t]
        c1, c2 = d >= 5.0, lo > 0
        c3 = (base12 - synth[t][0]) <= 1.0
        c4 = (base_worst - synth[t][1]) < 5.0          # §6.4
        print(f"  {t}")
        print(f"    1) 개선 >= +5점          {d:+.2f}점        {'O' if c1 else 'X'}")
        print(f"    2) 부트스트랩 하한 > 0   {lo:+.2f}점        {'O' if c2 else 'X'}")
        print(f"    3) 합성 τ=1.2 하락 <=1점 {base12-synth[t][0]:+.2f}점      "
              f"{'O' if c3 else 'X'}")
        print(f"    4) 프로파일최저 하락 <5점(§6.4) "
              f"{base_worst-synth[t][1]:+.2f}점  {'O' if c4 else 'X'}")
        print(f"    => {'채택' if (c1 and c2 and c3 and c4) else '기각'}")

    if dec:
        print("\n  기전 (§6.2): sel 은 오르고 gt_best 는 거의 안 움직여야 한다")
        for t in ARMS[1:]:
            if t not in dec or "bce" not in dec:
                continue
            ds = dec[t]["sel_ok"] - dec["bce"]["sel_ok"]
            db = dec[t]["gt_best_ok"] - dec["bce"]["gt_best_ok"]
            print(f"    {t:<12} sel {ds:+.1f}점 · gt_best {db:+.1f}점")


if __name__ == "__main__":
    main()
