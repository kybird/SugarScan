# GEN2 자동 체인 — 굽기 완료 대기 → GPU idle 게이트 → 검출기 학습 → 실사진 평가.
# 사람 승인(2026-10-04 "좋다 진행")으로 GEN1 30,000장 학습까지 무인 진행.
# 학습 처방은 현행 배포 검출기(atone_tg640w15)와 동일 예산(size 640·width 1.5
# ·steps 16000 — TG 30,000장) — 세대 교체 효과만 가르려면 예산이 같아야 한다
# ([[experiment-budget-parity]]).
# 사용: nohup python _diag/gen1_chain.py > _diag/gen2_chain.log 2>&1 &
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
GEN2 = HERE / "synth_coco" / "GEN2"
CKPT = HERE / "band_out" / "tone" / "gen2_v1"
TRAIN = [sys.executable, str(HERE / "train_band.py"), "--data", str(GEN2),
         "--out", str(CKPT), "--size", "640", "--width", "1.5",
         "--steps", "16000",
         # 2026-10-05 사람: "검출기 훈련하면서 구간별로 체크포인트 남기자"
         # — 2,000스텝마다 <out>_step<N>.pt (덮어쓰지 않음, 개별 파일).
         # 학습 곡선을 되짚어 '언제부터 나빠졌나/좋아졌나'를 본다.
         "--save-every", "2000"]
EVAL = [sys.executable, str(HERE / "eval_band_real.py"),
        "--ckpt", str(CKPT), "--exclude-accepted", "--no-overlay"]
LOG = HERE / "_diag" / "gen2_chain.log"


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def gen2_ready():
    try:
        j = json.loads((GEN2 / "annotations" / "instances_train2017.json")
                       .read_text(encoding="utf-8"))
        # 29,878 = 30,000 에서 사람 GT 최소 면적비 밑 122판을 뺀 수
        # (patch_gen2_minfrac.py, 2026-10-05 — "작은 것은 학습하지 않는다").
        return len(j.get("images", [])) >= 29878
    except Exception:
        return False


def gpu_util():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu",
             "--format=csv,noheader,nounits"], text=True)
        return int(out.strip().splitlines()[0])
    except Exception:
        return 100   # 판정 불가면 기다린다(잘못 훈련 시작보다 안전)


# 학습 뒤 전량 e2e 까지 잰다(2026-10-04 기준선: gen1_v1 실패 15·오독 254·판독률 89.3%).
E2E = [sys.executable, str(HERE / "eval_e2e_bandnet.py"),
       "--ckpt_det", str(CKPT), "--tag", "gen2"]
log("체인 시작 — GEN2 굽기 완료 대기")
while not gen2_ready():
    time.sleep(120)
log("GEN2 코퍼스 완료 감지 — GPU idle 대기(연속 3회 util<25%)")
idle = 0
while idle < 3:
    u = gpu_util()
    idle = idle + 1 if u < 25 else 0
    if idle < 3:
        time.sleep(120)
log(f"GPU idle 확인 — 학습 시작: {' '.join(TRAIN[1:])}")
with LOG.open("a", encoding="utf-8") as f:
    r = subprocess.run(TRAIN, stdout=f, stderr=subprocess.STDOUT, cwd=str(HERE))
log(f"학습 종료 rc={r.returncode}")
if r.returncode == 0:
    log("실사진 홀드아웃 평가 시작(346장·스케일 게이트)")
    with LOG.open("a", encoding="utf-8") as f:
        r2 = subprocess.run(EVAL, stdout=f, stderr=subprocess.STDOUT, cwd=str(HERE))
    log(f"평가 종료 rc={r2.returncode} — 기준 gen1_v1(실패 15·IoU 홀드아웃) 과 비교할 것")
    log("e2e 전량 2,511장 시작")
    with LOG.open("a", encoding="utf-8") as f:
        r3 = subprocess.run(E2E, stdout=f, stderr=subprocess.STDOUT, cwd=str(HERE))
    log(f"e2e 종료 rc={r3.returncode} — _diag/e2e_bandnet/gen2.jsonl")
else:
    log("학습 실패 — 수동 확인 필요")
