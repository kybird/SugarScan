# 2026-11-19 — 빈 판독 19건 전처리 구출 프로브(자).
#
# PaddleOCR 분석에서 온 방향: 그쪽은 증강을 세게 걸어 도메인을 흡수하지만,
# 우리는 먼저 추론 시점 전처리로 얼마나 구출되는지 잰다(재학습 불필요,
# 앱 배포에도 바로 적용 가능한 형태). GEN9 재판에서 리더가 빈 값을 낸
# 사진(stage=판독)에 6가지 전처리를 각각 걸고 변화를 본다.
#
#   python probe_preprocess.py --detector band_out/ps9_det_neg25.pt \
#       --reader reader_out/ps9_rdr_neg/best.pt
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from eval_reject_stages import CONF_GATE, MIN_FRAC, VLO, VHI, load_detector
from probe_conf_rules import LABELS, load_oriented, load_reader_logits

HERE = Path(__file__).resolve().parent


def clahe(crop):
    c = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return c.apply(crop)


def stretch(crop):
    lo, hi = np.percentile(crop, [2, 98])
    if hi - lo < 1:
        return crop
    return np.clip((crop.astype(np.float32) - lo) / (hi - lo) * 255,
                   0, 255).astype(np.uint8)


def unsharp(crop):
    blur = cv2.GaussianBlur(crop, (0, 0), 3)
    return cv2.addWeighted(crop, 2.0, blur, -1.0, 0)


def otsu(crop):
    _, b = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return b


def upscale2(crop):
    return cv2.resize(crop, (crop.shape[1] * 2, crop.shape[0] * 2),
                      interpolation=cv2.INTER_CUBIC)


VARIANTS = {
    "원본":    lambda c: c,
    "CLAHE":   clahe,
    "스트레치": stretch,
    "언샵":    unsharp,
    "오츠":    otsu,
    "업스케일2": upscale2,
    "CLAHE+언샵": lambda c: unsharp(clahe(c)),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", required=True)
    ap.add_argument("--reader", required=True)
    ap.add_argument("--judge", default="_diag/judge_GEN9 둘다(코드화면.jsonl",
                    help="빈 판독 사진을 가져올 GEN9 재판 jsonl")
    args = ap.parse_args()
    det_run, _ = load_detector(args.detector)
    read = load_reader_logits(args.reader)

    rows = [json.loads(l) for l in open(args.judge, encoding="utf-8")]
    # stage=판독 = 게이트 통과했는데 리더가 빈 값을 낸 값 사진
    targets = [r for r in rows
               if r["gt"] is not None and r["stage"] == "판독"]
    print(f"빈 판독 사진: {len(targets)}건")

    labs = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labs[j["id"].split("/", 1)[1]] = \
                [t for t in ("rot90", "rot45", "faint") if j.get(t)]

    results = {name: {"구출정닥": 0, "구출오답": 0, "값나옴": 0, "여전빈값": 0}
               for name in VARIANTS}
    for r in targets:
        img = load_oriented(r["id"])
        b, score, (rr, dx, dy) = det_run(img)
        p = [(b[0] - dx) / rr, (b[1] - dy) / rr,
             (b[2] - dx) / rr, (b[3] - dy) / rr]
        crop = img[max(0, int(p[1])):min(img.shape[0], int(p[3])),
                   max(0, int(p[0])):min(img.shape[1], int(p[2]))]
        tag = labs.get(r["id"], [])
        for name, fn in VARIANTS.items():
            text, probs = read(fn(crop))
            if not text:
                results[name]["여전빈값"] += 1
            else:
                results[name]["값나옴"] += 1
                inr = text.isdigit() and VLO <= int(text) <= VHI
                if inr and int(text) == r["gt"]:
                    results[name]["구출정닥"] += 1
                elif inr:
                    results[name]["구출오답"] += 1
    print(f"{'전처리':12} 구출정닥  구출오답  값나옴  여전빈값")
    for name, s in results.items():
        print(f"{name:12} {s['구출정닥']:6d} {s['구출오답']:8d} "
              f"{s['값나옴']:8d} {s['여전빈값']:8d}")


if __name__ == "__main__":
    main()
