# -*- coding: utf-8 -*-
"""GEN2P 신규 축 감사 — 분포(그림자·반사·경쟁인쇄·잘림)·잘림 가시 면적·
경쟁인쇄 높이 비·프로파일별 발화. 2026-10-05 GEN2 축 반영 검수 자."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
GEN = HERE / 'synth_coco' / 'GEN2P'

rows = [json.loads(l) for l in (GEN / 'manifest.jsonl').read_text(
    encoding='utf-8').splitlines() if l.strip()]
n = len(rows)
for k in ('band_shadow', 'band_reflect', 'comp_print', 'clip_shot'):
    c = sum(1 for r in rows if r.get(k))
    print(f'{k:13s}: {c:3d}/{n} ({c / n * 100:.1f}%)')

cl = [r for r in rows if r.get('clip_shot')]
for r in cl:
    b = r['box']
    W, H = r['w'], r['h']
    touch = (b[0] <= 0.5) + (b[1] <= 0.5) + (b[2] >= W - 1.5) + (b[3] >= H - 1.5)
    ar = (b[2] - b[0]) / max(b[3] - b[1], 1e-6)
    print(f'  clip {r["id"]}: 접촉변={touch} AR={ar:.2f}')

cp = []
for r in rows:
    band = [x for x in r['rects'] if x[4] == 'band']
    p = [x for x in r['rects'] if x[4] == 'comp_print']
    if band and p:
        bh = band[0][3] - band[0][1]
        cp.append((p[0][3] - p[0][1]) / max(bh, 1e-6))
if cp:
    cp = np.array(cp)
    print(f'comp_print 높이/숫자높이: min {cp.min():.2f} · '
          f'중앙 {np.median(cp):.2f} · max {cp.max():.2f} (n={len(cp)})')
print('comp_print 프로파일:', Counter(r['profile'] for r in rows
                                      if r.get('comp_print')))
print('clip_shot 프로파일:', Counter(r['profile'] for r in rows
                                     if r.get('clip_shot')))
