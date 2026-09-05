# TTA 일치도를 거절 신호로 썼을 때의 안전/유용 곡선.
#
# 발견(2026-09-04): softmax 확신도는 위험군을 못 거른다 — 모델이 확신하며
# 틀리기 때문이다(`275->279` 를 0.95 로). 같은 이미지를 조금씩 흔들어 여러 번
# 읽고 **답이 흔들리는지** 보면 다른 종류의 신호가 된다.
#   정답 일치도 중앙 1.000 vs 위험군 0.250
#
# 비용은 추론 N배다. 단말 예산(p95 400ms)에 넣으려면 N 을 줄여야 하므로
# N 별로 함께 잰다.
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
BLANK = 10
SEED = 7


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


def jitter(X, s, tx, ty, c):
    n, h, w = X.shape
    out = np.empty_like(X)
    for i in range(n):
        M = np.float32([[s, 0, tx * w + (1 - s) * w / 2],
                        [0, s, ty * h + (1 - s) * h / 2]])
        im = cv2.warpAffine(X[i], M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        med = float(np.median(im))
        out[i] = np.clip((im.astype(np.float32) - med) * c + med,
                         0, 255).astype(np.uint8)
    return out


def main() -> int:
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    X, y = cache["real_holdout_images"], cache["real_holdout_label_ids"]
    gts = ["".join(str(int(v)) for v in r if int(v) != BLANK) for r in y]
    n = len(gts)
    m = tf.keras.models.load_model(str(HERE / "reader_model"))

    base = m.predict(X[..., None].astype(np.float32), batch_size=128, verbose=0)
    P0 = [dec(base[i]) for i in range(n)]
    preds = [p[0] for p in P0]
    nb = [p[2] for p in P0]
    cls = np.array(["정답" if p == g else ("무출력" if k <= 2 else
                    ("위험" if len(p) == len(g) else "안전"))
                    for p, g, k in zip(preds, gts, nb)])
    print(f"holdout {n}장 · 거절 없음: 완전일치 {int((cls=='정답').sum())} "
          f"({100*(cls=='정답').mean():.2f}%) · 위험군 {int((cls=='위험').sum())} "
          f"({100*(cls=='위험').mean():.2f}%)\n")

    rng = np.random.RandomState(SEED)
    votes = [[] for _ in range(n)]
    for k in range(8):
        s = rng.uniform(0.92, 1.08); tx = rng.uniform(-0.03, 0.03)
        ty = rng.uniform(-0.03, 0.03); c = rng.uniform(0.85, 1.15)
        La = m.predict(jitter(X, s, tx, ty, c)[..., None].astype(np.float32),
                       batch_size=128, verbose=0)
        for i in range(n):
            votes[i].append(dec(La[i])[0])

    for N in (2, 4, 8):
        ag = np.array([sum(1 for v in votes[i][:N] if v == preds[i]) / N
                       for i in range(n)])
        print(f"=== TTA N={N} (추론 {N+1}회) ===")
        print(f"{'요구 일치도':>10} | {'완전일치':>14} | {'위험군':>13} | {'미인식':>13}")
        for thr in sorted(set(np.round(np.arange(0, 1.01, 1.0 / N), 4))):
            keep = ag >= thr
            ex = int((keep & (cls == "정답")).sum())
            rk = int((keep & (cls == "위험")).sum())
            rej = int((~keep).sum() + (keep & (cls == "무출력")).sum())
            flag = "  <= 게이트" if rk / n <= 0.002 else ""
            print(f"{thr:10.2f} | {ex:5d} ({100*ex/n:5.1f}%) | {rk:3d} "
                  f"({100*rk/n:5.2f}%) | {rej:4d} ({100*rej/n:5.1f}%){flag}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
