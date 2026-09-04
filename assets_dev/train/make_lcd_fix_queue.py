# LCD 재라벨링 큐 — GM 검출이 실패했거나 실패했을 법한 장을 모은다.
#
# 왜 이 기준인가 (2026-09-04 holdout 1,122장 실측):
#   GM 박스 w/h > 1.5  → 판독 정확도 14.3% (14장 중 12장 오답)
#   GM 박스 w/h 1.1~1.5 → 62.5%
#   GM 박스 w/h < 1.1  → 94~95%
#   GM score 0.5~0.7   → 37.5%     score 0.95+ → 96.4%
# 즉 '가로로 잡힌 박스'와 '낮은 confidence'가 실패를 예측한다. 눈으로 보면
# 가로 화면에서 GM 이 시간줄·단위 블록만 잡는 경우가 있다(1593·1596·1614).
#
# **테스트용을 반드시 남긴다.** 후보를 전부 라벨링해 GM 을 재학습하면 개선을
# 잴 데가 없어진다. holdout 은 라벨링 큐에서 빠지고 파일로 고정된다 —
# 판독 정확도로 평가하므로 holdout 에는 라벨이 필요 없다(GT 값만 있으면 된다).
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
Q_OUT = HERE / "lcd_fix_queue.json"
H_OUT = HERE / "lcd_fix_holdout.json"

AR_WIDE = 1.1          # 이 위는 판독 정확도가 62.5% 이하로 떨어진다
SCORE_LOW = 0.85       # 이 아래는 88% 이하
HOLDOUT_FRAC = 0.30
SEED = 20260904


def load(p, key="quad"):
    d = {}
    if not Path(p).exists():
        return d
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            d[j["id"]] = j
    return d


def main() -> int:
    gm = load(HERE / "gmscreen_quads.jsonl")
    scr = load(HERE / "screen_boxes.jsonl")
    readings = load(DATUMO / "labels.jsonl")

    labeled = {c for c, v in scr.items() if v.get("quad")}
    cands = []
    for cid in sorted(readings):
        if cid in labeled:
            continue                      # 이미 사람 박스가 있다 — 다시 그릴 이유 없음
        if not (DATUMO / "extracted" / "TILDE" / f"{cid}.jpg").exists():
            continue
        j = gm.get(cid)
        if j is None:
            cands.append((cid, "gm_miss", "GM 이 박스를 못 냈다"))
            continue
        a = np.array(j["quad"], float)
        ar = a[:, 0].ptp() / max(a[:, 1].ptp(), 1e-6)
        sc = float(j["score"])
        if ar > AR_WIDE:
            cands.append((cid, "wide", f"GM 박스 가로 w/h={ar:.2f} (판독 62%↓ 구간)"))
        elif sc < SCORE_LOW:
            cands.append((cid, "lowconf", f"GM score={sc:.2f} (판독 88%↓ 구간)"))

    # 층별로 같은 비율을 테스트용으로 뗀다. 층을 무시하고 섞어 뽑으면
    # gm_miss 18장 같은 작은 층이 통째로 한쪽에 몰린다.
    rng = np.random.RandomState(SEED)
    queue, holdout = [], []
    for stratum in ("gm_miss", "wide", "lowconf"):
        rows = [c for c in cands if c[1] == stratum]
        idx = rng.permutation(len(rows))
        n_hold = int(round(len(rows) * HOLDOUT_FRAC))
        for k, i in enumerate(idx):
            (holdout if k < n_hold else queue).append(rows[i])

    order = {"gm_miss": 0, "wide": 1, "lowconf": 2}
    queue.sort(key=lambda r: (order[r[1]], r[0]))
    holdout.sort(key=lambda r: (order[r[1]], r[0]))

    Q_OUT.write_text(json.dumps(
        [{"id": c, "stratum": s, "note": n} for c, s, n in queue],
        ensure_ascii=False, indent=1), encoding="utf-8")
    H_OUT.write_text(json.dumps(
        [{"id": c, "stratum": s, "note": n} for c, s, n in holdout],
        ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter
    cq, ch = Counter(r[1] for r in queue), Counter(r[1] for r in holdout)
    print(f"후보 {len(cands)}장 (이미 라벨된 {len(labeled)}장 제외)")
    print(f"  라벨링 큐 {len(queue)}장 → {Q_OUT.name}")
    for k in order:
        print(f"    {k:8s} {cq[k]}")
    print(f"  테스트 holdout {len(holdout)}장 → {H_OUT.name}  (라벨링하지 않는다)")
    for k in order:
        print(f"    {k:8s} {ch[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
