# G30 — 크롭만 남은 팔(세로 지터 0.08 = 기준선 값)의 파인튜닝 드라이버.
#
# 왜 있는가: 지시서 스펙(세로 0.15)이 파인튜닝을 붕괴시켰다(손실 5.40 에서
# 동결, TTA 완전일치 1.34%). 같은 캐시에서 0.08 만 바꾸면 즉시 수렴한다
# (차분 실험, docs/reports/G30-band-crop.md). 이 스크립트는 "프레이밍(크롭)만
# 기준선과 다르고 나머지는 전부 기준선 레시피"인 팔을 내기 위한 것이다.
#
# 재현: python g30_ft_nojit.py   (conda sugartrain)
#   - 입력: data_cache_v2_bandcrop.npz 와 그 사전학습 best
#     (checkpoints_v2_bandcrop/pre_best.weights.h5 — 사전학습은 증강이 없으므로
#     스펙 팔과 동일한 출발점이다)
#   - 산물: reader_model_bandcrop_ty008 · reader_preds_bandcrop_ty008.json ·
#     training_log_bandcrop_ty008.csv (모두 *_ty008 이름. 기존 산물 미건드림)
import json
import shutil
import sys
from pathlib import Path

import numpy as np

TRAIN = Path(__file__).resolve().parent
sys.path.insert(0, str(TRAIN))
import ctc_reader_v2 as C  # noqa: E402

C.CACHE = TRAIN / "data_cache_v2_bandcrop.npz"
C.CKPT_DIR = TRAIN / "_diag" / "G30" / "probe_ckpt"
C.RESUME_PRE = C.CKPT_DIR / "resume_pre"
C.RESUME_FT = C.CKPT_DIR / "resume_ft"
C.RESUME_STATE = C.CKPT_DIR / "resume_state.json"
C.CSV_LOG = TRAIN / "training_log_bandcrop_ty008.csv"
C.OUT_DIR = TRAIN / "reader_model_bandcrop_ty008"
C.OUT_PREDS = TRAIN / "reader_preds_bandcrop_ty008.json"
C.TRANS_Y = 0.08
FT_EPOCHS = 12

cache = np.load(str(C.CACHE))
X_rt = cache["real_train_images"]
y_rt = cache["real_train_label_ids"]
l_rt = cache["real_train_label_lens"]
X_rh = cache["real_holdout_images"]
y_rh = cache["real_holdout_label_ids"]
id_rh = [str(v) for v in cache["real_holdout_ids"]]
print(f"probe ft: cache={C.CACHE.name} TRANS_Y={C.TRANS_Y} "
      f"epochs={FT_EPOCHS}", flush=True)

train_model, logits_model = C.build_model()
pre = TRAIN / "checkpoints_v2_bandcrop" / "pre_best.weights.h5"
train_model.load_weights(str(pre))
print(f"loaded {pre}", flush=True)

import tensorflow as tf  # noqa: E402
train_model.fit(
    C.make_ds(X_rt, y_rt, l_rt, C.FT_BATCH, shuffle=True, augment=True),
    epochs=FT_EPOCHS, verbose=2)

logits = logits_model.predict(X_rh[..., np.newaxis].astype(np.float32),
                              batch_size=128, verbose=0)
preds = C.greedy_decode(logits)
gt_strs = ["".join(str(int(v)) for v in row if int(v) != C.NUM_CLASSES - 1)
           for row in y_rh]
exact = sum(1 for p, g in zip(preds, gt_strs) if p == g)
print(f"probe holdout exact: {exact}/{len(gt_strs)} "
      f"({100*exact/len(gt_strs):.1f}%)", flush=True)
C.OUT_PREDS.write_text(
    json.dumps({c: [p, g] for c, p, g in zip(id_rh, preds, gt_strs)},
               ensure_ascii=False), encoding="utf-8")
shutil.rmtree(C.OUT_DIR, ignore_errors=True)
logits_model.save(str(C.OUT_DIR))
print("saved", C.OUT_DIR, flush=True)
