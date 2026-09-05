# G26/G27 보조 — 자릿수 보존 오독(위험군) 중 어떤 자리가 틀리는지 센다.
# 왼쪽 여유(BOX_MARGIN[0])의 효과는 첫 자리 오독에서, 오른쪽 여유(BOX_MARGIN[1])의
# 효과는 마지막 자리 오독에서 드러난다. 조건 비교표의 "첫 자리 틀림" 칸을 채운다.
from pathlib import Path

import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
BLANK = 10


def greedy(row):
    seq = np.argmax(row, -1)
    s, prev = [], -1
    nb = 0
    for v in seq:
        v = int(v)
        if v != BLANK:
            nb += 1
        if v != prev and v != BLANK:
            s.append(str(v))
        prev = v
    return "".join(s), nb


def main() -> int:
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    X = cache["real_holdout_images"]
    y = cache["real_holdout_label_ids"]
    gts = ["".join(str(int(v)) for v in row if int(v) != BLANK) for row in y]
    m = tf.keras.models.load_model(str(HERE / "reader_model"))
    L = m.predict(X[..., None].astype(np.float32), batch_size=128, verbose=0)
    decoded = [greedy(L[i]) for i in range(len(gts))]
    preds = [d[0] for d in decoded]
    nbs = [d[1] for d in decoded]

    # "위험군" 정의는 diag_confidence_sweep 과 같다: 오답 · 자릿수 보존 · 무출력 아님.
    risky = [(g, p) for g, p, nb in zip(gts, preds, nbs)
             if p != g and len(p) == len(g) and nb > 2]
    first = [(g, p) for g, p in risky if g[0] != p[0]]
    last = [(g, p) for g, p in risky if g[-1] != p[-1] and g[:-1] == p[:-1]]
    mid = [(g, p) for g, p in risky if g[0] == p[0] and g[-1] == p[-1]]
    print(f"위험군(자릿수 보존 오독) {len(risky)}건 중 "
          f"첫 자리 틀림 {len(first)} · 마지막 자리만 틀림 {len(last)} · 가운데만 {len(mid)}")
    for g, p in first:
        print(f"  첫자리: GT {g} → {p}")
    print(f"(무출력/붕괴 오답 {sum(1 for g, p, nb in zip(gts, preds, nbs) if p != g and (len(p) != len(g) or nb <= 2))}건은 이 표에서 제외)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
