# oob 재심사 — EXIF 표시 좌표계 기준으로 라벨 경계 초과 재계산
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()

rows = [json.loads(l) for l in
        (HERE / "screen_boxes.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()]
oob = []
for r in rows:
    cid = r["id"]
    if not r.get("quad"):
        continue
    q = r["quad"]
    xs = [p[0] for p in q]
    ys = [p[1] for p in q]
    p = DATUMO / f"{cid}.jpg"
    with Image.open(p) as im:
        w, h = im.size
        if im.getexif().get(274) in (5, 6, 7, 8):
            w, h = h, w
    if min(xs) < 0 or min(ys) < 0 or max(xs) > w - 1 or max(ys) > h - 1:
        oob.append((cid, w, h, round(min(xs)), round(min(ys)),
                    round(max(xs)), round(max(ys))))
print(f"라벨 {len(rows)}장 중 표시 좌표계 기준 경계 초과: {len(oob)}장")
for cid, w, h, x0, y0, x1, y1 in oob:
    print(f"  {cid}: img {w}x{h}  box ({x0},{y0})-({x1},{y1})")
