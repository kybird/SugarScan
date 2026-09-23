# 리더 잔여 오독 분해 자 — 카드 '리더 잔여 오독 31장을 프레이밍 어긋남과 실제
# 잘림으로 가른다'(2026-09-22). 눈으로 추측하지 않는다 — 조인으로 분류한다.
#
# 조인: tone2te 상자 jsonl(_diag/tone2te/ve_tone2te_s*.jsonl — det·pass·
# area_ratio·iou·gt) × 리더 B 덤프(_diag/reader_dump/VE_B_tone2te_s*.jsonl —
# label·pred·ok) × GT 덤프(VE_B_gt — 같은 장을 정답 상자로 읽었는가).
#
# 분류(오독 장마다):
#   contains  상자가 숫자칸(digit_box)을 온전히 담았나 — 프레이밍 어긋남(리더
#             처방 후보) vs 실제 잘림(검출기 처방 후보)의 이분
#   자릿수 붕괴  len(pred) != len(label) — 상자가 숫자를 걸치거나 밀었다는 신호
#   값 오독     자릿수는 같고 숫자가 틀림
#   GT에서도 오독  B_gt 가 같은 장을 못 읽으면 상자가 아니라 리더·화소 몫
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BOXD = HERE / "_diag" / "tone2te"
RDD = HERE / "_diag" / "reader_dump"


def load(p):
    return {r["file_name"]: r for r in
            (json.loads(l) for l in
             Path(p).read_text(encoding="utf-8").splitlines() if l.strip())}


def ctr_off(p, g):
    """중심 이동 — 정답 밴드 크기로 정규화한 예측 밴드 중심의 어긋남(가로·세로 %)."""
    dx = abs((p[0] + p[2]) / 2 - (g[0] + g[2]) / 2) / max(1.0, g[2] - g[0])
    dy = abs((p[1] + p[3]) / 2 - (g[1] + g[3]) / 2) / max(1.0, g[3] - g[1])
    return 100 * dx, 100 * dy


def main() -> int:
    gt = load(RDD / "VE_B_gt.jsonl")
    gt_bad = {f for f, r in gt.items() if not r["ok"]}
    print(f"[천장] GT 상자 오독(리더·화소 몫): B {len(gt_bad)}장 — "
          f"tone2te 오독 중 이 장들은 상자를 고쳐도 안 읽힌다")

    rows = []
    per_seed = {}
    for s in range(4):
        bx = load(BOXD / f"ve_tone2te_s{s}.jsonl")
        rd = load(RDD / f"VE_B_tone2te_s{s}.jsonl")
        bad = [f for f, r in rd.items() if not r["ok"]]
        per_seed[s] = bad
        for f in bad:
            b = bx[f]
            ox, oy = ctr_off(b["pred"], b["gt"])
            rows.append({
                "seed": s, "file": f, "label": rd[f]["label"],
                "pred": rd[f]["pred"],
                "collapse": len(rd[f]["pred"]) != len(rd[f]["label"]),
                "contains": b["pass"], "area_ratio": b["area_ratio"],
                "iou": b["iou"], "off_x": ox, "off_y": oy,
                "gt_bad": f in gt_bad,
            })

    print(f"\n[오독 표 — 시드별 전체] s0 {len(per_seed[0])} · s1 {len(per_seed[1])}"
          f" · s2 {len(per_seed[2])} · s3 {len(per_seed[3])}장")
    print(f"{'seed':>4} {'파일':<26} {'값':>4} {'오독':>5} {'자릿':>4} "
          f"{'담음':>4} {'면적비':>6} {'IoU':>5} {'중심x%':>6} {'GT오독':>5}")
    for r in sorted(rows, key=lambda r: (r["gt_bad"], not r["contains"])):
        print(f"{r['seed']:>4} {r['file'][:24]:<26} {r['label']:>4} "
              f"{r['pred']:>5} {'붕괴' if r['collapse'] else '값':>4} "
              f"{'✓' if r['contains'] else '✗':>4} {r['area_ratio']:>6.2f} "
              f"{r['iou']:>5.2f} {r['off_x']:>6.1f} "
              f"{'예' if r['gt_bad'] else '-':>5}")

    print("\n[요약 — s0 기준 31장]")
    s0 = [r for r in rows if r["seed"] == 0]
    contains = sum(r["contains"] for r in s0)
    print(f"  담았다(프레이밍 어긋남 · 리더 지터 후보): {contains}장")
    print(f"  못 담았다(실제 잘림 · 검출기 처방): {len(s0)-contains}장")
    print(f"  자릿수 붕괴: {sum(r['collapse'] for r in s0)}장 · "
          f"값 오독: {sum(not r['collapse'] for r in s0)}장")
    print(f"  GT 상자로도 오독(천장 몫): {sum(r['gt_bad'] for r in s0)}장")

    print("\n[지터 스펙 근거 — tone2te 상자 오차 분포(전체 1000×4시드)]")
    ars, oxs, oys = [], [], []
    for s in range(4):
        bx = load(BOXD / f"ve_tone2te_s{s}.jsonl")
        for b in bx.values():
            if b["det"]:
                ars.append(b["area_ratio"])
                ox, oy = ctr_off(b["pred"], b["gt"])
                oxs.append(ox)
                oys.append(oy)
    q = lambda v, p: f"{np.percentile(v, p):.2f}"
    print(f"  면적비  p10 {q(ars,10)} · p50 {q(ars,50)} · p90 {q(ars,90)} · "
          f"p99 {q(ars,99)}")
    print(f"  중심이동(가로%) p50 {q(oxs,50)} · p90 {q(oxs,90)} · p99 {q(oxs,99)}")
    print(f"  중심이동(세로%) p50 {q(oys,50)} · p90 {q(oys,90)} · p99 {q(oys,99)}")
    s0ar = [r["area_ratio"] for r in s0]
    print(f"  (참고) s0 오독 31장의 면적비 p50 {np.percentile(s0ar,50):.2f} · "
          f"p90 {np.percentile(s0ar,90):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
