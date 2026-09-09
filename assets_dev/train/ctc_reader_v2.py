# CTC 리더 v2 — npz 캐시 + tf.data in-memory + 체크포인트 + 조기중단 + 재개.
#
# 실행:
#   python ctc_reader_v2.py            처음부터 (사전학습 40 → 파인튜닝 12)
#   python ctc_reader_v2.py resume     끊긴 지점부터 이어서
#   python ctc_reader_v2.py ft [N]     사전학습 best 에서 파인튜닝만 N 에폭
#   python ctc_reader_v2.py --bandcrop [--data-root DIR]  G30 — 세로형 밴드
#     크롭 캐시(data_cache_v2_bandcrop.npz)를 학습해 reader_model_bandcrop 로
#     낸다. 구조·에폭 수 불변. 바뀌는 것은 입력 프레이밍과 파인튜닝 증강의
#     세로 이동 RandomTranslation 0.08 → 0.15 (크롭 어긋남 내성. 가로 성분과
#     그 밖의 하이퍼파라미터는 불변)뿐이다.
# 모델 구조와 4입력+add_loss fit 패턴은 v1(ctc_reader.py)에서 검증된 것 그대로.
# 파인튜닝은 라벨 240장(화면 전체 rect), hold-out 평가는 eval_reader.py가 별도 수행
# (미라벨 1,767장 — 파인튜닝과 무겹침, 2026-08-30 리뷰에서 지적된 누수 구조의 수정판).
import argparse
import json
import time
from pathlib import Path

import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
CACHE = HERE / "data_cache_v2.npz"
CKPT_DIR = HERE / "checkpoints_v2"
# 재개용 체크포인트는 단계별로 나눈다. 한 디렉터리에 섞으면 파인튜닝 재개가
# 사전학습 체크포인트를 집어 조용히 다른 지점에서 이어 붙는다.
RESUME_PRE = CKPT_DIR / "resume_pre"
RESUME_FT = CKPT_DIR / "resume_ft"
RESUME_STATE = CKPT_DIR / "resume_state.json"
CSV_LOG = HERE / "training_log.csv"
OUT_DIR = HERE / "reader_model"

IN_H, IN_W = 160, 320
NUM_CLASSES = 11      # 0~9 + blank=10(마지막 인덱스)
MAX_LABEL = 3
SEQ_LEN = IN_W // 8   # conv 3회 s2 → 시간축 40
BATCH = 64
FT_BATCH = 16
EPOCHS_PRE = 40
EPOCHS_FT = 12   # 웹툴 진행 표시(TOTAL_EPOCHS=52)가 40+12 를 전제한다
SEED = 7
np.random.seed(SEED)
tf.random.set_seed(SEED)

# 파인튜닝 증강 RandomTranslation 의 세로(높이) 성분. 가로 성분은 0.08 고정.
# G30 --bandcrop 팔에서만 0.15 로 올린다 — 크롭 구간이 장마다 약간씩 어긋나도
# 견디게 하는 지터 넓히기(지시서 지정). 기본 경로(기준선 재현)는 0.08 을
# 유지한다. 이 값 외의 하이퍼파라미터는 어느 팔에서도 바꾸지 않는다.
TRANS_Y = 0.08


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
    # 프레이밍 흔들기 — 캐시가 박스+10% 여유로 잘려 있으므로, 그 여유 안에서
    # 줌·이동을 크게 주면 리더가 **빡빡한 크롭과 헐거운 크롭을 모두** 보게 된다.
    #
    # 왜 필요한가(2026-09-04): 검출 박스의 오른쪽 오차가 p5 −6% ~ p95 +28% 로
    # 넓게 퍼져 있는데, 리더는 지금까지 한 가지 프레이밍만 보고 학습했다.
    # 그래서 마지막 자리가 잘린 크롭이 들어오면 읽지 못하고 **지어낸다**
    # (949: 박스 밖 숫자를 0.993 확신으로 출력). 추론 시 고정 패딩으로는 못
    # 고친다 — 편차가 평균보다 커서 하나의 값으로 맞출 수 없다.
    tr = tf.keras.layers.RandomTranslation(TRANS_Y, 0.08, fill_mode="constant")
    zm = tf.keras.layers.RandomZoom(0.18, fill_mode="constant")
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


