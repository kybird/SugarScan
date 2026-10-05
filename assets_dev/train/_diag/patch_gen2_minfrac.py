# -*- coding: utf-8 -*-
"""GEN2 COCO 에서 사람 GT 최소 면적비(0.0367) 밑 라벨을 이미지째 제외한다.

2026-10-05 — MIN_BAND_FRAC 게이트가 유리-프레임 접촉으로 확대 여유가 없는
구도 122판(0.4%)을 놓쳤다(전수 감사: 최소 0.0104). 라벨만 빼면 '보이는
밴드=배경' 거짓 음성을 가르치므로 이미지+주석을 함께 뺀다. 원본 json 은
_diag 에 백업. 렌더러 쪽 근본 수습(한 단계 더 물러나 치고 확대)은 다음
세대 굽기에 반영한다."""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
GEN = HERE / 'synth_coco' / 'GEN2'
DIAG = HERE / '_diag'
MIN = 0.0367

p = GEN / 'annotations' / 'instances_train2017.json'
bak = DIAG / 'instances_train2017.pre_minfrac_20261005.json.bak'
if not bak.exists():
    shutil.copy2(p, bak)
    print('원본 백업:', bak.name)

j = json.loads(p.read_text(encoding='utf-8'))
imgs = {im['id']: im for im in j['images']}
drop_ids = set()
keep_ann = []
for a in j['annotations']:
    im = imgs.get(a['image_id'])
    if im is None:
        continue
    x, y, w, h = a['bbox']
    if w * h / (im['width'] * im['height']) < MIN:
        drop_ids.add(im['id'])
        continue
    keep_ann.append(a)
keep_imgs = [im for im in j['images'] if im['id'] not in drop_ids]
j['images'] = keep_imgs
j['annotations'] = keep_ann
p.write_text(json.dumps(j), encoding='utf-8')
print(f'제외 이미지 {len(drop_ids)} · 남은 이미지 {len(keep_imgs)} · '
      f'남은 상자 {len(keep_ann)}')
