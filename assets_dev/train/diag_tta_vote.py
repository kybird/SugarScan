# TTA 를 거절이 아니라 **투표(답 고치기)** 에 쓰면 어떻게 되는가.
#
# 685 에서 관찰: 기본 판독 '108'(틀림), TTA 8회 중 6회가 '106'(정답).
# 다수결이 답을 고칠 수 있다는 신호다.
#
# **오답에만 적용하는 것은 배포에서 불가능하다** — 추론 시점엔 무엇이 틀렸는지
# 모른다. 그래서 두 가지를 잰다:
#   (1) 진단: 오답 58건 중 몇 건이 복구되는가 / 정답 1064건 중 몇 건이 깨지는가
#       ※ 정답 쪽을 함께 재지 않으면 "실패만 보고 결론"이 된다
#   (2) 배포형: 기본 확신도가 낮은 장에만 TTA 를 돌린다(게이트). 평균 추론
#       비용이 얼마나 되는지 함께 낸다
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


def risky(p, g, nb):
    return p != g and nb > 2 and len(p) == len(g)


def main() -> int:
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    X, y = cache["real_holdout_images"], cache["real_holdout_label_ids"]
    gts = ["".join(str(int(v)) for v in r if int(v) != BLANK) for r in y]
    n = len(gts)
    m = tf.keras.models.load_model(str(HERE / "reader_model"))

    base = m.predict(X[..., None].astype(np.float32), batch_size=128, verbose=0)
    B = [dec(base[i]) for i in range(n)]
    bp = [b[0] for b in B]; bc = np.array([b[1] for b in B]); bn = [b[2] for b in B]

    rng = np.random.RandomState(SEED)
    votes = [[] for _ in range(n)]
    for _ in range(N_AUG):
        s = rng.uniform(0.92, 1.08); tx = rng.uniform(-0.03, 0.03)
        ty = rng.uniform(-0.03, 0.03); c = rng.uniform(0.85, 1.15)
        La = m.predict(jitter(X, s, tx, ty, c)[..., None].astype(np.float32),
                       batch_size=128, verbose=0)
        for i in range(n):
            votes[i].append(dec(La[i])[0])

    # 다수결(기본 판독도 한 표)
    vp = []
    for i in range(n):
        vp.append(Counter(votes[i] + [bp[i]]).most_common(1)[0][0])

    ok_b = sum(bp[i] == gts[i] for i in range(n))
    ok_v = sum(vp[i] == gts[i] for i in range(n))
    rb = sum(risky(bp[i], gts[i], bn[i]) for i in range(n))
    rv = sum(risky(vp[i], gts[i], bn[i]) for i in range(n))
    print(f"기본       완전일치 {ok_b} ({100*ok_b/n:.2f}%) · 위험군 {rb} ({100*rb/n:.2f}%)")
    print(f"TTA 다수결 완전일치 {ok_v} ({100*ok_v/n:.2f}%) · 위험군 {rv} ({100*rv/n:.2f}%)")

    fixed = [i for i in range(n) if bp[i] != gts[i] and vp[i] == gts[i]]
    broke = [i for i in range(n) if bp[i] == gts[i] and vp[i] != gts[i]]
    print(f"\n(1) 진단 — 오답 {n-ok_b}건 중 복구 {len(fixed)}건 "
          f"| 정답 {ok_b}건 중 파손 {len(broke)}건 → 순증 {len(fixed)-len(broke):+d}")
    print("    복구 예시:", ", ".join(f"{gts[i]}({bp[i]}→{vp[i]})" for i in fixed[:6]))
    if broke:
        print("    파손 예시:", ", ".join(f"{gts[i]}({bp[i]}→{vp[i]})" for i in broke[:6]))

    print("\n(2) 배포형 — 기본 확신도가 τ 미만인 장에만 TTA 를 돌린다")
    print(f"{'τ':>6} | {'TTA 대상':>11} | {'평균 추론':>9} | {'완전일치':>14} | {'위험군':>12}")
    for t in (0.0, 0.70, 0.90, 0.95, 0.99, 1.01):
        use = bc < t
        p2 = [vp[i] if use[i] else bp[i] for i in range(n)]
        e2 = sum(p2[i] == gts[i] for i in range(n))
        r2 = sum(risky(p2[i], gts[i], bn[i]) for i in range(n))
        cost = 1 + N_AUG * use.mean()
        print(f"{t:6.2f} | {int(use.sum()):5d} ({100*use.mean():4.1f}%) | "
              f"{cost:8.2f}회 | {e2:5d} ({100*e2/n:5.2f}%) | {r2:3d} ({100*r2/n:5.2f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
