# 확신도 임계값 스윕 — G24 를 새 모델로 다시 뜬다.
#
# G24(2026-09-04, 옛 모델)는 "부분적으로 갈린다"였다: 위험군 중앙 0.601 vs
# 정답 0.991 로 분리는 되지만 위험군 p75(0.909)가 정답 p25(0.930)와 겹쳐
# **확신하며 틀린 오독**이 어떤 τ 에서도 살아남았다(τ=0.99 에서 2건).
#
# 여유+흔들기 재학습 뒤 위험군이 43 → 18 로 줄었으므로 "안전을 사는 가격"이
# 달라졌을 것이다. 같은 정의·같은 τ 격자로 다시 잰다.
#
# 확신도 = greedy 경로가 문자를 내보낸 타임스텝에서 그 문자의 확률 중 **최솟값**
# (약한 고리 기준 — 한 자리만 흔들려도 값 전체가 틀린다).
import json
from collections import Counter
from pathlib import Path

import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
BLANK = 10
TAUS = (0.0, 0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.97, 0.99)


def dec(row):
    e = np.exp(row - row.max(-1, keepdims=True))
    pr = e / e.sum(-1, keepdims=True)
    seq = np.argmax(row, -1)
    ch, cf, prev = [], [], -1
    for t, v in enumerate(seq):
        v = int(v)
        if v != prev and v != BLANK:
            ch.append(str(v)); cf.append(float(pr[t, v]))
        prev = v
    return "".join(ch), (min(cf) if cf else 0.0), int((seq != BLANK).sum())


def main() -> int:
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    X, y = cache["real_holdout_images"], cache["real_holdout_label_ids"]
    gts = ["".join(str(int(v)) for v in r if int(v) != BLANK) for r in y]
    m = tf.keras.models.load_model(str(HERE / "reader_model"))
    L = m.predict(X[..., None].astype(np.float32), batch_size=128, verbose=0)
    P = [dec(L[i]) for i in range(len(gts))]
    preds = [p[0] for p in P]
    conf = np.array([p[1] for p in P])
    nb = [p[2] for p in P]
    n = len(gts)

    cls = []
    for p, g, k in zip(preds, gts, nb):
        if p == g:
            cls.append("정답")
        elif k <= 2:
            cls.append("무출력")
        elif len(p) == len(g):
            cls.append("위험")
        else:
            cls.append("안전")
    cls = np.array(cls)

    print("=== 분류별 확신도 분포 ===")
    print(f"{'분류':>8} | {'n':>5} | {'중앙':>6} | {'p25':>6} | {'p75':>6}")
    for k in ("정답", "위험", "안전", "무출력"):
        v = conf[cls == k]
        if len(v):
            print(f"{k:>8} | {len(v):5d} | {np.median(v):6.3f} | "
                  f"{np.percentile(v,25):6.3f} | {np.percentile(v,75):6.3f}")

    print("\n=== 임계값 스윕 ===")
    print(f"{'τ':>6} | {'완전일치':>14} | {'위험군 오독':>14} | {'미인식':>14}")
    rows = []
    for t in TAUS:
        keep = conf >= t
        ex = int((keep & (cls == "정답")).sum())
        rk = int((keep & (cls == "위험")).sum())
        rej = int((~keep).sum() + (keep & (cls == "무출력")).sum())
        rows.append((t, ex, rk, rej))
        lab = "거절없음" if t == 0 else f"{t:.2f}"
        print(f"{lab:>6} | {ex:5d} ({100*ex/n:5.1f}%) | {rk:4d} ({100*rk/n:5.2f}%) "
              f"| {rej:5d} ({100*rej/n:5.1f}%)")

    gate = [r for r in rows if r[2] / n <= 0.002]
    print("\n승격 게이트(치명적 오독 ≤0.2%) 충족 지점:")
    if gate:
        for t, ex, rk, rej in gate:
            print(f"  τ={t:.2f}: 완전일치 {100*ex/n:.1f}% · 위험군 {100*rk/n:.2f}% "
                  f"· 미인식 {100*rej/n:.1f}%")
    else:
        print("  없음")

    out = HERE.parent.parent / "docs" / "reports" / "confidence-sweep-v2.json"
    out.write_text(json.dumps(
        {"n": n, "counts": dict(Counter(cls.tolist())),
         "sweep": [{"tau": t, "exact": e, "risky": r, "rejected": j}
                   for t, e, r, j in rows]}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\n저장: {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
