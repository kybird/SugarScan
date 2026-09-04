# reader_model을 hold-out(파인튜닝에 안 쓴 Datumo 장)에서 평가한다.
# 산출: reader_preds.json {id: [pred, gt]} — 라벨러 모니터 표시용.
import json
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
MODEL = HERE / "reader_model"
DATUMO = HERE.parent / "upstream" / "datumo"
GM_QUADS = HERE / "gmscreen_quads.jsonl"
LABELED = HERE / "labeled.jsonl"
PREDS = HERE / "reader_preds.json"
IN_H, IN_W = 160, 320
NUM_CLASSES = 11


def main() -> int:
    model = tf.keras.models.load_model(MODEL)
    logits_model = tf.keras.Model(
        model.get_layer("img").input,
        model.get_layer("logits").output)

    labeled = set()
    for l in LABELED.read_text(encoding="utf-8").splitlines():
        if l.strip():
            labeled.add(json.loads(l)["id"])

    quads = {}
    for l in GM_QUADS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j["quad"]

    readings = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            readings[j["id"]] = j["reading"]
    corrections = {}
    corr = HERE / "gt_corrections.jsonl"
    if corr.exists():
        for l in corr.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                corrections[j["id"]] = j["corrected"]

    exact = wrong = skipped = 0
    misses = []
    preds_out = {}
    for cid, quad in quads.items():
        if cid in labeled:
            continue
        gt = corrections.get(cid) or str(readings.get(cid))
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            skipped += 1
            continue
        try:
            with Image.open(p) as pil:
                pil.load()
                # 좌표 정본은 표시(EXIF 적용) 이미지다. gmscreen_quads.jsonl 은
                # cv2.imread(EXIF 적용)로 만들어진 표시 좌표계인데 PIL 은 EXIF 를
                # 무시한다 — 여기서 굽지 않으면 원본의 83.5%(orientation=6)에
                # 옆으로 누운 이미지에 올바른 좌표를 물려 평가가 통째로 망가진다.
                # 실측: 이 한 줄 유무로 완전일치 14.7% ↔ 90.7% (표본 300).
                pil = ImageOps.exif_transpose(pil)
                img = cv2.cvtColor(
                    np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        except Exception:
            skipped += 1
            continue
        q = np.array(quad, dtype=np.float32)
        xs, ys = q[:, 0], q[:, 1]
        src = np.array(
            [[xs.min(), ys.min()], [xs.max(), ys.min()],
             [xs.max(), ys.max()], [xs.min(), ys.max()]], dtype=np.float32)
        dst = np.array(
            [[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1], [0, IN_H - 1]],
            dtype=np.float32)
        rect = cv2.warpPerspective(
            img, cv2.getPerspectiveTransform(src, dst), (IN_W, IN_H))
        x = rect[np.newaxis, ..., np.newaxis].astype(np.float32)
        logits = logits_model.predict(x, verbose=0)[0]
        seq = np.argmax(logits, axis=-1)
        s = []
        prev = -1
        for v in seq:
            v = int(v)
            if v != prev and v != NUM_CLASSES - 1:
                s.append(str(v))
            prev = v
        reading = "".join(s)
        preds_out[cid] = [reading, gt]
        if reading == gt:
            exact += 1
        else:
            wrong += 1
            misses.append((cid, gt, reading))

    PREDS.write_text(json.dumps(preds_out, ensure_ascii=False), encoding="utf-8")
    total = exact + wrong
    print(f"hold-out total={total} (skipped {skipped})")
    print(f"exact={exact} ({100 * exact / max(total, 1):.1f}%) wrong={wrong}")
    for m in misses[:15]:
        print("  MISS", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
