# -*- coding: utf-8 -*-
"""재개 기계장치 스모크 테스트 — 실제 학습 산출물은 건드리지 않는다.

실행: conda run -n sugartrain python smoke_resume.py  (약 1분, 무작위 데이터 32장)

검증하는 것:
  1) ResumePoint 가 매 에폭 체크포인트와 resume_state.json 을 남기는가
  2) 새 프로세스처럼 모델을 다시 만들어 restore 하면 가중치가 같은가
  3) 옵티마이저 슬롯(Adam 모멘텀)까지 복원되는가
  4) initial_epoch 로 이어서 돌면 에폭 번호가 이어지는가
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import tensorflow as tf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ctc_reader_v2 as M  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="resume_smoke_"))
M.RESUME_STATE = TMP / "resume_state.json"

N, H, W = 32, M.IN_H, M.IN_W
rng = np.random.default_rng(0)
X = rng.integers(0, 255, size=(N, H, W), dtype=np.uint8)
y = rng.integers(0, 10, size=(N, M.MAX_LABEL)).astype(np.int32)
lens = np.full((N,), M.MAX_LABEL, dtype=np.int32)
ds = M.make_ds(X, y, lens, 8, shuffle=False)


def fresh():
    tf.keras.utils.set_random_seed(7)
    tm, _ = M.build_model()
    return tm


# ── 1) 2에폭 돌리며 체크포인트를 남긴다 ──
m1 = fresh()
ck1 = tf.train.Checkpoint(model=m1, optimizer=m1.optimizer)
mgr1 = tf.train.CheckpointManager(ck1, str(TMP / "pre"), max_to_keep=2)
m1.fit(ds, epochs=2, verbose=0,
       callbacks=[M.ResumePoint(mgr1, "pre", "SIG", 4)])

state = json.loads(M.RESUME_STATE.read_text(encoding="utf-8"))
assert state["phase"] == "pre", state
assert state["next_epoch"] == 2, state
assert state["cache_sig"] == "SIG", state
assert mgr1.latest_checkpoint, "체크포인트가 안 만들어졌다"
print("1) 체크포인트+상태 저장 OK ->", state["next_epoch"], "에폭까지")

w_before = [v.numpy().copy() for v in m1.trainable_variables]
# Adam 슬롯 하나를 골라 기억해 둔다(0 이 아닌 것으로).
slot_before = None
for v in m1.optimizer.variables():
    a = v.numpy()
    if np.abs(a).sum() > 0:
        slot_before = (v.name, a.copy())
        break
assert slot_before is not None, "옵티마이저 슬롯이 비어 있다"

# ── 2) 새 프로세스처럼 다시 만들어 복원 ──
m2 = fresh()
ck2 = tf.train.Checkpoint(model=m2, optimizer=m2.optimizer)
mgr2 = tf.train.CheckpointManager(ck2, str(TMP / "pre"), max_to_keep=2)
w_random = [v.numpy().copy() for v in m2.trainable_variables]
ck2.restore(mgr2.latest_checkpoint).expect_partial()

w_after = [v.numpy().copy() for v in m2.trainable_variables]
same = all(np.allclose(a, b) for a, b in zip(w_before, w_after))
differed = any(not np.allclose(a, b) for a, b in zip(w_random, w_before))
assert differed, "학습 전후 가중치가 같다 — 테스트가 무의미하다"
assert same, "복원한 가중치가 저장 시점과 다르다"
print("2) 가중치 복원 OK")

# ── 3) 옵티마이저 슬롯 복원 (변수 생성 후 지연 복원이 풀린다) ──
m2.fit(ds, epochs=3, verbose=0, initial_epoch=2,
       callbacks=[M.ResumePoint(mgr2, "pre", "SIG", 4)])
name, arr = slot_before
restored = {v.name: v.numpy() for v in m2.optimizer.variables()}
assert name in restored, f"슬롯 {name} 이 없다"
assert not np.allclose(restored[name], np.zeros_like(arr)), \
    "옵티마이저 슬롯이 0 으로 리셋됐다 — 모멘텀이 안 살아났다"
print("3) 옵티마이저 슬롯 살아 있음 OK")

# ── 4) 에폭 번호가 이어진다 ──
state2 = json.loads(M.RESUME_STATE.read_text(encoding="utf-8"))
assert state2["next_epoch"] == 3, state2
print("4) initial_epoch 이어짐 OK ->", state2["next_epoch"])

shutil.rmtree(TMP, ignore_errors=True)
print("\n재개 기계장치 전부 통과")
