# v11e 오독의 기울기 근거 측정 — "현재 실패가 진짜 롤 쪽에 있나?"(사람 질문
# 2026-10-04). 오독(80장)과 정답(2,413장)의 밴드 기울기 분포를 같은 자로
# 재서 비교한다. GM 쿼드는 축정렬 사각형이라 정보가 없어 **밴드 내용물의
# 획 방향**에서 잰다:
#   roll  = 밴드 크롭의 그래디언트 방향 히스토그램(모듈로 180°) 최고봉
#           — 7세그 획(가로·세로)이 패널 회전각만큼 돌아가 있다
#   keystone = 좌·우 절반에서 각각 잰 각도의 차(수평 원근 성분 근사)
# 사용: python _diag/measure_e2e_tilt.py
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from eval_reader import load_gray  # noqa: E402  EXIF 규약 통일 로더

UPSTREAM = HERE.parent / "upstream" / "datumo"
E2E = HERE / "_diag" / "e2e_bandnet" / "tg_v11e.jsonl"
# 밴드 영역: 사람 라벨(277장) 우선, 없으면 배포 검출기(atone_tf640w15) 예측
# 상자(2,477장) — 크롭 영역만 필요하고 각도는 내용물에서 재므로 축정렬이어도
# 무방하다. 전체 모집단 커버를 위해 두 source 를 합친다.
BANDS = {}
for line in (HERE / "band_quads_pred_tf640w15_20261003.jsonl").read_text(
        encoding="utf-8").splitlines():
    if line.strip():
        r = json.loads(line)
        BANDS[r["id"]] = r
for line in (HERE / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        r = json.loads(line)
        BANDS[r["id"]] = r


def band_angle(crop):
    """그래디언트 방향 히스토그램 최고봉(도, -90~90). 실패 시 None."""
    if crop is None or min(crop.shape) < 24:
        return None
    g = crop.astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    ang = np.degrees(np.arctan2(gy, gx))  # -180~180, 변(에지)의 법선 아님 —
    # 변의 방향은 그래디언트와 수직: +90 회전
    ang = (ang + 90.0) % 180.0
    m = mag > np.percentile(mag, 90)
    if m.sum() < 200:
        return None
    hist, edges = np.histogram(ang[m], bins=180, range=(0, 180))
    k = np.ones(5) / 5.0
    hist = np.convolve(hist, k, "same")
    peak = float(np.argmax(hist))
    # 7세그 획 방향은 90° 모듈로다(가로·세로 획이 쌍을 이룬다) — 패널 롤은
    # -45~45 로 정준화해 읽는다. 최고봉이 세로획(≈90°)이면 -90 물린다.
    return ((peak + 45.0) % 90.0) - 45.0


rows = [json.loads(l) for l in E2E.read_text(encoding="utf-8").splitlines()]
out = {"right": [], "wrong": [], "wrong_lead1": []}
for r in rows:
    if r["verdict"] not in ("right", "wrong"):
        continue
    b = BANDS.get(r["id"])
    if b is None:
        continue
    rel = UPSTREAM / "extracted" / "TILDE" / (r["id"].replace("/", "\\") + ".jpg")
    if not rel.exists():
        rel = UPSTREAM / "extracted" / "TILDE" / (r["id"] + ".jpg")
    if not rel.exists():
        continue
    img = load_gray(rel)
    if img is None:
        continue
    xs_ = [p[0] for p in b["quad"]]
    ys_ = [p[1] for p in b["quad"]]
    x0, y0, x1, y1 = int(min(xs_)), int(min(ys_)), int(max(xs_)), int(max(ys_))
    m = int(0.04 * (y1 - y0))
    x0, y0 = max(0, x0 - m), max(0, y0 - m)
    x1, y1 = min(img.shape[1], x1 + m), min(img.shape[0], y1 + m)
    crop = img[y0:y1, x0:x1]
    half = crop.shape[1] // 2
    a = band_angle(crop)
    al, ar = band_angle(crop[:, :half]), band_angle(crop[:, half:])
    if a is None or al is None or ar is None:
        continue
    rec = dict(id=r["id"], gt=r["gt"], pred=r["pred"], roll=a,
               keystone=abs(al - ar) if abs(al - ar) < 45 else None)
    out["right" if r["verdict"] == "right" else "wrong"].append(rec)
    if r["verdict"] == "wrong" and str(r["gt"]).startswith("1"):
        out["wrong_lead1"].append(rec)


def stats(v, key):
    xs = np.array([r[key] for r in v if r[key] is not None])
    if len(xs) == 0:
        return "n=0"
    return (f"n={len(xs)} · median {np.median(xs):.1f}° · p90 {np.percentile(xs, 90):.1f}° "
            f"· >15° {100*np.mean(xs > 15):.1f}%")


for k in ("right", "wrong", "wrong_lead1"):
    print(f"[{k}] 롤:   {stats(out[k], 'roll')}")
    print(f"[{k}] 키스톤(좌우각차): {stats(out[k], 'keystone')}")
print("\n[wrong 롤 상위 10]")
for r in sorted(out["wrong"], key=lambda r: -abs(r["roll"]))[:10]:
    print(f"  {r['id']}  GT {r['gt']} → {r['pred']}  롤 {r['roll']:.0f}°")
