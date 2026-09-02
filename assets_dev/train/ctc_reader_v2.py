# CTC 리더 v2 — npz 캐시 + tf.data in-memory + 체크포인트 + 조기중단.
# 모델 구조와 4입력+add_loss fit 패턴은 v1(ctc_reader.py)에서 검증된 것 그대로.
# 파인튜닝은 라벨 240장(화면 전체 rect), hold-out 평가는 eval_reader.py가 별도 수행
# (미라벨 1,767장 — 파인튜닝과 무겹침, 2026-08-30 리뷰에서 지적된 누수 구조의 수정판).
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
CACHE = HERE / "data_cache_v2.npz"
CKPT_DIR = HERE / "checkpoints_v2"
CSV_LOG = HERE / "training_log.csv"
OUT_DIR = HERE / "reader_model"

IN_H, IN_W = 160, 320
NUM_CLASSES = 11      # 0~9 + blank=10(마지막 인덱스)
MAX_LABEL = 3
SEQ_LEN = IN_W // 8   # conv 3회 s2 → 시간축 40
BATCH = 64
FT_BATCH = 16
EPOCHS_PRE = 40
EPOCHS_FT = 12
SEED = 7
np.random.seed(SEED)
tf.random.set_seed(SEED)


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
    x = tf.keras.layers.Reshape((SEQ_LEN, 20 * 128))(x)
    x = tf.keras.layers.Dense(128, activation="relu")(x)
    x = tf.keras.layers.Bidirectional(
        tf.keras.layers.LSTM(96, return_sequences=True))(x)
    logits = tf.keras.layers.Dense(NUM_CLASSES, name="logits")(x)

    out = CTCLayer()(lab, logits, ilen, llen)
    train_model = tf.keras.Model([inp, lab, ilen, llen], out)
    train_model.compile(optimizer=tf.keras.optimizers.Adam(1e-3))
    logits_model = tf.keras.Model(inp, logits)
    return train_model, logits_model


def make_ds(X, y, lens, batch, shuffle=False, augment=False):
    """캐시 배열(uint8 H×W) → v1 호환 4입력 배치. 더미 y는 add_loss라 미사용.
    augment=True 면 회전·이동·줌·대비를 무작위로 걸어 암기를 방지한다."""
    ds = tf.data.Dataset.from_tensor_slices((X, y, lens))
    if shuffle:
        ds = ds.shuffle(min(len(X), 10000), reshuffle_each_iteration=True)

    rot = tf.keras.layers.RandomRotation(0.03, fill_mode="constant")
    tr = tf.keras.layers.RandomTranslation(0.05, 0.05, fill_mode="constant")
    zm = tf.keras.layers.RandomZoom(0.1, fill_mode="constant")
    ct = tf.keras.layers.RandomContrast(0.35)

    def _map(img, lab, ln):
        x = tf.expand_dims(tf.cast(img, tf.float32), -1)
        if augment:
            x = rot(x)
            x = tr(x)
            x = zm(x)
            x = ct(x)
        x4 = (x,
              tf.cast(lab, tf.int32),
              tf.fill([1], SEQ_LEN),
              tf.reshape(tf.cast(ln, tf.int32), [1]))
        return x4, tf.zeros(1, tf.float32)

    return (ds.map(_map, num_parallel_calls=tf.data.AUTOTUNE)
              .batch(batch).prefetch(tf.data.AUTOTUNE))


OUT_PREDS = HERE / "reader_preds.json"


def greedy_decode(logits):
    seq = np.argmax(logits, axis=-1)
    out = []
    for row in seq:
        s, prev = [], -1
        for v in row:
            v = int(v)
            if v != prev and v != NUM_CLASSES - 1:
                s.append(str(v))
            prev = v
        out.append("".join(s))
    return out


