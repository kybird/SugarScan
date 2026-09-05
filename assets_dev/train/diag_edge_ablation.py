# 오른쪽 가장자리를 지워도 정확도가 유지되는가 — '읽기'와 '찍기'를 가른다.
#
# 949 에서 발견: 크롭 오른쪽 끝에 잉크가 없는데도 모델이 마지막 자리 '1' 을
# 0.99 확신으로 냈고, 그 영역을 배경으로 덮어도 답이 그대로였다. 그리고
# holdout 1,122장 **전부**가 마지막 글자를 40칸 중 끝(38~39)에서 낸다.
# 공간적으로 읽는 게 아니라 '마지막 칸에 숫자를 놓는 습관'이라는 뜻이다.
#
# 이 스크립트는 오른쪽 N열을 배경색으로 덮고 정확도를 다시 잰다.
# 정확도가 유지되면 그만큼은 픽셀이 아니라 사전분포에서 나온 것이다.
from pathlib import Path

import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
BLANK = 10


def greedy(row):
    seq = np.argmax(row, -1)
    s, prev = [], -1
    for v in seq:
        v = int(v)
        if v != prev and v != BLANK:
            s.append(str(v))
        prev = v
    return "".join(s)


def main() -> int:
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    X = cache["real_holdout_images"]
    y = cache["real_holdout_label_ids"]
    gts = ["".join(str(int(v)) for v in row if int(v) != BLANK) for row in y]
    model = tf.keras.models.load_model(str(HERE / "reader_model"))
    n = len(gts)

    print(f"holdout {n}장 — 오른쪽 N열을 각 장의 배경색(중앙값)으로 덮고 재채점\n")
    print(f"{'가림':>10} | {'완전일치':>12} | {'마지막자리만 틀림':>16}")
    print("-" * 48)
    base = None
    for k in (0, 4, 8, 16, 24, 32, 48, 64):
        Xm = X.astype(np.float32).copy()
        if k:
            med = np.median(Xm.reshape(n, -1), axis=1)
            for i in range(n):
                Xm[i, :, -k:] = med[i]
        L = model.predict(Xm[..., None], batch_size=128, verbose=0)
        preds = [greedy(L[i]) for i in range(n)]
        exact = sum(p == g for p, g in zip(preds, gts))
        lastonly = sum(1 for p, g in zip(preds, gts)
                       if p != g and len(p) == len(g) and p[:-1] == g[:-1])
        if base is None:
            base = exact
        print(f"{k:>7}열 | {exact:5d} ({100*exact/n:5.1f}%) | {lastonly:5d}"
              + ("   ← 기준" if k == 0 else f"   ({100*(exact-base)/n:+.1f}pp)"))

    print("\n읽는 법: 오른쪽을 지웠는데 완전일치가 거의 안 떨어지면,")
    print("그 자리는 애초에 읽히고 있지 않았고 사전분포로 채워지던 것이다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
