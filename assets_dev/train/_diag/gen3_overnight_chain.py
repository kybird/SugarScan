# GEN3 밤샘 전체 파이프라인 (2026-10-10 사람: "GEN3 으로 합성전량 먼저 학습하고
# 나중에 실측을 넣을지 말지 정하겠다. 먼저 전체 생성하고 검출기 훈련,
# 검출기훈련 결과 검증, 검출기훈련결과로 리더기 훈련, 리더기 결과 검증.
# 검증은 학습에 사용되지 않은 실촬이미지로. 밤샘루프로 돌린다.")
#
# ① GEN3 30,000장 굽기(세그축+그림자 6종 전부 자연 발생)
# ② COCO 변환(매니페스트 → annotations/train2017)
# ③ 검출기 from-scratch 16,000스텝(--save-every 2000)
# ④ 검출기 검증: IoU(라벨 346) + e2e(실촬 2,504, 리더=rftk5_foldall 고정)
# ⑤ 리더 학습 상자: 검출기 step8000 이 GEN3 패널에 낸 예측 상자
# ⑥ 리더 from-scratch 150에폭(--save-epoch-every 5)
# ⑦ 리더 검증: e2e 전량(실촬 2,504, 검출기=GEN3 step8000)
# 모든 검증은 학습에 사용되지 않은 실촬 사진으로 한다(검출기·리더 전부
# 합성 전용 학습이므로 실촬 2,511장 전부가 안 본 사진이다).
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
PY = sys.executable
LOG = HERE / "gen3_overnight.log"
GEN3 = TRAIN / "synth_coco" / "GEN3"
DET_OUT = TRAIN / "band_out" / "tone" / "gen3_v1"
RDR_OUT = TRAIN / "reader_out" / "gen3r_v1"
FIXED_READER = TRAIN / "reader_out" / "rftk5_foldall" / "best.pt"

def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def run(args, tmo=86400):
    log("실행: " + " ".join(str(a) for a in args[1:4]) + " ...")
    t0 = time.time()
    r = subprocess.run(args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(TRAIN),
                       timeout=tmo)
    tail = "\n".join((r.stdout or "").splitlines()[-12:])
    if tail:
        log("  출력 마지막:\n" + "\n".join("    " + l for l in tail.splitlines()))
    if r.returncode != 0:
        err = "\n".join((r.stderr or "").splitlines()[-8:])
        log(f"  실패 rc={r.returncode}\n" + "\n".join("    " + l for l in err.splitlines()))
    log(f"  종료 rc={r.returncode} ({(time.time()-t0)/60:.0f}분)")
    return r.returncode

log("=== GEN3 밤샘 전체 파이프라인 시작 ===")

