# 플래그 라벨의 원본 크기 vs 저장 좌표 대조 — 좌표계 버그 진단
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()

rows = [json.loads(l) for l in
        (HERE / "screen_boxes.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()]
print("total labels:", len(rows))


def bbox(q):
    xs = [p[0] for p in q]
    ys = [p[1] for p in q]
    return min(xs), min(ys), max(xs), max(ys)


check = list(range(min(3, len(rows))))
check += [i for i, r in enumerate(rows)
          if r["id"] in ("glucose_batch1/1636", "glucose_batch1/1640",
                         "glucose_batch1/1645", "glucose_batch1/1681",
                         "glucose_batch1/1691")]
seen = set()
for i in check:
    if i in seen:
        continue
    seen.add(i)
    d = rows[i]
    p = DATUMO / f"{d['id']}.jpg"
    with Image.open(p) as im:
        W0, H0 = im.size
    x0, y0, x1, y1 = bbox(d["quad"])
    af = (x1 - x0) * (y1 - y0) / (W0 * H0)
    print(f"[{i}] {d['id']}: img {W0}x{H0}  "
          f"box ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})  af={af:.3f}")
