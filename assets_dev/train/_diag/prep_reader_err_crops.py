# -*- coding: utf-8 -*-
"""순수 리더 오류 35장 개별 분석 준비 — 장별 크롭 파일(2배 확대) + 기계 지표.
지표: 자릿수별 세로 스트립 잉크 강도(p95), 가장 약한 자릿수/중앙 자릿수 비,
위/아래 절반 잉크비. 등분 가정이지만 실촌·합성 양쪽 같은 규칙으로 잰다."""
import json
from pathlib import Path

import cv2
import numpy as np
import torch

from band_net import BandNet, decode
from train_band import letterbox

HERE = Path(__file__).resolve().parent.parent
UP = HERE.parent / 'upstream' / 'datumo' / 'extracted' / 'TILDE'
DIAG = HERE / '_diag'
OUT = DIAG / 'reader_err_each'
OUT.mkdir(exist_ok=True)
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
cd = torch.load(HERE / 'band_out' / 'tone' / 'gen2_v1_step8000',
                map_location='cpu', weights_only=False)
det = BandNet(width=cd['width'], stride=cd.get('stride', 16)).to(dev).eval()
det.load_state_dict(cd['model'])

idx = json.load(open(DIAG / 'pure_err_index.json', encoding='utf-8'))
recs = []
with torch.no_grad():
    for e in idx['reader']:
        pid, n = e['id'], e['n']
        img = cv2.imread(str(UP / (pid + '.jpg')), cv2.IMREAD_GRAYSCALE)
        lb, r_, dx, dy = letterbox(img, cd['size'])
        x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
        obj, reg = det(x.to(dev))
        b, s = decode(obj.float(), reg.float(), det.stride)
        b = b[0].cpu().numpy()
        box = [(b[0] - dx) / r_, (b[1] - dy) / r_,
               (b[2] - dx) / r_, (b[3] - dy) / r_]
        crop = img[max(0, int(box[1])):int(box[3]),
                   max(0, int(box[0])):int(box[2])]
        if not crop.size:
            continue
        fn = OUT / f'{n:02d}_{pid.split("/")[-1]}.png'
        up = cv2.resize(crop, (crop.shape[1] * 2, crop.shape[0] * 2),
                        interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(str(fn), up)

        g = crop.astype(np.float32)
        flat = np.abs(g - cv2.GaussianBlur(g, (0, 0),
                                           max(3.0, crop.shape[0] / 4.0)))
        h, w = flat.shape
        nd = len(str(e['gt']))
        cols = []
        for i in range(nd):
            c = flat[:, int(w * i / nd):max(int(w * (i + 1) / nd),
                                             int(w * i / nd) + 1)]
            cols.append(round(float(np.percentile(c, 95)), 1))
        cols_a = np.array(cols)
        minratio = float(cols_a.min() / max(np.median(cols_a), 1e-6))
        top = float(np.percentile(flat[:h // 2], 95))
        bot = float(np.percentile(flat[h // 2:], 95))
        vert = top / max(bot, 1e-6)
        recs.append({'n': n, 'id': pid, 'gt': e['gt'], 'pred': e['pred'],
                     'file': fn.name, 'digit_cols': cols,
                     'weakest_digit_ratio': round(minratio, 2),
                     'top_bottom_ratio': round(vert, 2)})
json.dump(recs, open(OUT / 'metrics.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'{len(recs)}장 개별 크롭+지표 완료 -> {OUT}')
for r_ in recs[:5]:
    print(r_['n'], r_['id'].split('/')[-1], r_['gt'], '->', r_['pred'],
          '약자리비', r_['weakest_digit_ratio'], '위/아래', r_['top_bottom_ratio'])
