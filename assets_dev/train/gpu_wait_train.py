# GPU 를 감시하다 쉬면 재학습을 시작한다 — 사람 지시(2026-09-28).
#
# 규칙(사람 명세 그대로):
#   1. 1시간마다 GPU 검사
#   2. 쉬고 있으면 10분 단위로 검사
#   3. 그래도 쉬고 있으면 1분 단위로 검사
#   4. 1분 단위에서 10번 연속 쉬고 있으면 학습 시작
# 중간에라도 GPU 가 바빠지면 1단계(1시간)로 되돌아간다 — 에폭 사이
# 순간 휴식이나 창을 닫는 사이에 올라타는 것을 막는 완충이다.
#
# idle 판정: utilization.gpu < IDLE_TH. supertonic-studio 학습 중 관찰은
# 72~99%, 그래픽 앱만 남으면 한 자릿수~십수% — 25% 임계가 둘을 가른다.
# 메모리는 그래픽 앱이 항상 3GB+ 를 잡고 있어 판정에 못 쓴다.
#
# 학습: 스케일 재정렬 2차(사람 승인 2026-09-28 "재굽기 재학습 진행").
# TG 코퍼스 30,000장(줌 하한 0.25 복원 — 초원경 라벨 근원 차단,
# mixed device 비중 0.5 — 클로즈업 보강). 스케일 게이트(면적 2%) 는
# eval·predict 양쪽에 이미 적용돼 있다. 구조·스텝은 1차와 동일
# (640·width1.5·16,000스텝 — 데이터 축만 재정렬해 1차 대비를 깨끗하게
# 가른다). 1차 TF 코퍼스(줌 0.10~1.0·procedural·mixed 장면 — 클로즈업 포함,
# 정보줄 간격 uniform 0.015~0.10H — 네거티브) + size 640 + width 1.5 +
# 스텝 16,000(데이터 2배에 스텝 2배). 학습 끝나면 순수 수동 홀드아웃
# 평가까지 돌려 로그만 남긴다. TF 는 굽는 중일 수 있다 — 준비될 때까지
# 기다린다(구조 A/B 순서가 아니라 묶음 먼저가 사람 결정).
#
# 사용:
#   python gpu_wait_train.py            # 백그라운드 권장
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDLE_TH = 25          # utilization.gpu % — 이 미만이면 '쉬고 있음'
H1, M10, M1 = 3600, 600, 60
RUNS1 = 10            # 1분 단위 연속 idle 횟수
LOG = HERE / "gpu_wait_train.log"
TF = HERE / "synth_coco" / "TG"
CKPT = HERE / "band_out" / "tone" / "atone_tg640w15"

TRAIN = [str(HERE / "train_band.py"), "--data", str(TF),
         "--out", str(CKPT),
         "--size", "640", "--width", "1.5", "--steps", "16000"]
# 2026-10-03 채점 기준 346장 전량 — 옛 파인튜닝(ft_bandnet_v1, 폐기) 잠금
# 123장은 현행 모델(합성 전용 학습)에 누수가 없어 해제됐다(사람 지적으로
# 발견). A키 source 판정도 순회 후 수락장 0장이라 no-op — 옵션은 유지.
EVAL = ["--ckpt", str(CKPT), "--exclude-accepted", "--no-overlay"]


def tf_ready():
    """TF 코퍼스 완료 판정 — COCO 주석이 온전히 파싱돼야 한다(굽는 중엔 없다)."""
    import json
    ann = TF / "annotations" / "instances_train2017.json"
    try:
        j = json.loads(ann.read_text(encoding="utf-8"))
        return len(j.get("images", [])) >= 30000
    except Exception:
        return False


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def gpu_util():
    out = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=utilization.gpu",
         "--format=csv,noheader", "-i", "0"], text=True).strip()
    return int(out.splitlines()[0].replace("%", "").strip())


def idle():
    u = gpu_util()
    return u < IDLE_TH, u


def main():
    log(f"감시 시작 · idle 판정: util < {IDLE_TH}% · "
        f"1h→10m→(1m×{RUNS1} 연속) → 학습")
    while True:
        # 1단계 — 1시간
        while True:
            ok, u = idle()
            log(f"[1h] util {u}% -> {'IDLE' if ok else 'busy'}")
            if ok:
                break
            time.sleep(H1)
        # 2단계 — 10분 (즉시 1회 + 10분 후 재확인)
        ok2 = False
        for _ in range(2):
            ok, u = idle()
            log(f"[10m] util {u}% -> {'IDLE' if ok else 'busy'}")
            if not ok:
                break
            if _ == 1:
                ok2 = True
            else:
                time.sleep(M10)
        if not ok2:
            continue
        # 3단계 — 1분 × 10 연속
        streak = 0
        aborted = False
        for i in range(RUNS1):
            ok, u = idle()
            log(f"[1m {i+1}/{RUNS1}] util {u}% -> {'IDLE' if ok else 'busy'}")
            if not ok:
                aborted = True
                break
            streak += 1
            if i < RUNS1 - 1:
                time.sleep(M1)
        if streak < RUNS1:
            log(f"연속 실패({streak}/{RUNS1}) — 1시간 단계로 복귀")
            continue
        log(f"IDLE {RUNS1}회 연속 확인 — 학습 직전 TF 코퍼스 확인")
        while not tf_ready():
            log("TF 미완료(굽는 중) — 10분 후 재확인")
            time.sleep(M10)
        log(f"TF 준비 완료 — 학습 시작: {' '.join(TRAIN[1:])}")
        with Path(str(CKPT) + ".log").open(
                "w", encoding="utf-8") as lf:
            r = subprocess.run(
                [sys.executable] + TRAIN,
                cwd=str(HERE), stdout=lf, stderr=subprocess.STDOUT)
        log(f"학습 종료 rc={r.returncode}")
        if r.returncode == 0:
            log("홀드아웃 평가 시작 (순수 수동 라벨)")
            with Path(str(CKPT) + ".eval.log").open(
                    "w", encoding="utf-8") as lf:
                r2 = subprocess.run(
                    [sys.executable, str(HERE / "eval_band_real.py")] + EVAL,
                    cwd=str(HERE), stdout=lf, stderr=subprocess.STDOUT)
            log(f"평가 종료 rc={r2.returncode} — {CKPT.name}.eval.log")
        log("감시 종료 — 재감시가 필요하면 스크립트를 다시 띄운다")
        return


if __name__ == "__main__":
    main()
