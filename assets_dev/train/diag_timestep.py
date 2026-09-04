# 타임스텝 진단 — 길이 붕괴가 형태 붕괴(H1)에서 오는지 직접 확인.
#
# 새 학습 없음. 기존 체크포인트(reader_model)로 캐시 holdout 을 다시 읽고,
# (1) 완전일치·길이 붕괴를 캐시 기준으로 재계산하고
# (2) 길이가 짧아진 표본의 타임스텝별 argmax 를 40칸 그대로 찍는다.
#
# **캐시(EXIF 적용) 기준으로만 잰다.** reader_preds.json 은 eval_reader.py 가
# 만든 것인데 그쪽은 PIL 로 EXIF 없이 디코드해 좌표계가 어긋나 있다 —
# 이 진단의 근거로 쓰지 않는다(대조용으로 숫자만 함께 출력).
import json
from collections import Counter
from pathlib import Path

import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
CACHE = HERE / "data_cache_v2.npz"
MODEL_DIR = HERE / "reader_model"
PREDS = HERE / "reader_preds.json"
NUM_CLASSES = 11
BLANK = NUM_CLASSES - 1
N_SAMPLES = 10


def greedy_decode(seq):
    s, prev = [], -1
    for v in seq:
        v = int(v)
        if v != prev and v != BLANK:
            s.append(str(v))
        prev = v
    return "".join(s)


def main() -> int:
    cache = np.load(str(CACHE))
    X_rh = cache["real_holdout_images"]
    y_rh = cache["real_holdout_label_ids"]
    id_rh = [str(x) for x in cache["real_holdout_ids"]]
    gts = ["".join(str(int(v)) for v in row if int(v) != BLANK) for row in y_rh]

    model = tf.keras.models.load_model(str(MODEL_DIR))
    logits = model.predict(
        X_rh[..., np.newaxis].astype(np.float32), batch_size=128, verbose=0)
    argmax = np.argmax(logits, axis=-1)          # (N, 40)
    preds = [greedy_decode(row) for row in argmax]

    exact = sum(1 for p, g in zip(preds, gts) if p == g)
    len_mismatch = sum(1 for p, g in zip(preds, gts) if len(p) != len(g))
    shorter = sum(1 for p, g in zip(preds, gts) if len(p) < len(g))
    longer = sum(1 for p, g in zip(preds, gts) if len(p) > len(g))
    n = len(gts)
    print("=== 캐시 holdout (EXIF 적용 좌표계) 재계산 ===")
    print(f"표본 {n}")
    print(f"완전일치      {exact} ({100*exact/n:.1f}%)")
    print(f"길이 불일치   {len_mismatch} ({100*len_mismatch/n:.1f}%)"
          f"  [짧음 {shorter} / 김 {longer}]")
    print(f"GT 자릿수 분포   {dict(sorted(Counter(len(g) for g in gts).items()))}")
    print(f"예측 자릿수 분포 {dict(sorted(Counter(len(p) for p in preds).items()))}")

    if PREDS.exists():
        pj = json.loads(PREDS.read_text(encoding="utf-8"))
        pe = sum(1 for p, g in pj.values() if p == g)
        pl = sum(1 for p, g in pj.values() if len(p) != len(g))
        print("\n=== 대조: reader_preds.json (eval_reader.py, EXIF 미적용) ===")
        print(f"표본 {len(pj)}  완전일치 {pe} ({100*pe/len(pj):.1f}%)"
              f"  길이 불일치 {pl} ({100*pl/len(pj):.1f}%)")
        print(f"예측 자릿수 분포 "
              f"{dict(sorted(Counter(len(p) for p, _ in pj.values()).items()))}")

    # ===== 타임스텝 =====
    shrunk = [i for i in range(n) if len(preds[i]) < len(gts[i])]
    shrunk.sort(key=lambda i: len(gts[i]) - len(preds[i]), reverse=True)
    picks = shrunk[:N_SAMPLES]
    print(f"\n=== 타임스텝 argmax — 길이 붕괴 {len(shrunk)}건 중 {len(picks)}건 ===")
    print("('.' = blank, 숫자 = 그 타임스텝의 최고점 클래스)\n")
    for i in picks:
        row = argmax[i]
        raw = "".join("." if v == BLANK else str(v) for v in row)
        runs, prev, start = [], None, 0
        for k, v in enumerate(row):
            if v != prev:
                if prev is not None:
                    runs.append((prev, start, k - 1))
                prev, start = v, k
        runs.append((prev, start, len(row) - 1))
        run_str = " ".join(
            f"{'.' if v == BLANK else v}x{e - s + 1}" for v, s, e in runs)
        print(f"id={id_rh[i]}  GT={gts[i]!r}  pred={preds[i]!r}")
        print(f"  raw(40)  : {raw}")
        print(f"  런렝스   : {run_str}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
