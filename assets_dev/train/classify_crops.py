# 밴드 크롭 → 셀 3등분 → 7seg_classifier.tflite 분류 → 조립 → GT 대조.
# CNN 판독 경로의 생존 여부를 재는 실험 스크립트.
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image

HERE = Path(__file__).resolve().parent
CROPS = HERE / "crops"
MODEL = HERE.parent.parent / "assets" / "models" / "7seg_classifier.tflite"
LABELS = HERE.parent / "upstream" / "datumo" / "labels.jsonl"
N_CELLS = 3
SCORE_MIN = 0.5


def main() -> int:
    interp = tf.lite.Interpreter(model_path=str(MODEL))
    interp.allocate_tensors()
    inp = interp.get_input_details()[0]
    ih, iw = inp["shape"][1], inp["shape"][2]
    out = interp.get_output_details()[0]
    print(f"input {inp['shape']} | output {out['shape']}")

    gt = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            gt[j["id"].replace("/", "__")] = j["reading"]

    crops = sorted(CROPS.glob("*.png"))
    exact = num_eq = wrong = 0
    examples = []
    for p in crops:
        cid = p.stem
        gt_val = gt.get(cid)
        if gt_val is None:
            continue
        img = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0
        h, w = img.shape[:2]
        digits = []
        cell_scores = []
        for c in range(N_CELLS):
            cell = img[:, c * w // N_CELLS:(c + 1) * w // N_CELLS]
            cell = np.asarray(
                Image.fromarray((cell * 255).astype(np.uint8)).resize((iw, ih)),
                dtype=np.float32) / 255.0
            interp.set_tensor(inp["index"], cell[np.newaxis])
            interp.invoke()
            scores = interp.get_tensor(out["index"])[0]
            cls = int(np.argmax(scores))
            cell_scores.append((cls, float(scores[cls])))
            if cls <= 9 and scores[cls] >= SCORE_MIN:
                digits.append(str(cls))
        # 선두 0 제거(내부 0 은 유효값 — 예: 105)
        while digits and digits[0] == "0":
            digits.pop(0)
        reading = "".join(digits) if digits else ""
        ok = reading != "" and int(reading) == int(gt_val)
        if ok:
            exact += 1
        elif reading:
            wrong += 1
            if len(examples) < 12:
                examples.append((cid, gt_val, reading,
                                 [(c, round(s, 2)) for c, s in cell_scores]))
        else:
            wrong += 1
    total = exact + wrong
    print(f"\ncrops={total} exact={exact} ({100 * exact / max(total, 1):.1f}%) wrong={wrong}")
    for e in examples:
        print("  MISS", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
