# -*- coding: utf-8 -*-
"""합성 양 스윕 — 굽고 · 크기별로 학습하고 · 포함 게이트로 잰다. 한 줄로.

사람이 자는 동안 돈다(2026-09-15). 단계마다 **먼저 로그에 적고** 실행하므로,
아침에 로그 끝 줄만 보면 어디까지 갔는지 안다.

설계에서 정한 것 두 가지:

1) **한 번 굽고 중첩 부분집합으로 자른다.** 크기마다 따로 구우면 난수열이
   갈려 '양의 효과'와 '다른 그림의 효과'가 섞인다(experiment-budget-parity).
   80k 를 한 번 굽고 --limit 로 10k/20k/40k/80k 를 만든다. 굽는 시간도
   3.5시간에서 2시간으로 준다.

2) **게이트는 포함 기준이다.** IoU 는 참고로만 찍힌다 — 기울어진 예측을
   축정렬 사람 라벨과 견주는 자라 천장이 있고, 이번 판은 cam_roll 을 ±1.5°
   에서 ±15° 로 넓혔으므로 그 천장에 더 깊이 들어간다. 옛 판의 IoU 와
   새 판의 IoU 를 나란히 놓고 우열을 말하면 안 된다.

사용:
  python band_det_sweep.py --tag r3 --total 80000 --sizes 10000,20000,40000,80000
  python band_det_sweep.py --tag r3 --skip-bake        # 코퍼스가 이미 있으면
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def log(msg):
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def run(cmd, what):
    log(f"▶ {what}")
    log(f"  $ {' '.join(str(c) for c in cmd[1:])}")
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(HERE))
    dt = (time.time() - t0) / 60
    if r.returncode != 0:
        log(f"✗ {what} 실패(코드 {r.returncode}, {dt:.1f}분) — 스윕을 멈춘다")
        # 멈춘다. 다음 단계가 앞 단계 산출물을 쓰므로 밀고 나가면 무엇을
        # 재는지 알 수 없는 결과가 쌓인다.
        sys.exit(r.returncode)
    log(f"✓ {what} ({dt:.1f}분)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="r3", help="코퍼스·체크포인트 이름표")
    ap.add_argument("--total", type=int, default=80000, help="구울 장 수")
    ap.add_argument("--sizes", default="10000,20000,40000,80000")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--seed", type=int, default=31000)
    ap.add_argument("--skip-bake", action="store_true")
    ap.add_argument("--skip-gate", action="store_true")
    ap.add_argument("--portrait-only", action="store_true", default=True,
                    help="가로형을 게이트에서도 뺀다. 학습 코퍼스가 "
                         "EXCLUDE_WIDE=True 이면 이것도 켜져 있어야 짝이 맞는다.")
    a = ap.parse_args(argv)

    sizes = [int(x) for x in a.sizes.split(",") if x.strip()]
    corpus = f"synth_{a.tag}_{a.total}"
    t_all = time.time()
    log(f"== 스윕 시작 · 코퍼스 {corpus} · 크기 {sizes} · {a.epochs}에폭 ==")

    if not a.skip_bake:
        run([PY, str(HERE / "synth_panel.py"), "gen",
             "--count", str(a.total), "--seed", str(a.seed),
             "--out", str(HERE / corpus)], f"합성 {a.total}장 굽기")
    else:
        log(f"· 굽기 건너뜀 — {corpus} 를 그대로 쓴다")
    if not (HERE / corpus / "manifest.jsonl").exists():
        log(f"✗ 코퍼스가 없다: {corpus}")
        return 2

    for n in sizes:
        if n > a.total:
            log(f"· {n} 은 코퍼스보다 크다 — 건너뜀")
            continue
        out = f"band_det_{a.tag}_{n // 1000}k.pt"
        run([PY, str(HERE / "train_band_detector.py"),
             "--data", corpus, "--limit", str(n),
             "--epochs", str(a.epochs), "--ckpt-every", "10",
             "--out", out], f"학습 {n}장 -> {out}")
        if not a.skip_gate:
            _g = [PY, str(HERE / "eval_band_detector.py"), "gate",
                  "--ckpt", out]
            if a.portrait_only:
                _g.append("--portrait-only")
            run(_g, f"게이트 {out}")

    log(f"== 스윕 끝 · 전체 {(time.time() - t_all) / 60:.0f}분 ==")
    log("아침에 볼 것: 웹툴 모니터 탭의 포함률 표. "
        "1순위 '전부 담음' 비율, 2순위 넓이비, 그 아래 잘린 변.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
