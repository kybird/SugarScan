# 크롭 전에 GM 박스를 넓히면 판독이 좋아지는가 — 재학습 없이 되는 수정인지 잰다.
#
# 근거: 사람 라벨 396장 대조 결과 GM 은 **오른쪽을 계통적으로 덜 덮는다**
# (중앙 6%, 26%의 장이 10% 넘게 잘림). 혈당계 표시는 우측 정렬이므로
# 잘리는 것은 마지막 자리다. 실제로 한 글자 오독 41건 중 24건이 마지막 자리다.
#
# 주의: 리더는 잘린 크롭으로 학습됐다. 넓히면 분포가 달라지므로, 개선이
# 안 나와도 "패딩이 나쁘다"가 아니라 "지금 리더에겐 낯설다"일 수 있다.
import json
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
IN_H, IN_W = 160, 320
BLANK = 10


def load(p):
    d = {}
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l); d[j["id"]] = j
    return d


def greedy(row):
    seq = np.argmax(row, -1); s, prev = [], -1
    for v in seq:
        v = int(v)
        if v != prev and v != BLANK:
            s.append(str(v))
        prev = v
    return "".join(s)


def warp(g, q, pad_r=0.0, pad_all=0.0):
    a = np.array(q, np.float32)
    x0, y0 = a[:, 0].min(), a[:, 1].min()
    x1, y1 = a[:, 0].max(), a[:, 1].max()
    w, h = x1 - x0, y1 - y0
    x0 -= w * pad_all; x1 += w * (pad_all + pad_r)
    y0 -= h * pad_all; y1 += h * pad_all
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(g.shape[1] - 1, x1), min(g.shape[0] - 1, y1)
    src = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32)
    dst = np.array([[0, 0], [IN_W-1, 0], [IN_W-1, IN_H-1], [0, IN_H-1]], np.float32)
    return cv2.warpPerspective(g, cv2.getPerspectiveTransform(src, dst), (IN_W, IN_H))


def main() -> int:
    gm = load(HERE / "gmscreen_quads.jsonl")
    scr = load(HERE / "screen_boxes.jsonl")
    trained = {c for c, v in scr.items() if v.get("quad")}
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    ids = [str(v) for v in cache["real_holdout_ids"]]
    y = cache["real_holdout_label_ids"]
    gts = {ids[i]: "".join(str(int(v)) for v in y[i] if int(v) != BLANK)
           for i in range(len(ids))}
    use = [c for c in ids if c in gm]
    print(f"캐시 holdout {len(use)}장으로 패딩 스윕 (리더 학습셋 아님)\n")

    grays = {}
    for c in use:
        p = DATUMO / "extracted" / "TILDE" / f"{c}.jpg"
        if p.exists():
            with Image.open(p) as pil:
                pil.load(); pil = ImageOps.exif_transpose(pil)
                grays[c] = cv2.cvtColor(np.asarray(pil.convert("RGB")),
                                        cv2.COLOR_RGB2GRAY)
    keys = [c for c in use if c in grays]
    model = tf.keras.models.load_model(str(HERE / "reader_model"))

    print(f"{'패딩':>22} | {'완전일치':>14} | 마지막자리만 틀림")
    print("-" * 60)
    base = None
    for label, pr, pa in (("없음(현재)", 0.00, 0.00),
                          ("오른쪽 +4%", 0.04, 0.00),
                          ("오른쪽 +8%", 0.08, 0.00),
                          ("오른쪽 +12%", 0.12, 0.00),
                          ("사방 +4%", 0.00, 0.04),
                          ("사방 +8%", 0.00, 0.08),
                          ("사방 4% + 오른쪽 8%", 0.08, 0.04)):
        X = [warp(grays[c], gm[c]["quad"], pr, pa) for c in keys]
        L = model.predict(np.asarray(X, np.float32)[..., None],
                          batch_size=64, verbose=0)
        preds = [greedy(L[i]) for i in range(len(keys))]
        ok = sum(1 for i, c in enumerate(keys) if preds[i] == gts[c])
        last = sum(1 for i, c in enumerate(keys)
                   if preds[i] != gts[c] and len(preds[i]) == len(gts[c])
                   and preds[i][:-1] == gts[c][:-1])
        if base is None:
            base = ok
        d = "" if base == ok and label.startswith("없음") else f"  ({100*(ok-base)/len(keys):+.2f}pp)"
        print(f"{label:>22} | {ok:5d} ({100*ok/len(keys):5.2f}%) | {last:4d}{d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
