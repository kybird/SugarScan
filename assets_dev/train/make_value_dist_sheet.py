# 값 분포 전환(값당 균등 30~599, 2026-10-25 사람 결정) 눈확인 시트.
# 6구간 × 2장 = 12장 렌더. 구간별 대표 값으로 뽑아 3자리 큰 값 렌더가
# 정상인지 사람이 본다(값 축만 변경 — 렌더 경로 불변).
from pathlib import Path

import cv2
import numpy as np
import random

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synth_panel as sp

OUT = Path(__file__).resolve().parent / "_diag" / "value_dist_sheet_v1.png"
PICK = [45, 88, 123, 171, 214, 257, 311, 368, 423, 476, 527, 583]

panels = []
for v in PICK:
    rng = random.Random(20261025 + v)
    s = sp.render_panel(v, rng)
    img = s["panel"]
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    panels.append((s["label"], img))

ph = max(p[1].shape[0] for p in panels)
pw = max(p[1].shape[1] for p in panels)
cols, rows = 4, 3
cell_h = ph + 34
sheet = np.full((rows * cell_h + 10, cols * (pw + 10) + 10, 3), 255, np.uint8)
for i, (v, img) in enumerate(panels):
    r, c = divmod(i, cols)
    y, x = 10 + r * cell_h, 10 + c * (pw + 10)
    sheet[y:y + img.shape[0], x:x + img.shape[1]] = img
    cv2.putText(sheet, f"value={v}", (x, y + img.shape[0] + 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
ok = cv2.imwrite(str(OUT), sheet)
print(f"wrote={ok}  {OUT}  panels={len(panels)}")
