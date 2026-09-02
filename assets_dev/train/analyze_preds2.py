# 후속 정량 — 예측 길이 분포·최빈 예측열·위치별 정확도 (analyze_preds.py 보충)
import json
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PREDS = HERE / "reader_preds.json"
LABELS = HERE / ".." / ".." / "assets_dev" / "upstream" / "datumo" / "labels.jsonl"

preds = json.loads(PREDS.read_text(encoding="utf-8"))
meta = {}
for ln in LABELS.read_text(encoding="utf-8").splitlines():
    if ln.strip():
        d = json.loads(ln)
        meta[d["id"]] = int(d["reading"])

rows = [(c, str(meta[c]), p) for c, (p, _g) in preds.items() if c in meta]
n = len(rows)

print("== 예측 길이 분포 (GT는 30~511 → 2~3자리) ==")
pl = Counter(len(p) for _, g, p in rows)
gl = Counter(len(g) for _, g, p in rows)
for L in sorted(set(list(pl) + list(gl))):
    print(f"  len {L}: pred {pl.get(L, 0):4d} | gt {gl.get(L, 0):4d}")
long_n = sum(v for k, v in pl.items() if k >= 4)
print(f"  → 4자리 이상 예측(화면의 다른 숫자까지 읽음): {long_n} ({100 * long_n / n:.1f}%)")
short_n = sum(v for k, v in pl.items() if k == 1)
print(f"  → 1자리 예측(자리 탈락): {short_n} ({100 * short_n / n:.1f}%)")

print("")
print("== 최빈 예측 문자열 top 15 (오답만) ==")
wrong = [p for _, g, p in rows if p != g]
for s, c in Counter(wrong).most_common(15):
    print(f"  {s!r}: {c}")

print("")
print("== 위치별 글자 정확도 (같은 길이 오류 대상) ==")
pos_tot, pos_ok = Counter(), Counter()
for _, g, p in rows:
    if p == g:
        for i, ch in enumerate(g):
            pos_tot[i] += 1
            pos_ok[i] += 1
    elif len(p) == len(g):
        for i, (a, b) in enumerate(zip(g, p)):
            pos_tot[i] += 1
            pos_ok[i] += (a == b)
for i in sorted(pos_tot):
    print(f"  {i + 1}번째 자리: {pos_ok[i]}/{pos_tot[i]} = {100 * pos_ok[i] / pos_tot[i]:.1f}%")

print("")
print("== 혼동 행렬 요약 (같은 길이 오류, 위치 무관 pairwise) ==")
cm = Counter()
for _, g, p in rows:
    if p != g and len(p) == len(g):
        for a, b in zip(g, p):
            if a != b:
                cm[(a, b)] += 1
for (a, b), c in cm.most_common(15):
    print(f"  GT {a} → pred {b}: {c}")

print("")
print("== rect 픽셀 통계 (캐시, 밝기 분포 — 어두운/쓰레기 rect 추정) ==")
cache = np.load(str(HERE / "data_cache_v2.npz"))
X = cache["real_holdout_images"]
mean_b = X.mean(axis=(1, 2))
dark = np.sum(mean_b < 60)
print(f"  holdout {len(X)}장 중 평균 밝기 <60 (검은 프레임류): {dark} ({100 * dark / len(X):.1f}%)")
std_b = X.std(axis=(1, 2))
flat = np.sum(std_b < 20)
print(f"  표준편차 <20 (질감·무패턴 류): {flat} ({100 * flat / len(X):.1f}%)")
