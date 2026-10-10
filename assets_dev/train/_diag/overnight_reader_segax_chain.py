# 리더 실촉 K=5 v2 체인 — 리플레이를 세그축 코퍼스(SEGAX)로 교체 (2026-10-09).
# 사람: "가로선 기능 삭제한다.진행진행" — hstreak 제거 후 나머지 축
# (offghost v2·slotghost v2·kill·subtle·그림자 극성/전체/갭/상승/사각레이어)로
# 리플레이 합성을 굽고, 리더 재파인튜닝 K=5 를 같은 폴드로 돌려 1차(rftk5,
# 폴합 오독 15)와 짝비교한다. 배포 동등: 검출기 ftk5_g0.06 고정.
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
PY = sys.executable
LOG = HERE / "overnight_reader_segax_chain.log"
DET = TRAIN / "band_out" / "tone" / "ftk5_g0.06"
WARM = HERE / "reader_ft" / "warm_base.pt"
SEGAX = TRAIN / "synth_coco" / "SEGAX"
EPOCHS = 25


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(args, tmo=28800):
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


log("=== 리더 실촉 K=5 v2(SEGAX 리플레이) 체인 시작 ===")
try:
    log("[1] SEGAX 굽기(3,000장)")
    mf = SEGAX / "manifest.jsonl"
    if mf.exists() and sum(1 for _ in mf.open(encoding="utf-8")) >= 2900:
        log("  이미 완료 — 건너뜀")
    else:
        rc = run([PY, "-c",
                  "import sys; sys.path.insert(0, '.'); import synth_panel as sp; "
                  "sp.generate(3000, 20261009, 'synth_coco/SEGAX')"], tmo=14400)
        if rc != 0:
            raise SystemExit("굽기 실패")
    log("[2] SEGAX 상자 (g0.06 → 예측)")
    sb = HERE / "reader_boxes" / "SEGAX_g006.jsonl"
    if sb.exists() and sum(1 for _ in sb.open(encoding="utf-8")) >= 2800:
        log("  이미 완료 — 건너뜀")
    else:
        rc = run([PY, str(TRAIN / "make_reader_boxes.py"), "--set", "SEGAX",
                  "--ckpt", str(DET), "--out", str(sb)], tmo=14400)
        nbox = sum(1 for _ in sb.open(encoding="utf-8")) if sb.exists() else 0
        if rc != 0 or nbox < 2800:
            raise SystemExit(f"상자 실패/부족({nbox}개)")
    log("[3] 폴드 세트 조립(v2)")
    if run([PY, str(HERE / "build_reader_ft_folds2.py")], tmo=600) != 0:
        raise SystemExit("조립 실패")
    import cv2 as _cv
    _t = json.loads((HERE / "reader_ft2/fold0/manifest.jsonl").read_text(
        encoding="utf-8").splitlines()[0])
    if _cv.imread(str((HERE / "reader_ft2/fold0/train2017") / (_t["id"] + ".png"))) is None:
        raise SystemExit("폴드 파일 로드 점검 실패")
    for name in ("fold0", "fold1", "fold2", "fold3", "fold4", "foldall"):
        fdir = HERE / "reader_ft2" / name
        out = TRAIN / "reader_out" / f"rftk5b_{name}"
        log(f"[4] {name} 리더 학습 (SEGAX 리플레이 · 25에폭)")
        if (out / "best.pt").exists():
            log("  이미 학습됨 — 건너뜀")
        elif run([PY, str(TRAIN / "reader_crnn.py"), "train",
                  "--set", str(fdir), "--boxes", str(fdir / "boxes_g006.jsonl"),
                  "--out", str(out), "--resume", str(WARM),
                  "--epochs", str(EPOCHS), "--lr", "1e-4"]) != 0:
            continue
        if name == "foldall":
            log("[5] foldall 전량 e2e (g0.06 × v2 리더)")
            run([PY, str(TRAIN / "eval_e2e_bandnet.py"),
                 "--ckpt_det", str(DET), "--ckpt_reader", str(out / "best.pt"),
                 "--tag", "rftk5b_foldall"], tmo=3600)
        else:
            run([PY, str(HERE / "reader_ft_eval.py"), "--reader",
                 str(out / "best.pt"),
                 "--ids", str(fdir / "holdout_ids.json"),
                 "--tag", f"{name}_v2"], tmo=1800)
    # 집계: v2(SEGAX 리플레이) vs 1차(rftk5) — 같은 holdout, 같은 검출기
    try:
        from math import comb
        v2_wrong, old_wrong = set(), set()
        for f in range(5):
            d2 = json.loads((HERE / "reader_ft" / f"eval_fold{f}_v2.json").read_text(encoding="utf-8"))
            d1 = json.loads((HERE / "reader_ft" / f"eval_fold{f}.json").read_text(encoding="utf-8"))
            v2_wrong |= set(d2["wrong_ids"])
            old_wrong |= set(d1["wrong_ids"])
        only_v2 = len(v2_wrong - old_wrong)
        only_old = len(old_wrong - v2_wrong)
        n = only_v2 + only_old
        p = min(1.0, 2*sum(comb(n, i) for i in range(min(only_v2, only_old)+1))/2**n) if n else 1.0
        (HERE / "reader_ft_v2_result.json").write_text(json.dumps(dict(
            v2_wrong=sorted(v2_wrong), old_wrong=sorted(old_wrong),
            only_v2=only_v2, only_old=only_old, p=p), ensure_ascii=False, indent=1),
            encoding="utf-8")
        log(f"[6] 폴합: v2 오독 {len(v2_wrong)} · 1차(rftk5) 오독 {len(old_wrong)} · "
            f"v2만 {only_v2} · 1차만 {only_old} · McNemar p={p:.4f}")
    except Exception as e:
        log(f"[6] 집계 예외: {e}")
except SystemExit as e:
    log(f"체인 중단: {e}")
except Exception as e:
    log(f"체인 예외: {e}")
log("=== v2 체인 종료 ===")
