# gmscreen_quads(raw 좌표) → 표시(oriented) 좌표계 변환 — 라벨러 힌트용
# 원본 gmscreen_quads.jsonl은 raw 좌표계로 보존(build_cache 등 백엔드용)
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()
SRC = HERE / "gmscreen_quads.jsonl"
DST = HERE / "gmscreen_quads_oriented.jsonl"


def to_oriented(quad, W, H, ori):
    if ori == 6:      # 표시 = 원본을 90° CW 회전: (x,y) → (H-1-y, x)
        return [[H - 1 - p[1], p[0]] for p in quad]
    if ori == 3:      # 180°
        return [[W - 1 - p[0], H - 1 - p[1]] for p in quad]
    if ori == 8:      # 표시 = 원본을 90° CCW 회전: (x,y) → (y, W-1-x)
        return [[p[1], W - 1 - p[0]] for p in quad]
    return quad       # 1 등 무회전


out = []
for l in SRC.read_text(encoding="utf-8").splitlines():
    if not l.strip():
        continue
    d = json.loads(l)
    p = DATUMO / f"{d['id']}.jpg"
    with Image.open(p) as im:
        W, H = im.size
        ori = im.getexif().get(274, 1)
    d = dict(d)
    d["quad"] = to_oriented(d["quad"], W, H, ori)
    out.append(json.dumps(d, ensure_ascii=False))


DST.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"변환 완료: {len(out)}행 → {DST.name}")