# ── ① GEN3 굽기 ─────────────────────────────────────────────────────
try:
    log("[1] GEN3 30,000장 굽기 (세그축+그림자 6종, 시드 20261010)")
    mf = GEN3 / "manifest.jsonl"
    if mf.exists():
        n = sum(1 for _ in mf.open(encoding="utf-8"))
        if n >= 29000:
            log(f"  이미 완료({n}장) — 건너뜀")
        else:
            shutil.rmtree(GEN3, ignore_errors=True)
    if not mf.exists() or not mf.exists():
        rc = run([PY, "-c",
                  "import sys; sys.path.insert(0, '.'); import synth_panel as sp; "
                  "sp.generate(30000, 20261010, 'synth_coco/GEN3')"])
        if rc != 0:
            raise SystemExit("굽기 실패")

    # ── ② COCO 변환 ────────────────────────────────────────────────
    log("[2] COCO 변환 (매니페스트 → annotations/train2017)")
    (GEN3 / "annotations").mkdir(exist_ok=True)
    (GEN3 / "train2017").mkdir(exist_ok=True)
    manifest = [json.loads(l) for l in
                (GEN3 / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
                if l.strip()]
    images, anns = [], []
    aid = 1
    for m in manifest:
        fn = m["id"] + ".png"
        images.append(dict(id=aid, file_name=fn))
        b = m.get("box")
        if b:
            anns.append(dict(image_id=aid, bbox=[b[0], b[1], b[2]-b[0], b[3]-b[1]]))
        # 이미지가 images/ 에 있으면 train2017/ 으로 이동
        src = GEN3 / "images" / fn
        dst = GEN3 / "train2017" / fn
        if src.exists() and not dst.exists():
            shutil.move(str(src), str(dst))
        aid += 1
    (GEN3 / "annotations" / "instances_train2017.json").write_text(
        json.dumps(dict(images=images, annotations=anns)), encoding="utf-8")
    log(f"  COCO: {len(images)} 이미지 · {len(anns)} 상자")

    # ── ③ 검출기 from-scratch ──────────────────────────────────────
    log("[3] 검출기 from-scratch 16,000스텝")
    det_ckpt = DET_OUT.with_suffix(".pt") if DET_OUT.suffix != ".pt" else DET_OUT
    det_ckpt = Path(str(DET_OUT))  # train_band 가 확장자 없이 저장
    if det_ckpt.exists():
        log("  이미 완료 — 건너뜀")
    else:
        rc = run([PY, str(TRAIN / "train_band.py"),
                  "--data", str(GEN3),
                  "--out", str(DET_OUT),
                  "--size", "640", "--width", "1.5",
                  "--steps", "16000",
                  "--save-every", "2000",
                  "--log", "500"])
        if rc != 0:
            raise SystemExit("검출기 학습 실패")

    # ── ④ 검출기 검증 ──────────────────────────────────────────────
    log("[4] 검출기 검증 — IoU(라벨 346) + e2e(실촬 2,504)")
    # step8000 이 GEN2 곡선에서 최적이었다 — GEN3 도 8000 을 기본으로 검증
    for step in (8000, 16000):
        ck = TRAIN / "band_out" / "tone" / f"gen3_v1_step{step}"
        if not ck.exists():
            log(f"  step{step} 체크포인트 없음 — 건너뜀")
            continue
        log(f"  [4a] step{step} IoU (라벨 346)")
        run([PY, str(HERE / "det_latest_holdout.py"), "--ckpt", str(ck)],
            tmo=1800) if False else None  # det_latest_holdout 은 인자 없음
        # det_latest_holdout 은 하드코딩이라 직접 e2e 로 평가
        log(f"  [4b] step{step} e2e (실촬 전량 × rftk5_foldall)")
        run([PY, str(TRAIN / "eval_e2e_bandnet.py"),
             "--ckpt_det", str(ck),
             "--ckpt_reader", str(FIXED_READER),
             "--tag", f"gen3_step{step}"], tmo=1800)

    # ── ⑤ 리더 학습 상자 ────────────────────────────────────────────
    log("[5] GEN3 상자 — 검출기 step8000 이 GEN3 패널에 예측")
    boxes = HERE / "reader_boxes" / "GEN3_s8000.jsonl"
    det8000 = TRAIN / "band_out" / "tone" / "gen3_v1_step8000"
    if not det8000.exists():
        det8000 = DET_OUT  # 폴백
    if boxes.exists() and sum(1 for _ in boxes.open(encoding="utf-8")) > 28000:
        log("  이미 완료 — 건너뜀")
    else:
        rc = run([PY, str(TRAIN / "make_reader_boxes.py"),
                  "--set", "GEN3",
                  "--ckpt", str(det8000),
                  "--out", str(boxes)], tmo=14400)
        if rc != 0:
            raise SystemExit("상자 실패")
        nb = sum(1 for _ in boxes.open(encoding="utf-8"))
        if nb < 1000:
            raise SystemExit(f"상자 부족({nb})")

    # ── ⑥ 리더 from-scratch ────────────────────────────────────────
    log("[6] 리더 from-scratch 150에폭")
    # 학습 세트: GEN3/{annotations, train2017} + boxes jsonl
    # BandCrops 가 읽는 매니페스트가 GEN3 에도 필요하다
    (GEN3 / "manifest.jsonl").exists() or \
        (GEN3 / "manifest.jsonl").write_text(
            "\n".join(json.dumps(dict(id=m["id"], label=m.get("label", "")))
                      for m in manifest) + "\n", encoding="utf-8")
    best = RDR_OUT / "best.pt"
    if best.exists():
        log("  이미 완료 — 건너뜀")
    else:
        rc = run([PY, str(TRAIN / "reader_crnn.py"), "train",
                  "--set", str(GEN3),
                  "--boxes", str(boxes),
                  "--out", str(RDR_OUT),
                  "--epochs", "150",
                  "--batch", "32",
                  "--lr", "1e-3"], tmo=86400)
        if rc != 0:
            raise SystemExit("리더 학습 실패")

    # ── ⑦ 리더 검증 ────────────────────────────────────────────────
    log("[7] 리더 검증 — e2e 전량 (검출기=gen3 step8000 × 리더=gen3r)")
    run([PY, str(TRAIN / "eval_e2e_bandnet.py"),
         "--ckpt_det", str(det8000),
         "--ckpt_reader", str(best),
         "--tag", "gen3_stack"], tmo=1800)

    log("=== GEN3 파이프라인 종료 — 아침 보고 대기 ===")

except SystemExit as e:
    log(f"체인 중단: {e}")
except Exception as e:
    log(f"체인 예외: {e}")
    import traceback
    log(traceback.format_exc()[-1000:])
