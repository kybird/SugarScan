# 학습된 cell_model.keras 을 production-path 밴드 크롭 57장에 평가한다.
# 조립: 3셀 분류 → 빈칸(11) 스킵 → 선두 0 제거 → int 비교.
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image

HERE = Path(__file__).resolve().parent
CROPS = HERE / "crops"
MODEL = HERE / "cell_model.h5"
LABELS = HERE.parent / "upstream" / "datumo" / "labels.jsonl"


def main() -> int:
    model = tf.keras.models.load_model(MODEL)
    gt = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            gt[j["id"].replace("/", "__")] = j["reading"]

    crops = sorted(CROPS.glob("*.png"))
    exact = wrong = blank = 0
    misses = []
    for p in crops:
        gt_val = gt.get(p.stem)
        if gt_val is None:
            continue
        img = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
        h, w = img.shape[:2]
        digits = []
        for c in range(3):
            cell = img[:, c * w // 3:(c + 1) * w // 3]
            cell = np.asarray(
                Image.fromarray(cell.astype(np.uint8)).resize((96, 96)),
                dtype=np.float32)
            pred = model(cell[np.newaxis], training=False).numpy()[0]
            cls = int(np.argmax(pred))
            if cls <= 9:
                digits.append(str(cls))
        while digits and digits[0] == "0":
            digits.pop(0)
        reading = "".join(digits)
        if not reading:
            blank += 1
            wrong += 1
            continue
        if int(reading) == int(gt_val):
            exact += 1
        else:
            wrong += 1
            misses.append((p.stem, gt_val, reading))
    total = exact + wrong
    print(f"crops={total} exact={exact} ({100 * exact / max(total, 1):.1f}%) "
          f"wrong={wrong} (blank {blank})")
    for m in misses[:12]:
        print("  MISS", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
