# GEN2 8k 검출기 채택 → 리더 재학습 체인(2026-10-05 사람 결정:
# "8k 채택한다. 그리고 8k 결과를 가지고 리더기를 새로학습한다").
# 설계 원칙('검출 예측 상자로 학습 = 배포 동등', make_reader_boxes.py 머리글)
# 에 따라 리더 학습 크롭은 **채택 검출기(step8000)의 예측 상자**로 자른다.
#
# 단계: ① GEN2 에서 5,000장 결정적 부분집합 GEN2R 조성(v11e 레시피 동일
# 규모 — 5,000장×150에폭과의 비교를 위해) ② step8000 상자 예측 ③ 리더
# 학습 150에폭 ④ e2e(8k 검출기 × 새 리더).
import json
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
GEN2 = HERE / "synth_coco" / "GEN2"
GEN2R = HERE / "synth_coco" / "GEN2R"
DET = HERE / "band_out" / "tone" / "gen2_v1_step8000"
BOXES = HERE / "_diag" / "reader_boxes" / "GEN2R_s8k.jsonl"
ROUT = HERE / "reader_out" / "gen2r_s8k_v1"
LOG = HERE / "_diag" / "reader8k_chain.log"
N_SUB = 5000


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def step1_subset():
    if (GEN2R / "annotations" / "instances_train2017.json").exists():
        log("GEN2R 이미 있음 — 건너뜀")
        return
    j = json.loads((GEN2 / "annotations" / "instances_train2017.json")
                   .read_text(encoding="utf-8"))
    rng = random.Random(20261005)
    keep = set(rng.sample([im["id"] for im in j["images"]], N_SUB))
    j["images"] = [im for im in j["images"] if im["id"] in keep]
    j["annotations"] = [a for a in j["annotations"]
                        if a["image_id"] in keep]
    (GEN2R / "annotations").mkdir(parents=True, exist_ok=True)
    (GEN2R / "train2017").mkdir(parents=True, exist_ok=True)
    (GEN2R / "annotations" / "instances_train2017.json").write_text(
        json.dumps(j), encoding="utf-8")
    keep_names = {im["file_name"].rsplit(".", 1)[0] for im in j["images"]}
    with (GEN2R / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for ln in (GEN2 / "manifest.jsonl").read_text(
                encoding="utf-8").splitlines():
            if ln.strip() and ln.split('"id": "', 1)[-1].split('"', 1)[0] \
                    in keep_names:
                f.write(ln + "\n")
    for im in j["images"]:
        src = GEN2 / "train2017" / im["file_name"]
        dst = GEN2R / "train2017" / im["file_name"]
        if not dst.exists():
            shutil.copy2(src, dst)
    log(f"GEN2R 조성: {len(j['images'])}장")


def run(cmd, what):
    log(f"{what} 시작: {' '.join(cmd[1:])}")
    t0 = time.time()
    with LOG.open("a", encoding="utf-8") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT,
                           cwd=str(HERE))
    log(f"{what} 종료 rc={r.returncode} ({(time.time() - t0) / 60:.1f}분)")
    return r.returncode


log("체인 시작 — GEN2R 조성")
step1_subset()
rc = run([sys.executable, str(HERE / "make_reader_boxes.py"),
          "--set", "GEN2R", "--ckpt", str(DET),
          "--out", str(BOXES)], "step8000 상자 예측")
if rc != 0:
    raise SystemExit("상자 예측 실패")
rc = run([sys.executable, str(HERE / "reader_crnn.py"), "train",
          "--set", str(GEN2R),
          "--boxes", str(BOXES),
          "--epochs", "150", "--out", str(ROUT)], "리더 학습 150에폭")
if rc != 0:
    raise SystemExit("리더 학습 실패")
rc = run([sys.executable, str(HERE / "eval_e2e_bandnet.py"),
          "--ckpt_det", str(DET),
          "--ckpt_reader", str(ROUT / "best.pt"),
          "--tag", "gen2r8k"], "e2e 8k×새 리더")
log(f"e2e 종료 rc={rc} — _diag/e2e_bandnet/gen2r8k.jsonl "
    "(기준: 8k×v2.1 = 실패 1(2317)·판독률 90.0%)")
