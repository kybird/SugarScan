# 합성 코퍼스 밴드 대비 분포 — 실측(real_baseline.json polarity)과 같은 자로.
# 자: 밴드 영역 grayscale p95−p5(measure_polarity.polarity_of 와 동일 식).
# 사람 관찰(2026-10-04 "실화면은 대비가 거의 없는 것도 있다")을 축 설계 전에
# 측정으로 확인한다 — 현재 합성의 저대비 꼬리가 실측(min 27 · <40 0.72%)
# 에 못 미치는지가 설계 전제다.
# 사용: python _diag/measure_synth_contrast.py [세트이름=master] [샘플수=600]
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent.parent
SET = (sys.argv[1] if len(sys.argv) > 1 else "Gmaster").replace("_", "")
N = int(sys.argv[2]) if len(sys.argv) > 2 else 600

root = HERE / "synth_coco" / ("Gmaster" if SET == "Gmaster" else SET)
rows = [json.loads(l) for l in open(root / "manifest.jsonl", encoding="utf-8")]
random.Random(7).shuffle(rows)
rows = rows[:N]

vals = []
for r in rows:
    p = root / "train2017" / (r["id"] + ".png")
    if not p.exists():
        continue
    img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue
    x0, y0, x1, y1 = r["box"]
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(img.shape[1], int(x1)), min(img.shape[0], int(y1))
    if x1 - x0 < 8 or y1 - y0 < 8:
        continue
    band = img[y0:y1, x0:x1].astype(np.float32)
    vals.append(abs(float(np.percentile(band, 95)) - float(np.percentile(band, 5))))

vals = np.asarray(vals)
base = json.load(open(HERE / "real_baseline.json", encoding="utf-8"))["polarity"]
print(f"합성 {root.name}: n={len(vals)}")
print(f"  median {np.median(vals):.1f} · p10 {np.percentile(vals,10):.1f} · "
      f"p90 {np.percentile(vals,90):.1f} · min {vals.min():.1f} · "
      f"<40 {100*np.mean(vals<40):.2f}% · <60 {100*np.mean(vals<60):.2f}%")
print(f"실측 real_baseline(n={base['n']}): median {base['contrast_median']} · "
      f"p10 {base['contrast_p10']} · p90 {base['contrast_p90']} · "
      f"min {base['contrast_min']} · <40 {base['contrast_lt40_pct']:.2f}%")
