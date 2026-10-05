# -*- coding: utf-8 -*-
"""GEN2 검출기 문제장 판 — step8000(추천) 기준.

A구획: 8k 에서 게이트(0.25)를 못 넘는 3장(잔여 실패) — 게이트 전 최상위
상자가 어디로 갔는지. B구획: 최종 16k 에서만 실패하는 6장 — 8k 에서는
0.27~0.81 로 제대로 잡는다는 증거(과적합 회귀).
주황 상자=프로브 최상위 상자(게이트 전)·초록=참조 밴드(사람 GT 우선,
없으면 tg 덤프). 2026-10-05 사람 요청 "검출기 쪽 문제 이미지 확인시켜줘"."""
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent.parent
UP = HERE.parent / 'upstream' / 'datumo' / 'extracted' / 'TILDE'
DIAG = HERE / '_diag'

A = ['1226', '1565', '2317']            # 8k 잔여 실패
B = ['1091', '1564', '81', '1709', '283', '940']   # 16k 에서만 실패

probe = {r['id'].split('/')[-1]: r
         for r in json.loads((DIAG / 'fail19_raw_probe_gen2s8k.json')
                             .read_text(encoding='utf-8'))}


def aabb(q):
    xs = [p[0] for p in q]
    ys = [p[1] for p in q]
    return min(xs), min(ys), max(xs), max(ys)


gt = {}
for ln in (HERE / 'band_boxes.jsonl').read_text(encoding='utf-8').splitlines():
    if ln.strip():
        r = json.loads(ln)
        gt[r['id'].split('/')[-1]] = aabb(r['quad'])
tg = {}
for ln in (HERE / 'band_quads_pred_tg640w15_20261004.jsonl').read_text(
        encoding='utf-8').splitlines():
    if ln.strip():
        r = json.loads(ln)
        tg[r['id'].split('/')[-1]] = aabb(r['quad'])

CW, CH, PAD, COLS = 480, 400, 10, 3


def draw(ids, title, out):
    rows = (len(ids) + COLS - 1) // COLS
    sheet = np.full((30 + rows * (CH + 26 + PAD) + PAD,
                     COLS * (CW + PAD) + PAD, 3), 24, np.uint8)
    cv2.putText(sheet, title, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                (255, 255, 255), 1, cv2.LINE_AA)
    for k, i in enumerate(ids):
        img = cv2.imread(str(UP / f'glucose_batch1/{i}.jpg'))
        if img is None:
            continue
        h, w = img.shape[:2]
        s = min(CW / w, CH / h)
        im = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))))
        p = probe[i]
        x0, y0, x1, y1 = p['box']
        cv2.rectangle(im, (int(x0 * s), int(y0 * s)),
                      (int(x1 * s), int(y1 * s)), (60, 140, 255), 3)
        ref = gt.get(i) or tg.get(i)
        if ref:
            cv2.rectangle(im, (int(ref[0] * s), int(ref[1] * s)),
                          (int(ref[2] * s), int(ref[3] * s)), (90, 220, 90), 2)
        cell = np.zeros((CH + 26, CW, 3), np.uint8)
        yy, xx = (CH - im.shape[0]) // 2, (CW - im.shape[1]) // 2
        cell[26 + yy:26 + yy + im.shape[0], xx:xx + im.shape[1]] = im
        lab = (f'#{i}  sc {p["score"]:.2f}  frac {p["frac"] * 100:.0f}%'
               + ('' if i in gt else '  (ref=tg)'))
        cv2.putText(cell, lab, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 1, cv2.LINE_AA)
        rr, cc = divmod(k, COLS)
        y0c = 30 + PAD + rr * (CH + 26 + PAD)
        x0c = PAD + cc * (CW + PAD)
        sheet[y0c:y0c + CH + 26, x0c:x0c + CW] = cell
    cv2.imwrite(str(out), sheet)
    small = cv2.resize(sheet, (1400, round(sheet.shape[0] * 1400
                                           / sheet.shape[1])),
                       interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out).replace('.png', '_s.jpg'), small,
                [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('작성:', out.name)


draw(A, 'A. step8000 residuals (gate 0.25 not passed) — orange: top box before gate / green: reference band',
     DIAG / 'gen2_detfail_A_s8k.png')
draw(B, 'B. 16k-only regressions — same photos at step8000 (all passed)',
     DIAG / 'gen2_detfail_B_s8k.png')
