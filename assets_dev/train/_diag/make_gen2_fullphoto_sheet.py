# -*- coding: utf-8 -*-
"""검출기 시점(전체 사진 규모) 실촬 vs 합성 병치판 — 평탄화 잉크 폭 자로 짝짓기.

2026-10-04 사람 지적: "검출오류 이야기하는데 리더기 인식화면을 왜가져오나" —
밴드 확대 크롭이 아니라 사진 전체 배율로 보여야 한다. 같은 날 시각 검증으로
기존 Otsu 이분범 자가 직격 그림자 패널에서 그림자 깊이를 재고 있었음이
확인됐다(짝지은 합성이 실촬보다 눈에 확실히 더 읽힘). 이 판은 국소 조명을
평탄화한 뒤의 잉크 편차 폭(flat-span)으로 다시 짝짓는다.

실촬 밴드 상자: atone_tg640w15 전량 덤프(TG 가 잡은 장) → gen1 프로브 폴백.
"""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent.parent
DIAG = HERE / '_diag'
UP = HERE.parent / 'upstream' / 'datumo' / 'extracted' / 'TILDE'
GEN2P = HERE / 'synth_coco' / 'GEN2P'

REAL = ['501', '2319', '498', '728', '525', '1710']
ROW_H = 300          # 각 행 높이(px) — 전체 사진 배율 유지
GAP = 6


def flat_ink_span(crop):
    """국소 조명 평탄화 뒤 잉크 편차 폭 — 그림자·조명 기울기에 강한 대비 자.

    큰 시그마 가우시안으로 배경 조명을 추출해 빼면 그림자 경계는 사라지고
    숫자 잉크의 국소 편차만 남는다. Otsu 이분범은 그림자 패널에서 이분점이
    그림자 경계로 이동해 "숫자 대비"가 아니라 "그림자 깊이"를 재는다.
    """
    g = crop.astype(np.float32)
    sig = max(3.0, crop.shape[0] / 6.0)
    flat = g - cv2.GaussianBlur(g, (0, 0), sig)
    return float(np.percentile(flat, 95) - np.percentile(flat, 5))


def photo(pid):
    for p in (UP / (pid.replace('/', os.sep) + '.jpg'), UP / (pid + '.jpg')):
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            return img
    raise SystemExit(f'사진 없음: {pid}')


def aabb(q):
    xs = [p[0] for p in q]
    ys = [p[1] for p in q]
    return min(xs), min(ys), max(xs), max(ys)


def band_boxes():
    boxes = {}
    for ln in (HERE / 'band_quads_pred_tg640w15_20261004.jsonl').read_text(
            encoding='utf-8').splitlines():
        if ln.strip():
            r = json.loads(ln)
            boxes[r['id']] = aabb(r['quad'])
    for f in ('fail19_raw_probe_gen1.json', 'fail19_raw_probe_gen1new.json'):
        p = DIAG / f
        if not p.exists():
            continue
        for r in json.loads(p.read_text(encoding='utf-8')):
            if 'box' in r and r['id'] not in boxes:
                boxes[r['id']] = r['box']
    return boxes


def fit_h(img, h):
    w = max(1, round(img.shape[1] * h / img.shape[0]))
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


def caption(w, text, bg):
    bar = np.full((26, w, 3), bg, np.uint8)
    cv2.putText(bar, text, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.52,
                (255, 255, 255), 1, cv2.LINE_AA)
    return bar


def main():
    boxes = band_boxes()

    real_vals, real_imgs = {}, {}
    for i in REAL:
        pid = 'glucose_batch1/' + i
        x0, y0, x1, y1 = boxes[pid]
        img = photo(pid)
        crop = img[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1)]
        real_vals[i] = flat_ink_span(crop)
        real_imgs[i] = img

    synth = []
    for ln in (GEN2P / 'manifest.jsonl').read_text(encoding='utf-8').splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        img = cv2.imread(str(GEN2P / 'train2017' / (r['id'] + '.png')),
                         cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        b = r['box']
        crop = img[int(b[1]):int(b[3]), int(b[0]):int(b[2])]
        synth.append({'id': r['id'], 'img': img, 'flat': flat_ink_span(crop),
                      'c': r.get('c_deg'), 'sh': r.get('band_shadow', 0)})

    rows = []
    print('== 평탄화 자 짝짓기 ==')
    for i in REAL:
        tgt = real_vals[i]
        best = min(synth, key=lambda s: abs(s['flat'] - tgt))
        print(f'REAL {i:>5} flat {tgt:5.1f}  <-  SYNTH {best["id"]} '
              f'flat {best["flat"]:5.1f} (lowc c={best["c"]:.2f}, '
              f'shadow={best["sh"]})')
        rows.append((i, tgt, best))

    W = max(fit_h(real_imgs[i], ROW_H).shape[1] for i in REAL) + \
        max(fit_h(s['img'], ROW_H).shape[1] for s in synth) + GAP * 3
    H = ROW_H + 26 + GAP
    sheet = np.zeros((H * len(rows) + GAP, W, 3), np.uint8)
    for k, (i, tgt, s) in enumerate(rows):
        y = GAP + k * H
        rl = fit_h(real_imgs[i], ROW_H)
        sl = fit_h(s['img'], ROW_H)
        lc = caption(rl.shape[1], f'REAL {i}  flat {tgt:.0f}', (200, 120, 40))
        rc = caption(sl.shape[1],
                     f'SYNTH {s["id"]}  flat {s["flat"]:.0f}  '
                     f'c={s["c"]:.2f} shadow={s["sh"]}', (60, 150, 60))
        cell = np.zeros((ROW_H + 26, W, 3), np.uint8)
        cell[26:26 + ROW_H, 0:rl.shape[1]] = cv2.cvtColor(rl, cv2.COLOR_GRAY2BGR)
        cell[0:26, 0:rl.shape[1]] = lc
        x1 = rl.shape[1] + GAP
        cell[26:26 + ROW_H, x1:x1 + sl.shape[1]] = cv2.cvtColor(sl, cv2.COLOR_GRAY2BGR)
        cell[0:26, x1:x1 + sl.shape[1]] = rc
        sheet[y:y + ROW_H + 26, :] = cell
    out = DIAG / 'gen2_fullphoto_real_vs_synth.png'
    cv2.imwrite(str(out), sheet)
    if not (out.stat().st_mtime > 0):
        raise SystemExit('imwrite 실패(파일 잠금?)')
    small = cv2.resize(sheet, (1600, round(sheet.shape[0] * 1600 / sheet.shape[1])),
                       interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(DIAG / 'gen2_fullphoto_real_vs_synth_s.jpg'), small,
                [cv2.IMWRITE_JPEG_QUALITY, 87])
    print('작성:', out)


if __name__ == '__main__':
    sys.exit(main())
