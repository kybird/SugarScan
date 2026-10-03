# COCO 세트들을 하나로 병합한다 — 이미지 복사 + 주석 id 재매김.
# 사용: python merge_coco_sets.py --sets TG,B2J --out synth_coco/TGB
import argparse, json, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--sets", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
out = HERE / a.out
(out / 'train2017').mkdir(parents=True, exist_ok=True)
imgs, anns, aid = [], [], 0
for name in a.sets.split(','):
    src = HERE / 'synth_coco' / name
    j = json.loads((src / 'annotations' / 'instances_train2017.json').read_text(encoding='utf-8'))
    m = {}
    for im in j['images']:
        nid = len(imgs) + 1
        m[im['id']] = nid
        fn = f"{name}__{im['file_name']}"
        shutil.copy2(src / 'train2017' / im['file_name'], out / 'train2017' / fn)
        imgs.append({**im, 'id': nid, 'file_name': fn})
    for x in j['annotations']:
        aid += 1
        anns.append({**x, 'id': aid, 'image_id': m[x['image_id']]})
    with (out / 'manifest.jsonl').open('a', encoding='utf-8') as f:
        for line in (src / 'manifest.jsonl').read_text(encoding='utf-8').splitlines():
            if line.strip():
                f.write(line + '\n')
(out / 'annotations').mkdir(exist_ok=True)
(out / 'annotations' / 'instances_train2017.json').write_text(
    json.dumps({'images': imgs, 'annotations': anns, 'categories': j['categories']}),
    encoding='utf-8')
print(f"{a.out}: 이미지 {len(imgs)} · 주석 {len(anns)}")