def _resolve_paths(bandcrop: bool, data_root):
    """--bandcrop/--data-root 로 데이터·산물 경로를 갈아 낀다(전역 재할당).

    플래그 없이 돌리면 종래 경로 그대로다. bandcrop 팔은 캐시·체크포인트·
    CSV 로그·모델·판독 json 전부 *_bandcrop 이름으로 나간다 — 기존 reader_model/
    data_cache_v2.npz/checkpoints_v2 를 덮어쓰는 일을 우연이 아니라 구조적으로
    막는다(G29 와 같은 규약. 2026-09-04 에 합성 라벨을 덮어써 복구에 시간을 쓴
    전례). 세로 지터 TRANS_Y 도 이 팔에서만 0.15 로 올린다.
    """
    global CACHE, CKPT_DIR, RESUME_PRE, RESUME_FT, RESUME_STATE
    global CSV_LOG, OUT_DIR, OUT_PREDS, TRANS_Y
    data = Path(data_root) if data_root else HERE
    sfx = "_bandcrop" if bandcrop else ""
    CACHE = data / f"data_cache_v2{sfx}.npz"
    CKPT_DIR = data / f"checkpoints_v2{sfx}"
    RESUME_PRE = CKPT_DIR / "resume_pre"
    RESUME_FT = CKPT_DIR / "resume_ft"
    RESUME_STATE = CKPT_DIR / "resume_state.json"
    CSV_LOG = data / f"training_log{sfx}.csv"
    OUT_DIR = data / f"reader_model{sfx}"
    OUT_PREDS = data / f"reader_preds{sfx}.json"
    if bandcrop:
        TRANS_Y = 0.15


def cache_signature():
    """데이터 캐시의 지문.

    **재개의 전제는 "같은 데이터"다.** 캐시를 다시 만든 뒤(예: EXIF 로더를 고친
    뒤) 옛 가중치에 이어 붙이면 두 데이터셋에 걸쳐 학습한 모델이 나오는데,
    그 사실이 로그 어디에도 남지 않는다. 지문이 다르면 재개를 거부한다.
    """
    st = CACHE.stat()
    return f"{st.st_size}:{int(st.st_mtime)}"


def load_resume_state():
    if not RESUME_STATE.exists():
        return None
    try:
        return json.loads(RESUME_STATE.read_text(encoding="utf-8"))
    except Exception:
        return None


