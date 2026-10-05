# 정밀 사다리 체인(2026-10-05 사람: "5000점으로 돌아가서 1000단위로 올리면서
# 체크포인트 남기자. 스윗포인트 찾아보자") — 15,000점에서 증량 악화가
# 확정되면(오독 > 121) 기존 사다리(10k→15k→…)는 중단하고, 같은 중첩
# 순서(reader_ladder_chain 과 동일한 Random(20261005) 전체 셔플)로
# 5,000부터 1,000단위 점을 잰다. 5,000점 재측정을 포함하는 이유: 기존
# gen2r 의 5,000점은 별도 추첨이라 점 간 비교에 추첨 잡음이 섞여 있다 —
# 같은 순서의 앞두름으로 다시 재면 데이터 양 효과와 추첨 잡음이 갈린다.
import json
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DET = HERE / "band_out" / "tone" / "gen2_v1_step8000"
GEN2 = HERE / "synth_coco" / "GEN2"
BOXDIR = HERE / "_diag" / "reader_boxes"
BOXES_FULL = BOXDIR / "GEN2full_s8k.jsonl"
LOG = HERE / "_diag" / "reader_fine_ladder.log"
POINTS = (5000, 6000, 7000, 8000, 9000)


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd, what):
    log(f"{what} 시작")
    t0 = time.time()
    with LOG.open("a", encoding="utf-8") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT,
                           cwd=str(HERE))
    log(f"{what} 종료 rc={r.returncode} ({(time.time() - t0) / 60:.1f}분)")
    return r.returncode


log("정밀 사다리 시작 — 점: " + "/".join(str(p) for p in POINTS))
rows = [json.loads(l) for l in BOXES_FULL.read_text(
    encoding="utf-8").splitlines() if l.strip()]
# reader_ladder_chain 과 완전히 같은 순서(중첩 비교의 정본)
order = [r["file_name"].rsplit(".", 1)[0] for r in rows]
random.Random(20261005).shuffle(order)
rank = {pid: i for i, pid in enumerate(order)}

for n in POINTS:
    keep = {p for p, i in rank.items() if i < n}
    bf = BOXDIR / f"GEN2fine{n}_s8k.jsonl"
    with bf.open("w", encoding="utf-8") as f:
        for r in rows:
            if r["file_name"].rsplit(".", 1)[0] in keep:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rc = run([sys.executable, str(HERE / "reader_crnn.py"), "train",
              "--set", str(GEN2), "--boxes", str(bf),
              "--epochs", "150",
              "--out", str(HERE / "reader_out" / f"gen2fine{n}_s8k")],
             f"[{n}] 리더 학습 150에폭")
    if rc != 0:
        raise SystemExit(f"[{n}] 리더 학습 실패")
    rc = run([sys.executable, str(HERE / "eval_e2e_bandnet.py"),
              "--ckpt_det", str(DET),
              "--ckpt_reader", str(HERE / "reader_out" / f"gen2fine{n}_s8k"
                                   / "best.pt"),
              "--tag", f"gen2fine{n}"], f"[{n}] e2e")
    log(f"[{n}] 점 완료 — _diag/e2e_bandnet/gen2fine{n}.jsonl")
log("정밀 사다리 완료")
