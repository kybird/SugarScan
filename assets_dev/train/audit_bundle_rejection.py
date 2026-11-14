"""Probe the bundled ONNX models with deterministic inputs and a scale control.

This is a small desktop smoke test, not a field false-acceptance estimate.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from export_deploy_onnx import (
    CONF_GATE, MIN_FRAC, decode_np, greedy_np, letterbox, run_reader_onnx,
)


def fixtures():
    yield "plain", np.full((640, 480), 170, np.uint8)
    for i, label in enumerate(("ABCDE", "SALE", "12:58", "123", "#@#@")):
        for scale in (1.6, 3.0, 4.0):
            image = np.full((640, 480), 195, np.uint8)
            cv2.putText(image, label, (16, 360), cv2.FONT_HERSHEY_SIMPLEX,
                        scale, 35, 6, cv2.LINE_AA)
            yield f"text_{i}_{scale}", image
    rng = np.random.default_rng(11)
    for i in range(12):
        image = np.full((640, 480), 180, np.uint8)
        for _ in range(120):
            x, y = rng.integers((15, 180), (459, 450))
            w, h = rng.integers((4, 4), (48, 48))
            shade = int(rng.integers(20, 235))
            cv2.rectangle(image, (x, y), (x + w, y + h), shade, -1)
        yield f"pattern_{i:02}", image


def probe(image, detector, reader):
    lb, scale, dx, dy = letterbox(image, 640)
    obj, reg = detector.run(None, {"image": lb[None, None].astype(np.float32) / 255})
    box, score = decode_np(obj[0, 0], reg[0], 16)
    x0, y0, x1, y1 = (float(v - off) / scale
                       for v, off in zip(box, (dx, dy, dx, dy)))
    h, w = image.shape
    fraction = (x1 - x0) * (y1 - y0) / (w * h)
    row = dict(score=round(score, 4), fraction=round(fraction, 4),
               box=[round(v, 1) for v in (x0, y0, x1, y1)],
               detector_pass=False)
    if score < CONF_GATE or fraction < MIN_FRAC:
        return row
    crop = image[max(0, int(y0)):min(h, round(y1)),
                 max(0, int(x0)):min(w, round(x1))]
    if crop.ndim != 2 or min(crop.shape) < 4:
        return row
    logits = run_reader_onnx(reader, cv2.resize(crop, (144, 96)))
    ids = logits.argmax(axis=1)
    previous = np.r_[-1, ids[:-1]]
    peaks = logits[(ids != previous) & (ids != 10)]
    confidence = float((1 / np.exp(peaks - peaks.max(axis=1, keepdims=True))
                        .sum(axis=1)).min()) if len(peaks) else 0.0
    return dict(row, detector_pass=True, reading=greedy_np(logits),
                confidence=round(confidence, 4))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--positive", type=Path,
                        help="Known meter photo to place at several frame scales")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    models = Path(__file__).resolve().parents[2] / "assets" / "models"
    sessions = []
    for name in ("band_detector", "reader_crnn"):
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        sessions.append(ort.InferenceSession(str(models / f"{name}.onnx"),
                                             options, providers=["CPUExecutionProvider"]))
    cases = list(fixtures())
    if args.positive is not None:
        source = cv2.imread(str(args.positive), cv2.IMREAD_GRAYSCALE)
        if source is None:
            parser.error(f"Cannot read {args.positive}")
        cases.append(("positive_original", source))
        h, w = source.shape
        for fraction in (0.9, 0.65, 0.45, 0.3):
            scale = fraction * min(480 / w, 640 / h)
            width, height = round(w * scale), round(h * scale)
            x, y = (480 - width) // 2, (640 - height) // 2
            frame = np.full((640, 480), 170, np.uint8)
            frame[y:y + height, x:x + width] = cv2.resize(source, (width, height))
            cases.append((f"positive_{fraction}", frame))
    with (args.out / "results.jsonl").open("w", encoding="utf-8") as report:
        for name, image in cases:
            cv2.imwrite(str(args.out / f"{name}.png"), image)
            row = dict(id=name, **probe(image, *sessions))
            report.write(json.dumps(row) + "\n")
            print(json.dumps(row))


if __name__ == "__main__":
    main()