def main() -> int:
    # "ft": 사전학습 best 체크포인트에서 파인튜닝만 재실행 (ft [에폭수])
    ft_only = len(sys.argv) > 1 and sys.argv[1] == "ft"
    ft_epochs = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    cache = np.load(str(CACHE))
    X_tr = cache["synth_train_images"]
    y_tr = cache["synth_train_label_ids"]
    l_tr = cache["synth_train_label_lens"]
    X_va = cache["synth_val_images"]
    y_va = cache["synth_val_label_ids"]
    l_va = cache["synth_val_label_lens"]
    X_rt = cache["real_train_images"]
    y_rt = cache["real_train_label_ids"]
    l_rt = cache["real_train_label_lens"]
    X_rh = cache["real_holdout_images"]
    y_rh = cache["real_holdout_label_ids"]
    l_rh = cache["real_holdout_label_lens"]
    id_rh = [str(x) for x in cache["real_holdout_ids"]]
    print(f"train={X_tr.shape} val={X_va.shape} "
          f"real_train={X_rt.shape} real_holdout={X_rh.shape}", flush=True)

    train_model, logits_model = build_model()
    CKPT_DIR.mkdir(exist_ok=True)
    val_ds = make_ds(X_va, y_va, l_va, BATCH)

    if ft_only:
        pre_ckpt = CKPT_DIR / "pre_best.weights.h5"
        train_model.load_weights(str(pre_ckpt))
        print(f"pre_best 로드: {pre_ckpt}", flush=True)
    else:
        print("== synthetic pretrain ==", flush=True)
        pre_cb = [
            tf.keras.callbacks.ModelCheckpoint(
                str(CKPT_DIR / "pre_best.weights.h5"), save_best_only=True,
                save_weights_only=True, monitor="val_loss", mode="min"),
            tf.keras.callbacks.CSVLogger(str(CSV_LOG), append=False),
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=8, restore_best_weights=True),
        ]
        train_model.fit(
            make_ds(X_tr, y_tr, l_tr, BATCH, shuffle=True),
            validation_data=val_ds, epochs=EPOCHS_PRE, verbose=2,
            callbacks=pre_cb)

    # 파인튜닝은 고정 에폭 — 실데이터 적응 전에 합성 val_loss 가 오르는 건
    # 도메인 시프트 때문이라 여기 ES 를 걸면 1에폭 만에 학습이 죽는다(실측).
    print("== real finetune (augment) ==", flush=True)
    ft_cb = [tf.keras.callbacks.CSVLogger(str(CSV_LOG), append=True)]
    train_model.fit(
        make_ds(X_rt, y_rt, l_rt, FT_BATCH, shuffle=True, augment=True),
        epochs=ft_epochs, verbose=2, callbacks=ft_cb)

    # hold-out(파인튜닝에 안 쓴 실사진) 판독 — 캐시라 즉시
    print("== hold-out 판독 ==", flush=True)
    logits_all = logits_model.predict(
        X_rh[..., np.newaxis].astype(np.float32), batch_size=128, verbose=0)
    preds = greedy_decode(logits_all)
    gt_strs = ["".join(str(int(v)) for v in row if int(v) != NUM_CLASSES)
               for row in y_rh]
    preds_out = {cid: [p, g] for cid, p, g in zip(id_rh, preds, gt_strs)}
    OUT_PREDS.write_text(json.dumps(preds_out, ensure_ascii=False),
                         encoding="utf-8")
    exact = sum(1 for p, g in zip(preds, gt_strs) if p == g)
    print(f"hold-out exact: {exact}/{len(gt_strs)} "
          f"({100 * exact / max(len(gt_strs), 1):.1f}%)", flush=True)
    tr_logits = logits_model.predict(
        X_rt[:600][..., np.newaxis].astype(np.float32),
        batch_size=128, verbose=0)
    tr_preds = greedy_decode(tr_logits)
    tr_gts = ["".join(str(int(v)) for v in row if int(v) != NUM_CLASSES)
              for row in y_rt[:600]]
    tr_exact = sum(1 for p, g in zip(tr_preds, tr_gts) if p == g)
    print(f"학습셋 참고: {tr_exact}/600 "
          f"({100 * tr_exact / 600:.1f}%) — 학습셋과 격차가 크면 과적합",
          flush=True)
    for i in range(min(12, len(preds))):
        print(f"  GT {gt_strs[i]:>4}  pred {preds[i]!r}  ({id_rh[i]})", flush=True)

    logits_model.save(str(OUT_DIR))
    print("SAVED", OUT_DIR, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
