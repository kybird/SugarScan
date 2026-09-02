# 진단: 학습셋 vs hold-out 판독률 대조 + 두 세트 몽타주 생성.
import json
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
from ctc_reader_v2 import build_model, greedy_decode, NUM_CLASSES  # noqa: E402


def montage(X, out, cols=12, cw=160, ch=80):
    n = min(len(X), 60)
    idx = np.linspace(0, len(X) - 1, n).astype(int)
    rows = (n + cols - 1) // cols
    im = np.full((rows * ch, cols * cw), 40, dtype=np.uint8)
    for k, i in enumerate(idx):
        y = (k // cols) * ch
        x = (k % cols) * cw
        im[y:y + ch, x:x + cw] = cv2.resize(X[i], (cw, ch))
    cv2.imwrite(str(out), im)
    print(f"{out.name}: {n}장")


def main() -> int:
    c = np.load(str(HERE / "data_cache_v2.npz"))
    X_rt = c["real_train_images"]
    y_rt = c["real_train_label_ids"]
    X_rh = c["real_holdout_images"]
    y_rh = c["real_holdout_label_ids"]
    id_rt = [str(x) for x in c["real_train_ids"]]
    id_rh = [str(x) for x in c["real_holdout_ids"]]

    m = tf.keras.models.load_model(str(HERE / "reader_model"))
    logits_model = tf.keras.Model(m.inputs, m.get_layer("logits").output)

    for name, X, y, ids in (("학습셋", X_rt, y_rt, id_rt),
                            ("holdout", X_rh, y_rh, id_rh)):
        logits = logits_model.predict(X[:600][..., np.newaxis].astype(np.float32),
                                      batch_size=128, verbose=0)
        preds = greedy_decode(logits)
        gts = ["".join(str(int(v)) for v in row if int(v) != NUM_CLASSES)
               for row in y[:600]]
        exact = sum(1 for p, g in zip(preds, gts) if p == g)
        print(f"{name}: exact {exact}/{len(gts)} ({100 * exact / len(gts):.1f}%)")
        for i in range(10):
            print(f"  GT {gts[i]:>4}  pred {preds[i]!r}  ({ids[i]})")

    montage(X_rt, HERE / "diag_train_sheet.png")
    montage(X_rh, HERE / "diag_holdout_sheet.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
