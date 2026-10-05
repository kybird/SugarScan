# -*- coding: utf-8 -*-
"""generic_v1 아이콘 미배치 원인 프로브 — 2026-10-05 GEN2 축 감사 중
generic 판 30장 전부 icon rects 가 0개인 문제. 임시 자."""
import random
import synth_panel as sp

profs = {p['id']: p for p in sp.TRAIN_PROFILES}
gv = profs['generic_v1']
print('generic_v1 icons 선언:', gv.get('icons'))
for i in range(6):
    rng = random.Random(7000 + i)
    s = sp.render_panel(str(120 + i), rng, profile=gv, scene='mixed')
    kinds = [x[4] for x in s['rects']]
    print(f'#{i} rects={kinds} dropped={s.get("dropped")}')
