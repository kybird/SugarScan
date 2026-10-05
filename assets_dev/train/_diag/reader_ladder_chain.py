# 리더 데이터 사다리 체인(2026-10-05 사람: "한번에 끝까지 올리지말고 조금씩
# 늘리자. 중간에 체크포인트 저장방식으로 하면") — GEN2 전량을 한 번에 쓰지
# 않고 **중첩 부분집합 점마다 from-scratch 학습 + 체크포인트 + e2e** 로
# 올린다(Gmaster 스케일 곡선 규율: 매 점 새 시드 금지 — 앞 점의 패널이
# 뒤 점에 그대로 들어가므로 점 간 차이가 순수하게 데이터 양이다).
#
# 점: 5,000(완료 — gen2r_s8k_v1, 95.1%) ⊂아님 주의: 아래 사다리는 자체
# 중첩 순서(seed 고정 전체 셔플의 앞두름)이며, 5,000 점은 별도 추첨이라
# 곡선의 참고점이다. 이후 10,000·15,000·20,000·25,000·29,878 은 서로 중첩.
# 각 점의 best.pt 는 reader_out/gen2lad<N>_s8k/ 에 따로 남는다 — 어느
# 점에서든 중단해도 그 점까지의 체크포인트는 확보된다.
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
LOG = HERE / "_diag" / "reader_ladder_chain.log"
POINTS = (10000, 15000, 20000, 25000, 29878)


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


log("사다리 체인 시작 — 점: " + "/".join(str(p) for p in POINTS))

# ① step8000 상자를 GEN2 전량 위에(완료 파일이 있으면 재사용)
if not BOXES_FULL.exists() or sum(1 for _ in BOXES_FULL.open(
        encoding="utf-8")) < 29878:
    BOXES_FULL.unlink(missing_ok=True)
    rc = run([sys.executable, str(HERE / "make_reader_boxes.py"),
              "--set", "GEN2", "--ckpt", str(DET),
              "--out", str(BOXES_FULL)], "step8000 상자 예측(전량)")
    if rc != 0:
        raise SystemExit("상자 예측 실패")

rows = [json.loads(l) for l in BOXES_FULL.read_text(
    encoding="utf-8").splitlines() if l.strip()]
# 중첩 순서 — id 정렬 후 고정 시드 셔플(재실행해도 같은 순서)
order = [r["file_name"].rsplit(".", 1)[0] for r in rows]
random.Random(20261005).shuffle(order)
rank = {pid: i for i, pid in enumerate(order)}

for n in POINTS:
    keep = {p for p, i in rank.items() if i < n}
    bf = BOXDIR / f"GEN2lad{n}_s8k.jsonl"
    with bf.open("w", encoding="utf-8") as f:
        for r in rows:
            if r["file_name"].rsplit(".", 1)[0] in keep:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"[{n}] 학습 상자 {sum(1 for _ in bf.open(encoding='utf-8'))}장")
    rc = run([sys.executable, str(HERE / "reader_crnn.py"), "train",
              "--set", str(GEN2), "--boxes", str(bf),
              "--epochs", "150",
              "--out", str(HERE / "reader_out" / f"gen2lad{n}_s8k")],
             f"[{n}] 리더 학습 150에폭")
    if rc != 0:
        raise SystemExit(f"[{n}] 리더 학습 실패")
    rc = run([sys.executable, str(HERE / "eval_e2e_bandnet.py"),
              "--ckpt_det", str(DET),
              "--ckpt_reader", str(HERE / "reader_out" / f"gen2lad{n}_s8k"
                                   / "best.pt"),
              "--tag", f"gen2lad{n}"], f"[{n}] e2e")
    log(f"[{n}] 점 완료 — 결과 _diag/e2e_bandnet/gen2lad{n}.jsonl "
        "(기준 5,000점: 실패 1·오독 121·95.1%)")

log("사다리 완료")
