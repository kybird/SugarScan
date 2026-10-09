# 밤샘 검출기 개선 체인 (2026-10-09 사람: "전부다 밤샘돌려라").
# B: topk 디코드 전량 시뮬(회복/손실/상자변경 + e2e 판독률)
# A: 실촉 K=5 검출기 파인튜닝(기기층화 폴드 × 리플레이 1:1 · 폴드별
#    IoU/포함률/e2e vs 배포 기준선 · foldall 배포후보)
# C: 가로형 '반쪽 상자' 7장 왼쪽 경쟁줄 실재 진단(GEN3 축 설계의 재료)
# 각 단계는 try/except 로 격리 — 한 단계 죽어도 나머지는 돈다.
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
PY = sys.executable
LOG = HERE / "overnight_det_chain.log"
DET = TRAIN / "band_out" / "tone" / "gen2_v1_step8000"
STEPS = 1200
LR = 2e-4
BATCH = 8


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(args, tmo=None):
    log("실행: " + " ".join(str(a) for a in args[1:]))
    t0 = time.time()
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       cwd=str(TRAIN), timeout=tmo)
    tail = "\n".join((r.stdout or "").splitlines()[-14:])
    if tail:
        log("  출력:\n" + "\n".join("    " + l for l in tail.splitlines()))
    if r.returncode != 0:
        err = "\n".join((r.stderr or "").splitlines()[-10:])
        log(f"  실패 rc={r.returncode}\n" + "\n".join("    " + l for l in err.splitlines()))
    log(f"  종료 rc={r.returncode} ({time.time()-t0:.0f}초)")
    return r.returncode


log("=== 밤샘 검출기 개선 체인 시작 ===")

# ── B: topk 디코드 시뮬 ─────────────────────────────────────────────
try:
    log("[B] topk 디코드 전량 시뮬 시작")
    rc = run([PY, str(HERE / "topk_sim_gen2.py")], tmo=3600)
    log(f"[B] 종료 rc={rc}")
except Exception as e:
    log(f"[B] 예외: {e}")

# ── A: 실촉 K=5 파인튜닝 ────────────────────────────────────────────
try:
    log("[A] 폴드/어노테이션 생성")
    rc = run([PY, str(HERE / "build_det_ft_folds.py")], tmo=600)
    if rc == 0:
        seeds = {"fold0": 20261010, "fold1": 20261011, "fold2": 20261012,
                 "fold3": 20261013, "fold4": 20261014, "foldall": 20261015}
        for name in ("fold0", "fold1", "fold2", "fold3", "fold4", "foldall"):
            out = TRAIN / "band_out" / "tone" / f"ftk5_{name}"
            log(f"[A] {name} 학습 시작 (resume gen2_v1_step8000 · "
                f"{STEPS}스텝 · lr {LR})")
            rc2 = run([PY, str(TRAIN / "train_band.py"),
                       "--data", str(HERE / "det_ft" / name),
                       "--out", str(out), "--resume", str(DET),
                       "--size", "640", "--width", "1.5",
                       "--steps", str(STEPS), "--batch", str(BATCH),
                       "--lr", str(LR), "--workers", "2",
                       "--seed", str(seeds[name]),
                       "--log", "200"], tmo=7200)
            if rc2 != 0:
                continue
            tag = name if name != "foldall" else "foldall_시료내"
            run([PY, str(HERE / "det_ft_eval.py"), "--ckpt", str(out),
                 "--ids", str(HERE / "det_ft" / name / "holdout_ids.json"),
                 "--tag", tag], tmo=1800)
            if name != "foldall":     # 같은 id 집합의 배포 기준선
                run([PY, str(HERE / "det_ft_eval.py"), "--ckpt", str(DET),
                     "--ids", str(HERE / "det_ft" / name / "holdout_ids.json"),
                     "--tag", f"base_{name}"], tmo=1800)
        # 집계
        agg = {}
        for p in sorted((HERE / "det_ft").glob("eval_*.json")):
            agg[p.stem[5:]] = json.loads(p.read_text(encoding="utf-8"))
        pooled = {}
        for side in ("", "base_"):
            ious = [v["iou_median"] for k, v in agg.items()
                    if k.startswith(side + "fold") and "시료" not in k]
            e2es = [v["e2e_rate"] for k, v in agg.items()
                    if k.startswith(side + "fold") and "시료" not in k]
            pooled["ft" if side == "" else "base"] = dict(
                folds_iou_median=round(sum(ious)/max(1, len(ious)), 4),
                folds_e2e_mean=round(sum(e2es)/max(1, len(e2es)), 4))
        (HERE / "det_ft_k5_result.json").write_text(
            json.dumps(dict(per_fold=agg, pooled=pooled), ensure_ascii=False,
                       indent=1), encoding="utf-8")
        log(f"[A] 집계 완료 -> det_ft_k5_result.json · {pooled}")
except Exception as e:
    log(f"[A] 예외: {e}")

# ── C: 가로형 경쟁줄 진단 ───────────────────────────────────────────
try:
    log("[C] 가로형 왼쪽 스트립 진단 시작")
    rc = run([PY, str(HERE / "horizontal_left_diag.py")], tmo=900)
    log(f"[C] 종료 rc={rc}")
except Exception as e:
    log(f"[C] 예외: {e}")

log("=== 밤샘 체인 종료 — 아침 보고 대기 ===")
