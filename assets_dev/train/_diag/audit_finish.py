# 감사 미완 3건 측정(2026-10-07 사람: "마지막 측정하려던거 측정 완료하자").
# ① ep65 verdict vs 현재라벨 재채점의 1행 엇갈림 식별
# ② 검출기기원 10장 × 30에폭 전량 오답 검증(misread47_review 예측)
# ③ McNemar — 동일 프로토콜(현재 라벨·회전 7장 제외) 25k vs ep65
import glob
import json
from collections import Counter
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
E2E = HERE / "e2e_bandnet"
cur = {}
for ln in (HERE.parent / ".." / "upstream" / "datumo" / "labels.jsonl").resolve() \
        .read_text(encoding="utf-8").splitlines():
    if ln.strip():
        r = json.loads(ln)
        cur[r["id"]] = str(r.get("reading", ""))
ROT = {"1213", "1226", "1564", "1565", "940", "283", "2411"}


def load(path):
    return {r["id"]: r for r in map(json.loads,
                                    Path(path).read_text(encoding="utf-8").splitlines())}


# ── ① 엇갈림 행 ───────────────────────────────────────────────────────
rows65 = load(E2E / "g2full_ep65.jsonl")
flip = []
for pid, r in rows65.items():
    if pid.split("/")[-1] in ROT:
        continue
    gt = cur.get(pid, "")
    if not gt.isdigit() or r["verdict"] == "det":
        continue
    if r["verdict"] == "skip":
        # 재채점은 skip 을 안 걸렀다 — 이게 57 vs 58 차이의 후보
        print("[①-보류행]", pid, "verdict=skip pred=", r.get("pred"),
              "gt=", gt)
        continue
    ok = r.get("pred") is not None and str(r["pred"]) == gt
    if ok != (r["verdict"] == "right"):
        flip.append((pid, r["verdict"], r.get("pred"), gt))
        print("[엇갈림]", pid, "verdict=", r["verdict"], "pred=", r.get("pred"),
              "현재 gt=", gt)
if not flip:
    print("[①] 채점 행(verdict right/wrong)은 재채점과 완전 일치")

# ── ② 검출기기원 10장 × 30에폭 ────────────────────────────────────────
mr = json.loads((HERE / "misread47_review.json").read_text(encoding="utf-8"))
det_ids = ["glucose_batch1/" + i for i in mr["detector_origin"]["ids"]]
tot = right = absent = 0
by_id = Counter()
for f in sorted(E2E.glob("g2full_ep*.jsonl")):
    rows = load(f)
    for pid in det_ids:
        r = rows.get(pid)
        if r is None:
            absent += 1
            continue
        if r["verdict"] in ("right", "wrong", "det"):
            tot += 1
            if r["verdict"] == "right":
                right += 1
                by_id[pid.split("/")[-1]] += 1
                print("  !! 정답:", f.stem, pid)
print(f"[②] 검출기기원 10장 × 30에폭: 채점 {tot}판정 · 정답 {right} · 행없음 {absent}"
      f" — 예측(전량 오답) {'통과' if right == 0 else '기각'}")

# ── ③ McNemar (동일 프로토콜) ─────────────────────────────────────────
def rescore(path):
    out = {}
    for pid, r in load(path).items():
        if pid.split("/")[-1] in ROT:
            continue
        gt = cur.get(pid, "")
        if not gt.isdigit() or r["verdict"] == "det":
            continue
        out[pid] = r.get("pred") is not None and str(r["pred"]) == gt
    return out


a = rescore(E2E / "gen2lad25000.jsonl")
b = rescore(E2E / "g2full_ep65.jsonl")
common = [k for k in a if k in b]
aw = sum(1 for k in common if not a[k] and b[k])
bw = sum(1 for k in common if a[k] and not b[k])
n = aw + bw
p = min(1.0, 2 * sum(comb(n, i) for i in range(min(aw, bw) + 1)) / 2 ** n)
print(f"[③] 25k 오독 {sum(1 for v in a.values() if not v)} · "
      f"ep65 오독 {sum(1 for v in b.values() if not v)} (짝 n={len(common)})")
print(f"    25k만 틀림 {aw} / ep65만 틀림 {bw} / McNemar exact p={p:.4f}")
