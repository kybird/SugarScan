# -*- coding: utf-8 -*-
"""comp_print 미발화 원인 프로브 — green_doctor(항상)·generic_v1(뽑기) 각각
강제 렌더해 상단 여백·플레이서 결과를 본다. 2026-10-05 GEN2 축 감사 중
comp_print 1/300(기대 ~17/300) 원인 조사용. 임시 자."""
import random
import synth_panel as sp

profs = {p['id']: p for p in sp.TRAIN_PROFILES}
print('TRAIN_PROFILES:', sorted(profs))
gd = profs.get('green_doctor')
gv = profs.get('generic_v1')
print('green_doctor:', gd is not None, '· generic_v1:', gv is not None)


def probe(pid, n=30):
    hit = 0
    margins = []
    for i in range(n):
        rng = random.Random(1000 + i)
        s = sp.render_panel(str(100 + i), rng, profile=profs[pid],
                            scene='mixed')
        if s.get('comp_print'):
            hit += 1
        band = [x for x in s['rects'] if x[4] == 'band']
        gq = s.get('glass_quad')
        if band and gq is not None:
            py0 = min(p[1] for p in gq)
            margins.append(band[0][1] - py0)
    if margins:
        m = sorted(margins)
        print(f'{pid}: comp_print {hit}/{n} · band_top-py0 '
              f'min {m[0]:.0f} 중앙 {m[len(m)//2]:.0f} max {m[-1]:.0f}px')
    else:
        print(f'{pid}: comp_print {hit}/{n} · band/glass 없음?')


if gd:
    probe('green_doctor')
if gv:
    probe('generic_v1')
