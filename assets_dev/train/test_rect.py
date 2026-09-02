# /api/rect 실측 — 정상 라벨 + 좌표 파손 의심 라벨 스트립 저장
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "rect_test"
OUT.mkdir(exist_ok=True)

IDS = [
    "glucose_batch1/1001", "glucose_batch1/1005", "glucose_batch1/1062", "glucose_batch1/1193",
    "glucose_batch1/1636",  # oob 의심
]

for cid in IDS:
    url = f"http://127.0.0.1:8777/api/rect?id={cid}"
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"{cid}: HTTP 오류 {e}")
        continue
    if d.get("error"):
        print(f"{cid}: error={d['error']}")
        continue
    b64 = d["img"].split(",", 1)[1]
    name = cid.replace("/", "__")
    (OUT / f"{name}.jpg").write_bytes(__import__("base64").b64decode(b64))
    print(f"{cid}: quad_ok={d['quad_ok']} oob={d['oob']} → {name}.jpg")
