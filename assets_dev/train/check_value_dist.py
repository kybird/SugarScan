# sample_value 값당 균등 전환(2026-10-25 사람 결정) 검증 — 10만 회 실측.
# 기대: 구간별 비중이 값 개수 비례(30~99 70/570=12.28%, 1xx~5xx 각 100/570=17.54%).
import collections
import random
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synth_panel import sample_value

N = 100_000
rng = random.Random(20261025)
c = collections.Counter(sample_value(rng) for _ in range(N))
bins = [(30, 100), (100, 200), (200, 300), (300, 400), (400, 500), (500, 600)]
print(f"n={N}  distinct values={len(c)}  min={min(c)}  max={max(c)}")
for lo, hi in bins:
    k = hi - lo
    n = sum(c[v] for v in range(lo, hi))
    obs = n / N
    exp = k / 570
    flag = "OK " if abs(obs - exp) < 0.005 else "!! "
    print(f"{flag}{lo:3d}~{hi-1:3d}: {obs*100:5.2f}% (기대 {exp*100:5.2f}%)  n={n}")
