# TTA 투표 + 거절을 함께 걸었을 때의 안전/유용 지점.
#
# 따로 쟀을 때:
#   투표만  완전일치 94.83 → 96.88% · 위험군 1.60 → 1.07%   (답을 고친다)
#   거절만  일치도 ≥0.88 에서 위험군 0.00% · 미인식 8.4%     (틀린 것을 버린다)
# 둘은 다른 일을 하므로 함께 쓰면 게이트에 더 가까울 수 있다.
#
# 승격 게이트(G17 §2.7): 완전일치 ≥98% · 치명적 오독 ≤0.2% · 미인식 ≤5%
# ※ 그 게이트는 **실촬 골든셋 + 여러 프레임** 기준이고 여기는 사진 한 장
#   기준이다. 숫자를 나란히 놓되 "통과"라고 부르지 않는다.
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
BLANK, N_AUG, SEED = 10, 8, 7


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
    B = [dec(base[i]) for i in range(n)]
    bp = [b[0] for b in B]; bn = [b[2] for b in B]

    rng = np.random.RandomState(SEED)
    votes = [[] for _ in range(n)]
    for _ in range(N_AUG):
        s = rng.uniform(0.92, 1.08); tx = rng.uniform(-0.03, 0.03)
        ty = rng.uniform(-0.03, 0.03); c = rng.uniform(0.85, 1.15)
        La = m.predict(jitter(X, s, tx, ty, c)[..., None].astype(np.float32),
                       batch_size=128, verbose=0)
        for i in range(n):
            votes[i].append(dec(La[i])[0])

    # 투표 결과와 그 **득표율**(= 그 답에 대한 지지도)
    win, share = [], []
    for i in range(n):
        c = Counter(votes[i] + [bp[i]])
        w, k = c.most_common(1)[0]
        win.append(w); share.append(k / (N_AUG + 1))
    share = np.array(share)

    print(f"holdout {n}장 · TTA N={N_AUG} (추론 {N_AUG+1}회)\n")
    print("득표율 분포:")
    okm = np.array([win[i] == gts[i] for i in range(n)])
    rkm = np.array([win[i] != gts[i] and bn[i] > 2 and len(win[i]) == len(gts[i])
                    for i in range(n)])
    print(f"  정답  중앙 {np.median(share[okm]):.3f}")
    print(f"  위험군 중앙 {np.median(share[rkm]):.3f}   (n={int(rkm.sum())})")

    print(f"\n{'요구 득표율':>11} | {'완전일치':>14} | {'위험군':>13} | {'미인식':>13}")
    print("-" * 62)
    for thr in [k / (N_AUG + 1) for k in range(N_AUG + 2)]:
        keep = share >= thr
        ex = int((keep & okm).sum())
        rk = int((keep & rkm).sum())
        rej = int((~keep).sum() + int((keep & ~okm & ~rkm).sum()))
        flag = ""
        if rk / n <= 0.002:
            flag += "  오독OK"
        if rej / n <= 0.05:
            flag += " 미인식OK"
        print(f"{thr:11.3f} | {ex:5d} ({100*ex/n:5.2f}%) | {rk:3d} ({100*rk/n:5.2f}%) "
              f"| {rej:4d} ({100*rej/n:5.1f}%){flag}")

    print("\n게이트 세 조건(완전일치 ≥98% · 오독 ≤0.2% · 미인식 ≤5%) 동시 충족:")
    hit = [t for t in [k/(N_AUG+1) for k in range(N_AUG+2)]
           if (lambda kp: ((kp & okm).sum()/n >= 0.98
                           and (kp & rkm).sum()/n <= 0.002
                           and ((~kp).sum()+ (kp & ~okm & ~rkm).sum())/n <= 0.05))(share >= t)]
    print("  " + (", ".join(f"{t:.2f}" for t in hit) if hit else "없음"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
