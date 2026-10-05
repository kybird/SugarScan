# 리더 전량 학습 체인(2026-10-05 사람 질문 "검출기는 삼만장이나있는데?") —
# gen2r_s8k_v1(5,000장×150에폭, v11e 규모 패리티)이 95.1% 까지 왔으니,
# 다음 레버는 v11e 교훈("증량+에폭 둘 다 필요")대로 GEN2 29,878장 전부로
# 리더를 학습하는 것이다. 검출기는 29,878장 전부 이미 학습했고 스텝 확장은
# 퇴화(8k→16k 확신 사망)라 건드리지 않는다.
#
# ① step8000 상자를 GEN2 전량 위에 예측 ② 리더 150에폭(전량)
# ③ e2e(8k × 전량 리더). 기준: 8k×gen2r(5k) = 실패 1·오독 121·95.1%.
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DET = HERE / "band_out" / "tone" / "gen2_v1_step8000"
BOXES = HERE / "_diag" / "reader_boxes" / "GEN2full_s8k.jsonl"
ROUT = HERE / "reader_out" / "gen2full_s8k_v1"
LOG = HERE / "_diag" / "reader_full_chain.log"


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd, what):
    log(f"{what} 시작: {' '.join(cmd[1:])}")
    t0 = time.time()
    with LOG.open("a", encoding="utf-8") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT,
                           cwd=str(HERE))
    log(f"{what} 종료 rc={r.returncode} ({(time.time() - t0) / 60:.1f}분)")
    return r.returncode


log("체인 시작 — GEN2 전량(29,878) 리더 재학습")
rc = run([sys.executable, str(HERE / "make_reader_boxes.py"),
          "--set", "GEN2", "--ckpt", str(DET),
          "--out", str(BOXES)], "step8000 상자 예측(전량)")
if rc != 0:
    raise SystemExit("상자 예측 실패")
rc = run([sys.executable, str(HERE / "reader_crnn.py"), "train",
          "--set", str(HERE / "synth_coco" / "GEN2"),
          "--boxes", str(BOXES),
          "--epochs", "150", "--out", str(ROUT)], "리더 학습 150에폭(전량)")
if rc != 0:
    raise SystemExit("리더 학습 실패")
rc = run([sys.executable, str(HERE / "eval_e2e_bandnet.py"),
          "--ckpt_det", str(DET),
          "--ckpt_reader", str(ROUT / "best.pt"),
          "--tag", "gen2full8k"], "e2e 8k×전량 리더")
log(f"e2e 종료 rc={rc} — 기준: 8k×gen2r(5k)=실패 1·오독 121·95.1%")
