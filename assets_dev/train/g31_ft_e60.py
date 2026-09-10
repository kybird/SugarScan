# G31 — 크롭만 팔(세로 지터 0.08)을 기준선과 같은 예산(파인튜닝 60에폭)으로
# 다시 잰다.
#
# 왜 있는가: G30 의 크롭 팔 완전일치 87.79% 는 스크립트 기본 에폭(12)으로 낸
# 것인데, 기준선 reader_model 이 실제로 받은 파인튜닝 예산은 60에폭이었다
# (training_log.csv 마지막 런 — 최종 손실 0.1238. 크롭 팔은 12에폭 · 0.96 에서
# 하강 중에 멈춤). 손실이 8배 다른 두 모델을 비교한 것이라 격차를 프레이밍
# 탓으로 읽을 수 없다(docs/reports/G30-band-crop.md).
#
# 이 드라이버는 g30_ft_nojit.py 에서 **파인튜닝 에폭 수(12→60)와 산물 이름만**
# 바꾼 것이다. 레시피·하이퍼파라미터는 g30_ft_nojit.py 와 한 글자도 다르지 않다
# (세로 지터 0.08, FT_BATCH, 증강 스택, 출발점 = G30 사전학습 best 전부 동일).
# CSVLogger 와 ft_last.weights.h5 저장은 학습 결과에 영향을 주지 않는 기록용
# 추가며, 60에폭 손실 곡선이 보고서에 필요해서 넣었다.
#
# 이어붙이기(재개)는 의도적으로 없다 — 재시작으로 예산이 쌓이면 이 작업이
# 고치려는 문제를 다시 만든다. 중간에 죽으면 처음부터 다시 돌린다.
#
# 재현: python g31_ft_e60.py   (conda sugartrain)
#   - 입력: data_cache_v2_bandcrop.npz(G30 산물, 재사용) 와 그 사전학습 best
#     checkpoints_v2_bandcrop/pre_best.weights.h5 (G30 산물, 읽기만 함)
#   - 산물(모두 *_ty008_e60 이름. G30 산물 미건드림):
#     reader_model_bandcrop_ty008_e60 ·
#     reader_preds_bandcrop_ty008_e60.json(greedy 즉석 평가 — TTA 판독은
#     eval_reader.py --bandcrop 가 같은 경로에 덮어 쓴다) ·
#     training_log_bandcrop_ty008_e60.csv ·
#     checkpoints_v2_bandcrop_ty008_e60/ft_last.weights.h5
import json
import shutil
import sys
from pathlib import Path

import numpy as np

TRAIN = Path(__file__).resolve().parent
sys.path.insert(0, str(TRAIN))
import ctc_reader_v2 as C  # noqa: E402

C.CACHE = TRAIN / "data_cache_v2_bandcrop.npz"
C.CKPT_DIR = TRAIN / "checkpoints_v2_bandcrop_ty008_e60"
C.RESUME_PRE = C.CKPT_DIR / "resume_pre"
C.RESUME_FT = C.CKPT_DIR / "resume_ft"
C.RESUME_STATE = C.CKPT_DIR / "resume_state.json"
C.CSV_LOG = TRAIN / "training_log_bandcrop_ty008_e60.csv"
C.OUT_DIR = TRAIN / "reader_model_bandcrop_ty008_e60"
C.OUT_PREDS = TRAIN / "reader_preds_bandcrop_ty008_e60.json"
C.TRANS_Y = 0.08
FT_EPOCHS = 60

cache = np.load(str(C.CACHE))
X_rt = cache["real_train_images"]
y_rt = cache["real_train_label_ids"]
l_rt = cache["real_train_label_lens"]
X_rh = cache["real_holdout_images"]
y_rh = cache["real_holdout_label_ids"]
id_rh = [str(v) for v in cache["real_holdout_ids"]]
print(f"g31 ft: cache={C.CACHE.name} TRANS_Y={C.TRANS_Y} "
      f"epochs={FT_EPOCHS}", flush=True)

train_model, logits_model = C.build_model()
pre = TRAIN / "checkpoints_v2_bandcrop" / "pre_best.weights.h5"
train_model.load_weights(str(pre))
print(f"loaded {pre}", flush=True)

import tensorflow as tf  # noqa: E402
C.CKPT_DIR.mkdir(exist_ok=True)
train_model.fit(
    C.make_ds(X_rt, y_rt, l_rt, C.FT_BATCH, shuffle=True, augment=True),
    epochs=FT_EPOCHS, verbose=2,
    callbacks=[tf.keras.callbacks.CSVLogger(str(C.CSV_LOG))])
train_model.save_weights(str(C.CKPT_DIR / "ft_last.weights.h5"))

logits = logits_model.predict(X_rh[..., np.newaxis].astype(np.float32),
                              batch_size=128, verbose=0)
preds = C.greedy_decode(logits)
gt_strs = ["".join(str(int(v)) for v in row if int(v) != C.NUM_CLASSES - 1)
           for row in y_rh]
exact = sum(1 for p, g in zip(preds, gt_strs) if p == g)
print(f"g31 holdout exact(greedy): {exact}/{len(gt_strs)} "
      f"({100*exact/len(gt_strs):.1f}%)", flush=True)
C.OUT_PREDS.write_text(
    json.dumps({c: [p, g] for c, p, g in zip(id_rh, preds, gt_strs)},
               ensure_ascii=False), encoding="utf-8")
shutil.rmtree(C.OUT_DIR, ignore_errors=True)
logits_model.save(str(C.OUT_DIR))
print("saved", C.OUT_DIR, flush=True)
