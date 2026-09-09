# G30 — 세로형 밴드 크롭 A/B 보고. 두 팔의 preds json 을 짝지어 비교한다.
#
# 내는 표(지시서가 명시한 것 — 판정은 하지 않는다):
#   1. 완전일치 % / 위험군(자릿수 보존 오독) % / blank / 안전 실패
#   2. McNemar 검정 p값(정확 이항)
#   3. 새로 틀린 장의 id 전체 목록(채택 판단이 여기서 갈린다) + 새로 맞은 장
#   4. 가로형/세로형/회전 제외 층별 정확도 — 가로형은 크롭하지 않으므로
#      기준선과 같아야 한다. 달라지면 형태 판정이나 좌표계가 틀린 것이다.
#      (단 모델이 재학습된 팔이므로 판독 자체는 흔들릴 수 있다 — 프레이밍
#      동일성은 g30_check_cache.py 가 픽셀로 증명한다.)
#
# 사용:
#   python g30_ab_report.py --baseline PREDS.json --bandcrop PREDS.json \
#       [--data-root DIR] [--json OUT.json]
#
# 두 preds json 의 키 집합이 같은지 먼저 검사한다 — 다르면 비교 자체가 무효라
# 그 자리에서 죽는다.
import argparse
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def mcnemar_exact(b: int, c: int) -> float:
    """짝지은 비교의 정확 이항 McNemar p값(양측). b/c 는 각 방향의 일치-불일치.

    n 이 크면 2^n 이 float 범위를 넘는다(G30 스펙 판 비교에서 n=1,102 로
    오버플로) — 로그 공간에서 계산한다. n 이 작을 때는 G29 식과 동치다.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    if 2 * k >= n:
        return 1.0  # 작은쪽 꼬리가 절반 이상이면 양측 p는 1
    logs = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
            for i in range(k + 1)]
    m = max(logs)
    s = m + math.log(sum(math.exp(v - m) for v in logs))
    tail = math.exp(s - n * math.log(2.0))
    return min(1.0, 2.0 * tail)


def classify(pred: str, gt: str) -> str:
    if pred == gt:
        return "exact"
    if pred == "":
        return "blank"
    if len(pred) == len(gt):
        return "risky"
    return "safe"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True, help="기준선 preds.json (A)")
    ap.add_argument("--bandcrop", required=True, help="bandcrop preds.json (B)")
    ap.add_argument("--data-root", type=Path, default=None,
                    help="데이터 루트(기본: 스크립트 폴더) — gmscreen_quads 위치")
    ap.add_argument("--json", type=Path, default=None,
                    help="결과 json 저장 경로(선택)")
    args = ap.parse_args()
    data = args.data_root if args.data_root else HERE

    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    bc = json.loads(Path(args.bandcrop).read_text(encoding="utf-8"))
    keys = sorted(set(base) & set(bc))
    only_b = set(base) - set(bc)
    only_g = set(bc) - set(base)
    if only_b or only_g:
        raise SystemExit(
            f"비교 불가: 평가 집합이 다르다 (기준선에만 {len(only_b)}장, "
            f"bandcrop 에만 {len(only_g)}장) — hold-out 정의가 갈렸다")

    quads = {}
    for l in (data / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j["quad"]
    rotated = set()
    for l in (data / "band_rotation.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            rotated.add(json.loads(l)["id"])

    def form(cid):
        """형태 판정 — 크롭 규칙(build_cache_v2.band_crop_box)과 동일한 판정."""
        if cid in rotated:
            return "회전 제외"
        q = np.asarray(quads[cid], dtype=np.float64)
        w = q[:, 0].max() - q[:, 0].min()
        h = q[:, 1].max() - q[:, 1].min()
        return "가로형" if w > 1.2 * h else "세로형"

    def arm_table(preds):
        tally = {"exact": 0, "risky": 0, "blank": 0, "safe": 0}
        for k in keys:
            tally[classify(preds[k][0], preds[k][1])] += 1
        strat = {}
        for k in keys:
            f = form(k)
            s = strat.setdefault(f, {"n": 0, "exact": 0})
            s["n"] += 1
            if preds[k][0] == preds[k][1]:
                s["exact"] += 1
        return tally, strat

    bt, bs = arm_table(base)
    gt_, gs = arm_table(bc)
    n = len(keys)

    b_only = [k for k in keys
              if base[k][0] != base[k][1] and bc[k][0] == bc[k][1]]
    c_only = [k for k in keys
              if base[k][0] == base[k][1] and bc[k][0] != bc[k][1]]
    p = mcnemar_exact(len(b_only), len(c_only))

    print(f"평가 장수(두 팔 공통): {n}")
    print()
    print("| | 기준선(A·스트레치) | bandcrop(B) |")
    print("|---|---|---|")
    print(f"| 완전일치 | {bt['exact']} ({100*bt['exact']/n:.2f}%) "
          f"| {gt_['exact']} ({100*gt_['exact']/n:.2f}%) |")
    print(f"| 위험군(자릿수 보존 오독) | {bt['risky']} ({100*bt['risky']/n:.2f}%) "
          f"| {gt_['risky']} ({100*gt_['risky']/n:.2f}%) |")
    print(f"| blank(침묵) | {bt['blank']} ({100*bt['blank']/n:.2f}%) "
          f"| {gt_['blank']} ({100*gt_['blank']/n:.2f}%) |")
    print(f"| 안전 실패(자릿수 붕괴) | {bt['safe']} ({100*bt['safe']/n:.2f}%) "
          f"| {gt_['safe']} ({100*gt_['safe']/n:.2f}%) |")
    print()
    print(f"McNemar(정확 이항): 기준선만 틀림 b={len(b_only)}, bandcrop 만 틀림 "
          f"c={len(c_only)}, p={p:.4f}")
    print()
    print("| 층 | 장수 | A 정확도 | B 정확도 |")
    print("|---|---|---|---|")
    for f in ("가로형", "세로형", "회전 제외"):
        if f not in bs and f not in gs:
            continue
        a = bs.get(f, {"n": 0, "exact": 0})
        b_ = gs.get(f, {"n": 0, "exact": 0})
        print(f"| {f} | {a['n']} | {a['exact']}/{a['n']} "
              f"({100*a['exact']/max(a['n'],1):.1f}%) | {b_['exact']}/{b_['n']} "
              f"({100*b_['exact']/max(b_['n'],1):.1f}%) |")

    print()
    print(f"새로 틀린 장(bandcrop 만 틀림) {len(c_only)}:")
    for k in c_only:
        print(f"  {k}  gt={base[k][1]}  A={base[k][0]}  B={bc[k][0]} "
              f"(B agree={bc[k][2] if len(bc[k]) > 2 else '-'})")
    print(f"새로 맞은 장(bandcrop 만 맞음) {len(b_only)}:")
    for k in b_only:
        print(f"  {k}  gt={base[k][1]}  A={base[k][0]}  B={bc[k][0]}")

    if args.json:
        out = {
            "n": n,
            "baseline": {"tally": bt, "strata": bs},
            "bandcrop": {"tally": gt_, "strata": gs},
            "mcnemar": {"b": len(b_only), "c": len(c_only), "p": p},
            "newly_wrong": c_only,
            "newly_right": b_only,
            "wrong": {
                "baseline": sorted(k for k in keys
                                   if base[k][0] != base[k][1]),
                "bandcrop": sorted(k for k in keys if bc[k][0] != bc[k][1]),
            },
        }
        Path(args.json).write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n저장: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