class ResumePoint(tf.keras.callbacks.Callback):
    """매 에폭 끝에 "어디까지 갔는지" 를 가중치·옵티마이저와 함께 남긴다.

    best 체크포인트만으로는 재개할 수 없다. best 는 *가장 좋았던* 지점이지
    *마지막* 지점이 아니라서, 거기서 이어 붙이면 그 뒤 에폭이 조용히 사라진다.
    그래서 best 와 별개로 last 를 남긴다.
    """

    def __init__(self, manager, phase, sig, total):
        super().__init__()
        self.manager = manager
        self.phase = phase
        self.sig = sig
        self.total = total

    def on_epoch_end(self, epoch, logs=None):
        self.manager.save()
        RESUME_STATE.write_text(json.dumps({
            "phase": self.phase,
            "next_epoch": epoch + 1,
            "total_epochs": self.total,
            "cache_sig": self.sig,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, ensure_ascii=False), encoding="utf-8")


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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", nargs="?", default="fresh",
                    choices=("fresh", "resume", "ft"))
    ap.add_argument("epochs", nargs="?", type=int, default=None,
                    help="ft 모드의 에폭 수(기본 EPOCHS_FT)")
    ap.add_argument("--bandcrop", action="store_true",
                    help="bandcrop 캐시를 학습해 reader_model_bandcrop 로 낸다"
                         "(G30). 프레이밍과 세로 지터 0.15 외의 설정은 전부 불변")
    ap.add_argument("--data-root", type=Path, default=None,
                    help="데이터 루트(기본: 스크립트 폴더). 워크트리 실행 시 "
                         "메인 트리의 assets_dev/train 을 지정한다")
    args = ap.parse_args()
    _resolve_paths(args.bandcrop, args.data_root)
    print(f"cache={CACHE.name} → model={OUT_DIR.name} "
          f"(data root: {CACHE.parent})", flush=True)
    if args.bandcrop:
        print(f"RandomTranslation 세로 성분 = {TRANS_Y} (기준선 0.08)",
              flush=True)

    mode = args.mode
    # "ft": 사전학습 best 체크포인트에서 파인튜닝만 재실행 (ft [에폭수])
    ft_only = mode == "ft"
    ft_epochs = args.epochs if args.epochs is not None else EPOCHS_FT

    sig = cache_signature()
    state = load_resume_state() if mode == "resume" else None
    if mode == "resume":
        if state is None:
            print("재개할 지점이 없다 — 처음부터 시작한다.", flush=True)
        elif state.get("cache_sig") != sig:
            # 조용히 처음부터 돌면 몇 시간 뒤에야 알아챈다. 멈추고 이유를 말한다.
            print("재개 거부: 데이터 캐시가 바뀌었다.", flush=True)
            print(f"  체크포인트가 본 캐시: {state.get('cache_sig')}", flush=True)
            print(f"  지금 캐시:            {sig}", flush=True)
            print("  같은 데이터가 아니면 이어 붙일 수 없다 "
                  "(두 데이터셋에 걸쳐 학습한 모델이 되고 로그에 흔적이 안 남는다).",
                  flush=True)
            print("  처음부터 돌리려면: python ctc_reader_v2.py fresh", flush=True)
            return 3
        else:
            print(f"재개: {state['phase']} 단계 {state['next_epoch']} 에폭부터 "
                  f"(마지막 저장 {state.get('saved_at')})", flush=True)

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

    # 옵티마이저까지 함께 담는다. 가중치만 되살리면 Adam 의 모멘텀이 0 으로
    # 리셋돼 재개 직후 몇 에폭이 흔들린다.
    ckpt = tf.train.Checkpoint(model=train_model, optimizer=train_model.optimizer)
    pre_mgr = tf.train.CheckpointManager(ckpt, str(RESUME_PRE), max_to_keep=2)
    ft_mgr = tf.train.CheckpointManager(ckpt, str(RESUME_FT), max_to_keep=2)

    resume_phase = state["phase"] if state else None
    resume_epoch = int(state["next_epoch"]) if state else 0
    # 재개할 때는 CSV 를 이어 붙인다. 덮어쓰면 어디까지 갔는지 이력이 사라진다.
    pre_append = resume_phase == "pre"

    pre_initial = 0
    skip_pre = ft_only
    if resume_phase == "pre":
        if resume_epoch >= EPOCHS_PRE:
            print("사전학습은 이미 끝났다 — 파인튜닝부터 이어간다.", flush=True)
            skip_pre = True
        else:
            pre_initial = resume_epoch
        if pre_mgr.latest_checkpoint:
            ckpt.restore(pre_mgr.latest_checkpoint).expect_partial()
            print(f"복원: {pre_mgr.latest_checkpoint}", flush=True)
    elif resume_phase == "ft":
        skip_pre = True

    if skip_pre and resume_phase != "ft":
        pre_ckpt = CKPT_DIR / "pre_best.weights.h5"
        if pre_ckpt.exists():
            train_model.load_weights(str(pre_ckpt))
            print(f"pre_best 로드: {pre_ckpt}", flush=True)
        else:
            print(f"pre_best 없음 — 사전학습 없이 파인튜닝한다: {pre_ckpt}",
                  flush=True)

    if not skip_pre:
        print("== synthetic pretrain ==", flush=True)
        pre_cb = [
            tf.keras.callbacks.ModelCheckpoint(
                str(CKPT_DIR / "pre_best.weights.h5"), save_best_only=True,
                save_weights_only=True, monitor="val_loss", mode="min"),
            tf.keras.callbacks.CSVLogger(str(CSV_LOG), append=pre_append),
            # 재개하면 patience 카운터가 0 부터 다시 센다. 조기중단이 조금 늦게
            # 걸릴 뿐이라 감수한다 — 카운터를 이어 붙이려면 상태를 하나 더
            # 저장해야 하는데, 그 복잡도만큼의 값어치가 없다.
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=8, restore_best_weights=True),
            ResumePoint(pre_mgr, "pre", sig, EPOCHS_PRE),
        ]
        train_model.fit(
            make_ds(X_tr, y_tr, l_tr, BATCH, shuffle=True),
            validation_data=val_ds, epochs=EPOCHS_PRE, verbose=2,
            initial_epoch=pre_initial, callbacks=pre_cb)

    # 파인튜닝은 고정 에폭 — 실데이터 적응 전에 합성 val_loss 가 오르는 건
    # 도메인 시프트 때문이라 여기 ES 를 걸면 1에폭 만에 학습이 죽는다(실측).
    ft_initial = 0
    if resume_phase == "ft":
        ft_epochs = int(state.get("total_epochs", ft_epochs))
        ft_initial = resume_epoch
        if ft_mgr.latest_checkpoint:
            ckpt.restore(ft_mgr.latest_checkpoint).expect_partial()
            print(f"복원: {ft_mgr.latest_checkpoint}", flush=True)
        elif (CKPT_DIR / "pre_best.weights.h5").exists():
            # 파인튜닝 0 에폭에서 죽으면 ft 체크포인트가 없다. 사전학습 끝에서 시작.
            train_model.load_weights(str(CKPT_DIR / "pre_best.weights.h5"))
            ft_initial = 0
            print("ft 체크포인트 없음 — pre_best 에서 파인튜닝을 다시 시작한다.",
                  flush=True)
    if ft_initial >= ft_epochs:
        print("파인튜닝도 이미 끝났다 — 평가만 수행한다.", flush=True)
    else:
        print("== real finetune (augment) ==", flush=True)
        ft_cb = [
            tf.keras.callbacks.CSVLogger(str(CSV_LOG), append=True),
            ResumePoint(ft_mgr, "ft", sig, ft_epochs),
        ]
        train_model.fit(
            make_ds(X_rt, y_rt, l_rt, FT_BATCH, shuffle=True, augment=True),
            epochs=ft_epochs, verbose=2,
            initial_epoch=ft_initial, callbacks=ft_cb)

    # hold-out(파인튜닝에 안 쓴 실사진) 판독 — 캐시라 즉시
    print("== hold-out 판독 ==", flush=True)
    logits_all = logits_model.predict(
        X_rh[..., np.newaxis].astype(np.float32), batch_size=128, verbose=0)
    preds = greedy_decode(logits_all)
    # 패딩은 blank(=NUM_CLASSES-1=10)다. NUM_CLASSES(11)와 비교하면 걸러지지 않아
    # 2자리 라벨 '97' 이 '9710' 이 된다 — 2자리 표본(전체의 20%)이 전부 오답으로
    # 집계돼 완전일치가 실제보다 18pp 낮게 찍혔다.
    gt_strs = ["".join(str(int(v)) for v in row if int(v) != NUM_CLASSES - 1)
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
    tr_gts = ["".join(str(int(v)) for v in row if int(v) != NUM_CLASSES - 1)
              for row in y_rt[:600]]
    tr_exact = sum(1 for p, g in zip(tr_preds, tr_gts) if p == g)
    print(f"학습셋 참고: {tr_exact}/600 "
          f"({100 * tr_exact / 600:.1f}%) — 학습셋과 격차가 크면 과적합",
          flush=True)
    for i in range(min(12, len(preds))):
        print(f"  GT {gt_strs[i]:>4}  pred {preds[i]!r}  ({id_rh[i]})", flush=True)

    logits_model.save(str(OUT_DIR))
    print("SAVED", OUT_DIR, flush=True)
    # 끝까지 갔으므로 재개 지점을 지운다. 남겨 두면 다음 `resume` 이 끝난 학습을
    # 이어가려 한다.
    RESUME_STATE.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
