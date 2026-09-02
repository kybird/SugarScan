# 자동 셀 라벨(304장×3)로 숫자 셀 분류기 학습 — MobileNetV2 전이.
# 입력 96×96×3 (기존 SevenSegCnnEngine 계약 동일), 12클래스(0~9 숫자, 11=빈칸).
# 산출: assets_dev/train/cell_model.keras (+ tflite는 통과 후 변환)
import csv
import json
import random

import numpy as np
import tensorflow as tf
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "cell_data"
OUT = HERE / "cell_model.h5"

SEED = 7
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)


def load_rows():
    rows = []
    with open(DATA / "labels.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((r["file"], [int(r["c1"]), int(r["c2"]), int(r["c3"])]))
    random.shuffle(rows)
    return rows


def cell_image(band, cell_index):
    h, w = band.shape[:2]
    c = band[:, cell_index * w // 3:(cell_index + 1) * w // 3]
    return cv2.resize(c, (96, 96), interpolation=cv2.INTER_AREA)


import cv2  # noqa: E402


def main() -> int:
    rows = load_rows()
    X, y = [], []
    for fn, cells in rows:
        band = cv2.imread(str(DATA / fn))
        if band is None:
            continue
        for i, cls in enumerate(cells):
            X.append(cell_image(band, i))
            y.append(cls)
    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.int32)
    n = len(X)
    idx = list(range(n))
    random.shuffle(idx)
    n_val = max(1, int(n * 0.12))
    val_idx = idx[:n_val]
    tr_idx = idx[n_val:]
    print(f"samples={n} train={len(tr_idx)} val={len(val_idx)}")

    aug = tf.keras.Sequential([
        tf.keras.layers.RandomTranslation(0.06, 0.06),
        tf.keras.layers.RandomZoom(0.12),
        tf.keras.layers.RandomRotation(0.02),
        tf.keras.layers.RandomContrast(0.35),
    ])

    def ds(indices, training):
        def gen():
            for i in indices:
                x = X[i]
                if training:
                    x = aug(tf.convert_to_tensor(x), training=True).numpy()
                yield x, y[i]
        return tf.data.Dataset.from_generator(
            gen, output_signature=(
                tf.TensorSpec(shape=(96, 96, 3), dtype=tf.float32),
                tf.TensorSpec(shape=(), dtype=tf.int32)),
        ).batch(32).prefetch(4)

    base = tf.keras.applications.MobileNetV2(
        input_shape=(96, 96, 3), include_top=False,
        weights="imagenet", alpha=0.5)
    base.trainable = True
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(96, 96, 3)),
        # MobileNetV2 preprocess_input 은 함수라 Sequential 에 못 넣는다(TF 2.10)
        tf.keras.layers.Rescaling(scale=1.0 / 127.5, offset=-1.0),
        base,
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dropout(0.25),
        tf.keras.layers.Dense(12, activation="softmax"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(5e-4),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"])
    model.fit(
        ds(tr_idx, True), validation_data=ds(val_idx, False),
        epochs=30, verbose=2)
    model.save(OUT)
    print("SAVED", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
