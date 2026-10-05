# 검출 실패 19장 + 잘림 후보 12장 검증 몽타주(사람: "자 이제 검출쪽 보자",
# 2026-10-04). A카드: 사진 + 주황(게이트 탈락 원시 예측) + 초록(사람 라벨),
# 캡션 = 원시 점수·면적비·탈락 사유. 클립카드: 사진(빨강/초록) + 리더 크롭,
# 캡션 = GT→pred·포함률.
# 사용: python _diag/make_fail_montage.py
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from eval_reader import load_gray  # noqa: E402

UPSTREAM = HERE.parent / "upstream" / "datumo"
CONF_TH = 0.25     # e2e(tg_v11e) 규격: conf 0.25 · frac>=2%

det_rows = [json.loads(l) for l in
            (HERE / "_diag" / "band_real" / "atone_tg640w15.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip() and '"id"' in l]
det_by_id = {r["id"]: r for r in det_rows}
e2e = {}
for ln in (HERE / "_diag" / "e2e_bandnet" / "tg_v11e.jsonl").read_text(
        encoding="utf-8").splitlines():
    if ln.strip():
        r = json.loads(ln)
        e2e[r["id"]] = r
preds = {}
for r in json.loads((HERE / "_diag" / "fail19_raw_probe.json").read_text(encoding="utf-8")):
    if "box" in r:
        b = r["box"]
        preds[r["id"]] = (b[0], b[1], b[2], b[3], r["score"])
human = {}
for ln in (HERE / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
    if ln.strip():
        r = json.loads(ln)
        xs = [p[0] for p in r["quad"]]
        ys = [p[1] for p in r["quad"]]
        human[r["id"]] = (min(xs), min(ys), max(xs), max(ys))


def photo(eid):
    rel = UPSTREAM / "extracted" / "TILDE" / (eid.replace("/", "\\") + ".jpg")
    if not rel.exists():
        rel = UPSTREAM / "extracted" / "TILDE" / (eid + ".jpg")
    return load_gray(rel)


def base_card(eid, W, H, boxes):
    s = 340 / max(W, H)
    th = cv2.resize(photo_cache, (max(2, int(W * s)), max(2, int(H * s))),
                    interpolation=cv2.INTER_AREA) if False else None
    return s


def render_thumb(eid):
    global photo_cache
    img = photo(eid)
    photo_cache = img
    return img


# ── A: 검출 실패 19장
# 2026-10-04 사람: "90도 돌아간 건 제외하고 보자 — 애당초 모델에 90도 돌아간
# 건 보여주지도 않았잖아". 합성 학습 축은 roll ±15도뿐이라 90도 도메인은
# 정의상 학습 분포 밖이다. device_labels 의 rotation 라벨이 있는 4장
# (1213·1226 left, 1565·940 right)을 리뷰에서 뺀다.
ROT_EXCL = {"glucose_batch1/1213", "glucose_batch1/1226",
            "glucose_batch1/1565", "glucose_batch1/940"}
fails = sorted(({r["id"] for r in det_rows if not r.get("det")} |
                {cid for cid, r in e2e.items() if r["verdict"] == "det"})
               - ROT_EXCL)
CW, CH, PAD, COLS = 360, 320, 8, 4
ROWS = (len(fails) + COLS - 1) // COLS
canvas = np.full((PAD + ROWS * (CH + PAD), PAD + COLS * (CW + PAD)), 16, np.uint8)
canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
for k, eid in enumerate(fails):
    img = photo(eid)
    if img is None:
        continue
    H, W = img.shape
    s = 300 / max(W, H)
    th = cv2.resize(img, (max(2, int(W * s)), max(2, int(H * s))),
                    interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)
    g = human.get(eid)
    if g:
        cv2.rectangle(rgb, (int(g[0] * s), int(g[1] * s)),
                      (int(g[2] * s), int(g[3] * s)), (0, 220, 0), 2)
    p = preds.get(eid)
    if p:
        cv2.rectangle(rgb, (int(p[0] * s), int(p[1] * s)),
                      (int(p[2] * s), int(int(p[3]) * s)), (0, 140, 255), 2)
        frac = (p[2] - p[0]) * (p[3] - p[1]) / max(1.0, W * H) * 100
        why = ("점수낮음" if p[4] < CONF_TH else ("스케일게이트(미세상자)" if frac < 2.0 else "통과??"))
        cap = f"{eid.split('/')[-1]} sc{p[4]:.2f} {frac:.1f}% {why}"
    else:
        cap = f"{eid.split('/')[-1]} 원시예측 없음(완전미검출)"
    rgb = cv2.copyMakeBorder(rgb, 0, 26, 0, 0, cv2.BORDER_CONSTANT,
                             value=(16, 16, 16))
    cv2.putText(rgb, cap[:46], (4, CH - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                (210, 210, 210), 1)
    y0 = PAD + (k // COLS) * (CH + PAD)
    x0 = PAD + (k % COLS) * (CW + PAD)
    h2, w2 = rgb.shape[:2]
    canvas[y0:y0 + h2, x0:x0 + w2] = rgb
cv2.imwrite(str(HERE / "_diag" / "fail15_montage_tg.png"), canvas)
print(f"A(실패 {len(fails)}장, 90도회전 4장 제외): _diag/fail15_montage_tg.png")

# ── 클립 후보 12장(det-clip-오독): 사진 + 리더 크롭
clips = []
for cid, r in sorted(e2e.items()):
    d = det_by_id.get(cid)
    if r["verdict"] == "wrong" and d is not None and d.get("det") \
            and d.get("contain", 1.0) < 1.0:
        clips.append((cid, r, d))
CW2, CH2, PAD2, COLS2 = 340, 470, 8, 4
ROWS2 = (len(clips) + COLS2 - 1) // COLS2
c2 = np.full((PAD2 + ROWS2 * (CH2 + PAD2), PAD2 + COLS2 * (CW2 + PAD2)), 16,
             np.uint8)
c2 = cv2.cvtColor(c2, cv2.COLOR_GRAY2BGR)
for k, (cid, r, d) in enumerate(clips):
    img = photo(cid)
    if img is None:
        continue
    H, W = img.shape
    s = 300 / max(W, H)
    th = cv2.resize(img, (max(2, int(W * s)), max(2, int(H * s))),
                    interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(th, cv2.COLOR_GRAY2BGR)
    g = human.get(cid)
    if g:
        cv2.rectangle(rgb, (int(g[0] * s), int(g[1] * s)),
                      (int(g[2] * s), int(g[3] * s)), (0, 220, 0), 2)
    p = d["pred"]
    cv2.rectangle(rgb, (int(p[0] * s), int(p[1] * s)),
                  (int(p[2] * s), int(p[3] * s)), (0, 0, 255), 2)
    x0b, y0b, x1b, y1b = [int(v) for v in p]
    crop = img[max(0, y0b):y1b, max(0, x0b):x1b]
    crop = cv2.resize(crop, (300, 200), interpolation=cv2.INTER_AREA)
    crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    cell = np.full((CH2, CW2, 3), 16, np.uint8)
    th2 = cv2.copyMakeBorder(rgb, 0, 20, 0, 0, cv2.BORDER_CONSTANT,
                             value=(16, 16, 16))
    cv2.putText(th2, f"{cid.split('/')[-1]} GT{r['gt']}->{r['pred']} "
                 f"cont{d['contain']:.2f}", (4, CH2 - 148),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    hh = min(th2.shape[0], CH2 - 220)
    cell[:hh, :min(th2.shape[1], CW2)] = th2[:hh, :min(th2.shape[1], CW2)]
    cell[CH2 - 210:CH2 - 10, 10:310] = cv2.resize(
        crop, (300, 200), interpolation=cv2.INTER_AREA)
    y0 = PAD2 + (k // COLS2) * (CH2 + PAD2)
    x0 = PAD2 + (k % COLS2) * (CW2 + PAD2)
    c2[y0:y0 + CH2, x0:x0 + CW2] = cell
cv2.imwrite(str(HERE / "_diag" / "clip12_montage_tg.png"), c2)
print(f"클립후보({len(clips)}장): _diag/clip12_montage.png")
