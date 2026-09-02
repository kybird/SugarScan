# EXIF orientation 실측 — 라벨된 표본 + 1707 (회전 불일치 원인 배제 검증)
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = (HERE / ".." / "upstream" / "datumo" / "extracted" / "TILDE").resolve()

rows = [json.loads(l) for l in
        (HERE / "screen_boxes.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()]
sample = [r["id"] for r in rows[:10]] + ["glucose_batch1/1707"]

for cid in sample:
    p = DATUMO / f"{cid}.jpg"
    try:
        with Image.open(p) as im:
            ex = im.getexif()
            ori = ex.get(274, "없음")
            w, h = im.size
        print(f"{cid}: EXIF orientation={ori}  저장크기 {w}x{h}")
    except Exception as e:
        print(f"{cid}: 읽기 실패 {e}")
