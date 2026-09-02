# 글자 단위 분류기 학습 — glyph_data (성분 분할 자동 라벨, 10클래스 0~9).
# 이미지 단위 train/val 분할(같은 사진의 글자가 양쪽에 쓰이는 누수 방지).
import random
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
DATA = HERE / "glyph_data"
OUT = HERE / "glyph_cnn.keras"
SEED = 7
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)


def main() -> int:
    files = list(DATA.glob("*.png"))
    import re
    pat = re.compile(r"(\d+)_(.+)_(\d+)$")
    by_img = {}
    for f in files:
        m = pat.fullmatch(f.stem)
        if not m:
            continue
        cls, img_id = int(m.group(1)), m.group(2)
        by_img.setdefault(img_id, []).append((f, cls))
    img_ids = sorted(by_img)
    random.shuffle(img_ids)
    n_val = max(1, int(len(img_ids) * 0.12))
    val_ids = set(img_ids[:n_val])
    tr, va = [], []
    for iid in img_ids:
        (va if iid in val_ids else tr).extend(by_img[iid])
    print(f"images={len(img_ids)} train_glyphs={len(tr)} val_glyphs={len(va)}")

    def load(f):
        im = cv2.imread(str(f))
        return cv2.resize(im, (96, 96), interpolation=cv2.INTER_AREA)

    aug = tf.keras.Sequential([
        tf.keras.layers.RandomTranslation(0.06, 0.06),
        tf.keras.layers.RandomZoom(0.15),
        tf.keras.layers.RandomRotation(0.03),
        tf.keras.layers.RandomContrast(0.4),
    ])

    def make_set(items, training):
        X = np.asarray([load(f) for f, _ in items], dtype=np.float32)
        y = np.asarray([c for _, c in items], dtype=np.int32)
        ds = tf.data.Dataset.from_tensor_slices((X, y))
        if training:
            ds = ds.shuffle(len(X))

            def augmap(x, yy):
                return aug(x, training=True), yy
            ds = ds.map(augmap, num_parallel_calls=4)
        return ds.batch(32).prefetch(4)

    base = tf.keras.applications.MobileNetV2(
        input_shape=(96, 96, 3), include_top=False,
        weights="imagenet", alpha=0.5)
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(96, 96, 3)),
        tf.keras.layers.Rescaling(scale=1.0 / 127.5, offset=-1.0),
        base,
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dropout(0.25),
        tf.keras.layers.Dense(10, activation="softmax"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(5e-4),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"])
    es = tf.keras.callbacks.EarlyStopping(
        monitor="val_accuracy", patience=6, restore_best_weights=True)
    model.fit(
        make_set(tr, True), validation_data=make_set(va, False),
        epochs=40, verbose=2, callbacks=[es])
    model.save(OUT)
    print("SAVED", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
