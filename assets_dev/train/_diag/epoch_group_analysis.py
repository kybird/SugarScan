# 에폭 스윕 군 분석(2026-10-06 사람 제안 "실촬을 몇개의 집단으로 나눠 각 군마다
# 평가") — K=5 기기 층화 군으로:
#   ① 에폭별 전량 곡선 ② 군별 곡선 ③ leave-one-group-out 선택(저주 실측)
#   ④ 강건 선택(군 중앙값·최악군 최대화)
# 장 단위 verdict 행렬(g2full_ep*.jsonl)에서 전부 후처리로 계산한다.
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
E2E = HERE / "_diag" / "e2e_bandnet"
K = 5
ROT = {"1213", "1226", "1564", "1565", "940", "283", "2411"}

dev = {}
for ln in (HERE / "device_labels.jsonl").read_text(
        encoding="utf-8").splitlines():
    if ln.strip():
        r = json.loads(ln)
        key = " ".join(x for x in (r.get("brand"), r.get("model"),
                                   r.get("variant")) if x) or "?"
        dev[r["id"].split("/")[-1]] = key

eps = sorted(int(m.group(1)) for p in E2E.glob("g2full_ep*.jsonl")
             if (m := re.match(r"g2full_ep(\d+)\.jsonl$", p.name)))
assert eps, "g2full_ep*.jsonl 없음"
photos = None
ok = {}          # (ep, photo) -> 1/0
for ep in eps:
    rows = [json.loads(l) for l in
            (E2E / f"g2full_ep{ep}.jsonl").read_text(
                encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows
            if r["id"].split("/")[-1] not in ROT
            and r.get("verdict") not in ("skip", None)]
    if photos is None:
        photos = [r["id"].split("/")[-1] for r in rows]
    else:
        assert [r["id"].split("/")[-1] for r in rows] == photos, "사진 순 불일치"
    for r in rows:
        ok[(ep, r["id"].split("/")[-1])] = 1 if r["verdict"] == "right" else 0

# 기기 층화 K분할: 기기 키 순 정렬(안정) 후 라운드로빈 — 각 군이 모든 기기의
# 사진을 고르게 나눠 가진다.
order = sorted(photos, key=lambda p: (dev.get(p, "?"), p))
grp = {p: i % K for i, p in enumerate(order)}
gphotos = {g: [p for p in photos if grp[p] == g] for g in range(K)}

acc = {ep: np.mean([ok[(ep, p)] for p in photos]) for ep in eps}
gacc = {ep: {g: np.mean([ok[(ep, p)] for p in gphotos[g]]) for g in range(K)}
        for ep in eps}

# ③ leave-one-group-out: 군 g 를 뺀 나머지 평균으로 최적 에폭을 고르고
# 그 에폭을 g 에서 채점 — 선택 절차의 '안 본 사진' 기대치(공정 추정).
loo = []
for g in range(K):
    rest = [np.mean([gacc[ep][h] for h in range(K) if h != g]) for ep in eps]
    pick = eps[int(np.argmax(rest))]
    loo.append(gacc[pick][g])
loo_est = float(np.mean(loo))
full_pick = eps[int(np.argmax([acc[ep] for ep in eps]))]  # acc 는 dict — 리스트로
full_sel = float(acc[full_pick])
rob_med = eps[int(np.argmax([np.median(list(gacc[ep].values()))
                             for ep in eps]))]
rob_worst = eps[int(np.argmax([min(gacc[ep].values()) for ep in eps]))]

out = {
    "n_photos": len(photos), "k_groups": K, "epochs": eps,
    "curve_full": {ep: round(acc[ep], 5) for ep in eps},
    "curve_groups": {ep: {g: round(gacc[ep][g], 5) for g in range(K)}
                     for ep in eps},
    "group_sizes": {g: len(gphotos[g]) for g in range(K)},
    "full_pick": full_pick, "full_selection_score": round(full_sel, 5),
    "loo_estimate": round(loo_est, 5),
    "winners_curse_gap": round(full_sel - loo_est, 5),
    "robust_median_pick": rob_med,
    "robust_worst_pick": rob_worst,
}
(HERE / "_diag" / "epoch_sweep_analysis.json").write_text(
    json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

print(f"사진 {len(photos)}장 · 군 {K}개(기기 층화 라운드로빈) "
      f"· 크기 {out['group_sizes']}")
print("에폭   전량     " + "  ".join(f"군{g}" for g in range(K)))
for ep in eps:
    mark = (" <-전량최고" if ep == full_pick else
            " <-중앙값최고" if ep == rob_med else
            " <-최악군최고" if ep == rob_worst else "")
    print(f"{ep:5d} {acc[ep]*100:6.2f}%  "
          + "  ".join(f"{gacc[ep][g]*100:5.1f}" for g in range(K)) + mark)
print(f"\n전량 선택: ep{full_pick} = {full_sel*100:.2f}%")
print(f"LOO 추정(안 본 사진 기대): {loo_est*100:.2f}%  "
      f"→ 승자의 저주 격차 {out['winners_curse_gap']*100:.2f}pp")
print(f"강건 선택: 중앙값 ep{rob_med} · 최악군 ep{rob_worst}")
