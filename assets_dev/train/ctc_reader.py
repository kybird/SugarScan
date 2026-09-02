# CTC 화면 리더 — rectified LCD 화면(320×160 gray) → 숫자열 직접 출력.
# 1단계: 합성 화면 사전학습  2단계: 실사진 304장(GM rect) 파인튜닝.
# 산출: assets_dev/train/reader_model (SavedModel, logits 출력)
import json
import random
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
SYNTH = HERE / "synth_screens"
DATUMO = HERE.parent / "upstream" / "datumo"
GM_QUADS = HERE / "gmscreen_quads.jsonl"
LABELED = HERE / "labeled.jsonl"
OUT_DIR = HERE / "reader_model"

IN_H, IN_W = 160, 320
NUM_CLASSES = 11  # 0~9 숫자 + 10=blank(마지막 인덱스)
MAX_LABEL = 3
SEED = 7
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)


def build_model():
    inp = tf.keras.Input((IN_H, IN_W, 1), name="img")
    lab = tf.keras.Input((MAX_LABEL,), dtype=tf.int32, name="label")
    ilen = tf.keras.Input((1,), dtype=tf.int32, name="input_len")
    llen = tf.keras.Input((1,), dtype=tf.int32, name="label_len")

    x = tf.keras.layers.Rescaling(scale=1.0 / 127.5, offset=-1.0)(inp)
    x = tf.keras.layers.Conv2D(32, 3, strides=2, padding="same", activation="relu")(x)
    x = tf.keras.layers.Conv2D(64, 3, strides=2, padding="same", activation="relu")(x)
    x = tf.keras.layers.Conv2D(128, 3, strides=2, padding="same", activation="relu")(x)
    # (B, 20, 40, 128) → 시간축(W=40) 시퀀스로
    x = tf.keras.layers.Permute((2, 1, 3))(x)
    x = tf.keras.layers.Reshape((40, 20 * 128))(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Bidirectional(
        tf.keras.layers.LSTM(96, return_sequences=True))(x)
    logits = tf.keras.layers.Dense(NUM_CLASSES, name="logits")(x)

    class CTCLayer(tf.keras.layers.Layer):
        def call(self, labels, y_pred, il, ll):
            loss = tf.nn.ctc_loss(
                labels=tf.cast(labels, tf.int32),
                logits=y_pred,
                label_length=tf.cast(tf.squeeze(ll, -1), tf.int32),
                logit_length=tf.cast(tf.squeeze(il, -1), tf.int32),
                logits_time_major=False,
                blank_index=NUM_CLASSES - 1,
            )
            self.add_loss(loss)
            return y_pred

    loss = CTCLayer()(lab, logits, ilen, llen)
    train_model = tf.keras.Model([inp, lab, ilen, llen], loss)
    train_model.compile(optimizer=tf.keras.optimizers.Adam(1e-3))
    logits_model = tf.keras.Model(inp, logits)
    return train_model, logits_model


def decode_greedy(logits):
    seq = np.argmax(logits, axis=-1)  # (B, T)
    out = []
    for row in seq:
        s = []
        prev = -1
        for v in row:
            v = int(v)
            if v != prev and v != NUM_CLASSES - 1:
                s.append(str(v))
            prev = v
        out.append("".join(s))
    return out


def load_real(threshold_score=0.0, only_ids=None):
    quads = {}
    for l in GM_QUADS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j["quad"]
    readings = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            readings[j["id"]] = j["reading"]
    labeled = {}
    for l in LABELED.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labeled[j["id"]] = j
    out = []
    for cid, quad in quads.items():
        if only_ids is not None and cid not in only_ids:
            continue
        if cid in labeled and labeled[cid].get("source") == "human":
            continue  # 학습에 쓴 장은 hold-out 에서 제외 안 함(파인튜닝에 씀)
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            continue
        from PIL import Image
        try:
            with Image.open(p) as pil:
                pil.load()
                img = cv2.cvtColor(
                    np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        except Exception:
            continue
        q = np.array(quad, dtype=np.float32)
        xs, ys = q[:, 0], q[:, 1]
        src = np.array(
            [[xs.min(), ys.min()], [xs.max(), ys.min()],
             [xs.max(), ys.max()], [xs.min(), ys.max()]], dtype=np.float32)
        dst = np.array(
            [[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1], [0, IN_H - 1]],
            dtype=np.float32)
        rect = cv2.warpPerspective(
            img, cv2.getPerspectiveTransform(src, dst), (IN_W, IN_H))
        val = corrections_or(readings, cid)
        out.append((cid, rect, str(val)))
    return out


def corrections_or(readings, cid):
    corr = HERE / "gt_corrections.jsonl"
    if corr.exists():
        for l in corr.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                if j["id"] == cid:
                    return j["corrected"]
    return readings.get(cid)


def synth_dataset(count, seeds):
    labels = {}
    for seed in seeds:
        j = json.loads((SYNTH / f"labels_{seed}.json").read_text(encoding="utf-8"))
        labels.update(j)
    keys = sorted(labels)
    rng = random.Random(seeds[0])
    rng.shuffle(keys)
    for k in keys[:count]:
        p = SYNTH / "images" / f"{k}.png"
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        img = cv2.resize(img, (IN_W, IN_H))
        yield img, labels[k]


def pad_labels(strs):
    out = np.full((len(strs), MAX_LABEL), NUM_CLASSES - 1, dtype=np.int32)
    lens = np.zeros(len(strs), dtype=np.int32)
    for i, s in enumerate(strs):
        lens[i] = len(s)
        for j, ch in enumerate(s[:MAX_LABEL]):
            out[i, j] = int(ch)
    return out, lens


def main() -> int:
    train_model, logits_model = build_model()

    # 1단계: 합성 사전학습
    def synth_ds():
        while True:
            imgs, strs = [], []
            for img, s in synth_dataset(10 ** 9, seeds=(1, 2, 3)):
                imgs.append(img)
                strs.append(s)
                if len(imgs) == 16:
                    lab, lens = pad_labels(strs)
                    yield (np.asarray(imgs)[..., np.newaxis].astype(np.float32),
                           lab,
                           np.full((len(imgs), 1), IN_W // 8, dtype=np.int32),
                           lens[:, np.newaxis]), np.zeros(len(imgs))
                    imgs, strs = [], []

    # 2단계: 실사진
    real = load_real()
    print(f"real rects: {len(real)}")
    random.shuffle(real)

    def real_ds():
        while True:
            order = list(range(len(real)))
            random.shuffle(order)
            for i in range(0, len(order) - 7, 8):
                chunk = [real[j] for j in order[i:i + 8]]
            imgs = np.asarray(
                [c[1][..., np.newaxis].astype(np.float32) for c in chunk])
            lab, lens = pad_labels([c[2] for c in chunk])
            yield (imgs, lab,
                   np.full((len(chunk), 1), IN_W // 8, dtype=np.int32),
                   lens[:, np.newaxis]), np.zeros(len(chunk))


    print("== synthetic pretrain ==")
    import math
    synth_steps = math.ceil(23000 / 16)
    train_model.fit(synth_ds(), epochs=12, verbose=2,
                    steps_per_epoch=synth_steps)
    print("== real finetune ==")
    train_model.fit(real_ds(), epochs=12, verbose=2,
                    steps_per_epoch=max(1, len(real) // 8))

    logits_model.save(str(OUT_DIR))
    print("SAVED", OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
