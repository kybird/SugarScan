# GT 검수용 몽타주 — 자릿수를 보존한 오독(위험군)을 번호 붙여 떨어뜨린다.
#
# 왜 필요한가: "오독"은 GT 가 옳다는 전제 위의 판정이다. GT 가 틀렸다면 그 장은
# 오독이 아니라 **정답**이고, 그러면 지금의 정확도는 과소평가다. 이 저장소는
# 이미 두 번(EXIF·GT 패딩) 계측이 실력을 가린 적이 있다.
#
# 산출: _diag/gt_review/montage_N.png + index.json (번호 → id/GT/예측)
# 사람이 몽타주를 보고 "GT 가 틀린 번호"를 고르면 gt_corrections.jsonl 에 반영한다.
import json
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
OUT = HERE / "_diag" / "gt_review"
BLANK = 10
COLS = 3
PER_SHEET = 21          # 한 장에 21개(7행×3열) — 더 넣으면 화면에서 못 읽는다
BAR = 26                # 라벨 띠 높이


def greedy(seq):
    s, prev = [], -1
    for v in seq:
        v = int(v)
        if v != prev and v != BLANK:
            s.append(str(v))
        prev = v
    return "".join(s)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    X, y = cache["real_holdout_images"], cache["real_holdout_label_ids"]
    ids = [str(v) for v in cache["real_holdout_ids"]]
    gts = ["".join(str(int(v)) for v in row if int(v) != BLANK) for row in y]

    model = tf.keras.models.load_model(str(HERE / "reader_model"))
    am = np.argmax(model.predict(X[..., None].astype(np.float32),
                                 batch_size=128, verbose=0), axis=-1)
    preds = [greedy(r) for r in am]

    # 위험군: 값을 냈고(=blank 아님), 자릿수가 GT 와 같은데 틀린 장
    picks = []
    for i, (p, g) in enumerate(zip(preds, gts)):
        if p == g or len(p) != len(g):
            continue
        if int(np.sum(am[i] != BLANK)) <= 2:
            continue
        picks.append(i)
    print(f"위험군(자릿수 보존 오독) {len(picks)}건")

    index = []
    sheets = 0
    for start in range(0, len(picks), PER_SHEET):
        chunk = picks[start:start + PER_SHEET]
        tiles = []
        for k, i in enumerate(chunk):
            no = start + k + 1
            img = cv2.cvtColor(X[i], cv2.COLOR_GRAY2BGR)
            bar = np.full((BAR, img.shape[1], 3), 30, np.uint8)
            cv2.putText(bar, f"#{no}  GT {gts[i]} -> {preds[i]}", (6, 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 220, 255), 1,
                        cv2.LINE_AA)
            tiles.append(np.vstack([bar, img]))
            index.append({"no": no, "id": ids[i], "gt": gts[i],
                          "pred": preds[i]})
        while len(tiles) % COLS:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [np.hstack(tiles[r:r + COLS]) for r in range(0, len(tiles), COLS)]
        sheets += 1
        p = OUT / f"montage_{sheets}.png"
        cv2.imwrite(str(p), np.vstack(rows))
        print("saved", p)

    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", OUT / "index.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
