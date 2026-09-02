# /api/rect 스트립 대량 생성 — 라벨 앞 24장 몽타주 (깨짐 패턴 파악용)
import base64
import json
import urllib.request
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "rect_test"
OUT.mkdir(exist_ok=True)

rows = [json.loads(l) for l in
        (HERE / "screen_boxes.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()]
ids = [r["id"] for r in rows[:24] if r.get("quad")]

strips = []
for cid in ids:
    url = f"http://127.0.0.1:8777/api/rect?id={cid}&mode=lcd"
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            d = json.loads(r.read().decode("utf-8"))
        if d.get("error"):
            print(f"{cid}: {d['error']}")
            continue
        buf = np.frombuffer(base64.b64decode(d["img"].split(",", 1)[1]), np.uint8)
        im = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        im = cv2.resize(im, None, fx=0.5, fy=0.5)
        cv2.putText(im, cid.split("/")[1], (4, 14), cv2.FONT_HERSHEY_SIMPLEX,
                    0.4, (0, 255, 255), 1, cv2.LINE_AA)
        strips.append(im)
        print(f"{cid}: ok")
    except Exception as e:
        print(f"{cid}: FAIL {e}")

if strips:
    w = max(s.shape[1] for s in strips)
    h = max(s.shape[0] for s in strips)
    cols = 3
    rowsn = (len(strips) + cols - 1) // cols
    board = np.full((rowsn * (h + 4), cols * (w + 4), 3), 18, np.uint8)
    for i, s in enumerate(strips):
        y = (i // cols) * (h + 4)
        x = (i % cols) * (w + 4)
        board[y:y + s.shape[0], x:x + s.shape[1]] = s
    cv2.imwrite(str(OUT / "rect_montage.png"), board)
    print(f"→ rect_test/rect_montage.png ({len(strips)}장)")
