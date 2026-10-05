# -*- coding: utf-8 -*-
"""GEN2 신규 축 예판 — 잘림·경쟁인쇄·큰아이콘·직격반사 각 축의 실제 판을 띄운다.
밴드(초록)·경쟁인쇄(빨강)·아이콘(주황) 상자는 워프 후 이미지 좌표(quad)와
매니페스트 rects(워프 전)라 좌표계가 다르다 — rects 는 그리지 않고 축 플래그로
판만 골라 전체를 보여준다(검출기 시점). 2026-10-05 GEN2 축 반영 검수 자."""
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent.parent
GEN = HERE / 'synth_coco' / 'GEN2P'
DIAG = HERE / '_diag'

rows = [json.loads(l) for l in (GEN / 'manifest.jsonl').read_text(
    encoding='utf-8').splitlines() if l.strip()]


def band_of(r):
    b = r.get('box')
    return b


def big_icon(r):
    band = [x for x in r['rects'] if x[4] == 'band']
    if not band:
        return False
    bh = band[0][3] - band[0][1]
    return any(x[4].startswith('icon:')
               and (x[3] - x[1]) / max(bh, 1e-6) >= 0.55
               for x in r['rects'])


groups = [
    ('CLIP (밴드가 프레임에 잘림)', [r for r in rows if r.get('clip_shot')]),
    ('COMP PRINT (큰 비숫자 인쇄)', [r for r in rows if r.get('comp_print')]),
    ('BIG ICON (숫자급 픽토그램)', [r for r in rows if big_icon(r)]),
    ('BAND REFLECT (직격 반사)', [r for r in rows if r.get('band_reflect')][:6]),
]
CW, CH, PAD = 360, 300, 8
for title, sel in groups:
    if not sel:
        print(f'{title}: 판 0개 — 스킵')
        continue
    cols = min(4, len(sel))
    rws = (len(sel) + cols - 1) // cols
    sheet = np.full((rws * (CH + 26 + PAD) + PAD,
                     cols * (CW + PAD) + PAD, 3), 24, np.uint8)
    for k, r in enumerate(sel[:cols * rws]):
        img = cv2.imread(str(GEN / 'train2017' / (r['id'] + '.png')))
        if img is None:
            continue
        h, w = img.shape[:2]
        s = min(CW / w, CH / h)
        im = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))))
        b = r['box']
        p1 = (int(b[0] * s), int(b[1] * s))
        p2 = (int(b[2] * s), int(b[3] * s))
        cv2.rectangle(im, p1, p2, (80, 220, 80), 2)
        cell = np.zeros((CH + 26, CW, 3), np.uint8)
        yy, xx = (CH - im.shape[0]) // 2, (CW - im.shape[1]) // 2
        cell[26 + yy:26 + yy + im.shape[0], xx:xx + im.shape[1]] = im
        cv2.putText(cell, r['id'].replace('panel_20261203_', '#'),
                    (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1, cv2.LINE_AA)
        rr, cc = divmod(k, cols)
        y0 = PAD + rr * (CH + 26 + PAD)
        x0 = PAD + cc * (CW + PAD)
        sheet[y0:y0 + CH + 26, x0:x0 + CW] = cell
    out = DIAG / f'gen2_axes_{title.split()[0].lower()}.png'
    cv2.imwrite(str(out), sheet)
    print(f'{title}: {len(sel)}판 -> {out.name}')
