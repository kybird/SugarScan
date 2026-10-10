# 리더 실촉 K=5 파인튜닝 체인 — 새 검출기(ftk5_g0.06)와 페어 (2026-10-09).
# ① 사전 크롭(g0.06 상자로 실촬 전량) ② 합성 리플레이 상자(g0.06 이 합성 패널)
# ③ 폴드 세트 조립 ④ 폴드마다 train(웜스타트 gen2lad25000 · 25에폭 · lr 1e-4)
# + ft/base 짝평가 ⑤ foldall 학습 + 전량 e2e ⑥ 집계(McNemar 폴합).
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
PY = sys.executable
LOG = HERE / "overnight_reader_ft_chain.log"
DET = TRAIN / "band_out" / "tone" / "ftk5_g0.06"
BASE_READER = TRAIN / "reader_out" / "gen2lad25000_s8k" / "best.pt"
EPOCHS = 25


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(args, tmo=7200):
    log("실행: " + " ".join(str(a) for a in args[1:]))
    t0 = time.time()
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(TRAIN),
                       timeout=tmo)
    tail = "\n".join((r.stdout or "").splitlines()[-10:])
    if tail:
        log("  출력:\n" + "\n".join("    " + l for l in tail.splitlines()))
    if r.returncode != 0:
        err = "\n".join((r.stderr or "").splitlines()[-8:])
        log(f"  실패 rc={r.returncode}\n" + "\n".join("    " + l for l in err.splitlines()))
    log(f"  종료 rc={r.returncode} ({time.time()-t0:.0f}초)")
    return r.returncode


log("=== 리더 실촉 K=5 체인 시작 (검출기 ftk5_g0.06 페어) ===")
try:
    log("[1] 실촬 크롭+폴드")
    cm = HERE / "reader_ft" / "crops_manifest.jsonl"
    if cm.exists() and sum(1 for _ in cm.open(encoding="utf-8")) >= 2500:
        log("  이미 완료 — 건너뜀")
    elif run([PY, str(HERE / "reader_ft_precrop.py")], tmo=3600) != 0:
        raise SystemExit("크롭 실패")
    log("[2] 합성 리플레이 상자 (g0.06 → GEN2 전량)")
    sb = HERE / "reader_boxes" / "GEN2full_ftk5g006.jsonl"
    if sb.exists() and sum(1 for _ in sb.open(encoding="utf-8")) >= 29000:
        log("  이미 완료 — 건너뜀")
    elif run([PY, str(TRAIN / "make_reader_boxes.py"), "--set", "GEN2",
            "--ckpt", str(DET),
            "--out", str(HERE / "reader_boxes" / "GEN2full_ftk5g006.jsonl")],
           tmo=14400) != 0:
        raise SystemExit("합성 상자 실패")
    log("[3] 폴드 세트 조립")
    if run([PY, str(HERE / "build_reader_ft_folds.py")], tmo=600) != 0:
        raise SystemExit("세트 조립 실패")
    for name in ("fold0", "fold1", "fold2", "fold3", "fold4", "foldall"):
        fdir = HERE / "reader_ft" / name
        out = TRAIN / "reader_out" / f"rftk5_{name}"
        log(f"[4] {name} 리더 학습 (웜스타트 25에폭)")
        if (out / "best.pt").exists():
            log("  이미 학습됨 — 건너뜀")
        elif run([PY, str(TRAIN / "reader_crnn.py"), "train",
                "--set", str(fdir), "--boxes", str(fdir / "boxes_g006.jsonl"),
                "--out", str(out), "--resume", str(HERE / "reader_ft" / "warm_base.pt"),
                "--epochs", str(EPOCHS), "--lr", "1e-4"], tmo=28800) != 0:
            continue
        if name == "foldall":
            log("[5] foldall 전량 e2e (검출기 g0.06 × ft 리더)")
            run([PY, str(TRAIN / "eval_e2e_bandnet.py"),
                 "--ckpt_det", str(DET), "--ckpt_reader", out / "best.pt",
                 "--tag", "rftk5_foldall"], tmo=3600)
        else:
            run([PY, str(HERE / "reader_ft_eval.py"), "--reader",
                 out / "best.pt",
                 "--ids", str(fdir / "holdout_ids.json"),
                 "--tag", name], tmo=1800)
            run([PY, str(HERE / "reader_ft_eval.py"), "--reader", "base",
                 "--ids", str(fdir / "holdout_ids.json"),
                 "--tag", f"base_{name}"], tmo=1800)
    # 집계: 폴합 McNemar(ft vs base, 폴드 holdout 합집합)
    try:
        ft_wrong, base_wrong, common = set(), set(), set()
        for f in range(5):
            d = json.loads((HERE / "reader_ft" / f"eval_fold{f}.json").read_text(encoding="utf-8"))
            b = json.loads((HERE / "reader_ft" / f"eval_base_fold{f}.json").read_text(encoding="utf-8"))
            ft_wrong |= set(d["wrong_ids"])
            base_wrong |= set(b["wrong_ids"])
        only_ft = len(ft_wrong - base_wrong)
        only_base = len(base_wrong - ft_wrong)
        (HERE / "reader_ft_k5_result.json").write_text(json.dumps(dict(
            ft_wrong=sorted(ft_wrong), base_wrong=sorted(base_wrong),
            only_ft=only_ft, only_base=only_base), ensure_ascii=False, indent=1),
            encoding="utf-8")
        log(f"[6] 폴합: ft 오독 {len(ft_wrong)} · base 오독 {len(base_wrong)} · "
            f"ft만 {only_ft} · base만 {only_base}")
    except Exception as e:
        log(f"[6] 집계 예외: {e}")
except SystemExit as e:
    log(f"체인 중단: {e}")
except Exception as e:
    log(f"체인 예외: {e}")
log("=== 리더 실촉 체인 종료 ===")
