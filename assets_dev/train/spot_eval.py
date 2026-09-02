# 빠른 표본 판독 — 가중치 비교 디버그용 (전체 평가는 eval_reader.py).
# 사용: python spot_eval.py [weights.h5] [N]
#   weights.h5 를 주면 그 가중치를 얹은 모델, 없으면 reader_model SavedModel.
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
IN_H, IN_W = 160, 320
NUM_CLASSES = 11

from ctc_reader_v2 import build_model  # noqa: E402


def main() -> int:
    weights = None
    n = 12
    for a in sys.argv[1:]:
        if a.isdigit():
            n = int(a)
        else:
            weights = a
    if weights:
        train_model, logits_model = build_model()
        train_model.load_weights(str(HERE / weights))
        tag = weights
    else:
        m = tf.keras.models.load_model(str(HERE / "reader_model"))
        logits_model = tf.keras.Model(m.inputs, m.get_layer("logits").output)
        tag = "reader_model"

    labeled = set()
    for l in (HERE / "labeled.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            labeled.add(json.loads(l)["id"])
    quads = {}
    for l in (HERE / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j["quad"]
    readings = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            readings[j["id"]] = j["reading"]

    print(f"== {tag} — 표본 {n}장 ==")
    shown = 0
    ok = 0
    for cid, quad in quads.items():
        if cid in labeled:
            continue
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            continue
        with Image.open(p) as pil:
            pil.load()
            img = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        q = np.array(quad, dtype=np.float32)
        xs, ys = q[:, 0], q[:, 1]
        src = np.array([[xs.min(), ys.min()], [xs.max(), ys.min()],
                        [xs.max(), ys.max()], [xs.min(), ys.max()]],
                       dtype=np.float32)
        dst = np.array([[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1],
                        [0, IN_H - 1]], dtype=np.float32)
        rect = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst),
                                   (IN_W, IN_H))
        x = rect[np.newaxis, ..., np.newaxis].astype(np.float32)
        seq = np.argmax(logits_model.predict(x, verbose=0)[0], axis=-1)
        s, prev = [], -1
        for v in seq:
            v = int(v)
            if v != prev and v != NUM_CLASSES - 1:
                s.append(str(v))
            prev = v
        pred = "".join(s)
        gt = str(readings.get(cid))
        mark = "OK " if pred == gt else "MISS"
        ok += pred == gt
        shown += 1
        print(f"{mark} {cid}  GT {gt:>4}  pred {pred!r}")
        if shown >= n:
            break
    print(f"표본 {ok}/{shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
