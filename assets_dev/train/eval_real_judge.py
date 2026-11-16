# Datacluster 238 목표축 재판 — 사람 정답표로 전 파이프라인을 채점한다.
#
# 설계 pure-synthetic-psg-design.md §0·§4: 이 스크립트가 내는 판정이 이
# 프로젝트의 "해결" 정의다(합성 지표는 방향 확인용). 대상: 제품 번들 vs
# PS 계보 짝비교. 정답표 dc238_labels.jsonl(측정 전용 — 학습 미사용).
#
# 앱 확정 규칙 재현: EXIF 지향 이미지 → 검출 게이트(0.25·면적2%) → 리더
# greedy(비었으면 탈락) → 값 파싱(mg/dL 10..600 정수) → 최약자리 확신도
# 0.85. 결정적 모델의 3회 합의는 1회 판정과 같다(사진 가져오기 규약).
#
# 사용:
#   python eval_real_judge.py --detector bundle --reader bundle \
#       --name "제품 번들" [--out report.md]
#   python eval_real_judge.py --detector band_out/ps_det_neg25.pt \
#       --reader reader_out/ps_rdr_neg/best.pt --name "PS 둘다"
import argparse
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from eval_reject_stages import (CONF_GATE, MIN_FRAC, READ_CONF, VLO, VHI,
                                conf_of, load_detector, load_reader)

HERE = Path(__file__).resolve().parent
DC = HERE.parent / "upstream" / "datacluster-glucometer-ocr"
IMG = DC / "glucometer_images"
LABELS = HERE / "dc238_labels.jsonl"


def load_oriented(stem):
    """EXIF 지향 그레이스케일 — webtool 표시·앱 디코드와 같은 관례."""
    with Image.open(IMG / f"{stem}.jpg") as im:
        return np.asarray(ImageOps.exif_transpose(im).convert("L"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", required=True)
    ap.add_argument("--reader", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    det_run, _ = load_detector(args.detector)
    read = load_reader(args.reader)
    rows = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            rows[j["id"].split("/", 1)[1]] = j

    pos = Counter()
    pos_n = 0
    trap = Counter()
    trap_n = 0
    detail = []
    for stem, gt in sorted(rows.items()):
        img = load_oriented(stem)
        b, score, (r, dx, dy) = det_run(img)
        p = [(b[0] - dx) / r, (b[1] - dy) / r, (b[2] - dx) / r, (b[3] - dy) / r]
        frac = ((p[2] - p[0]) * (p[3] - p[1]) / (img.shape[0] * img.shape[1]))
        stage = "검출게이트"
        text = ""
        conf = 0.0
        val = None
        if score >= CONF_GATE and frac >= MIN_FRAC:
            stage = "판독"
            crop = img[max(0, int(p[1])):min(img.shape[0], int(p[3])),
                       max(0, int(p[0])):min(img.shape[1], int(p[2]))]
            text, conf = read(crop)
            if text:
                stage = "값검증"
                if text.isdigit() and VLO <= int(text) <= VHI:
                    val = int(text)
                    stage = "확신도"
                    if conf >= READ_CONF:
                        stage = "확정"
        # 채점: 값 있는 사진은 확정==GT 만 정답. 값 없음(함정)은 확정 자체가 오답.
        if gt["source"] == "human" and gt["value"] is not None:
            pos_n += 1
            if val is None:
                pos[f"미확정({stage})"] += 1
                outcome = "미확정"
            elif val == gt["value"]:
                pos["정답 확정"] += 1
                outcome = "정답"
            else:
                pos["오답 확정"] += 1
                outcome = f"오답({val})"
        else:
            trap_n += 1
            if val is None:
                trap["거절(정상)"] += 1
                outcome = "거절"
            else:
                trap["오답 확정(함정통과)"] += 1
                outcome = f"함정통과({val})"
        detail.append((stem, outcome, stage, gt.get("value"), val,
                       round(score, 3), round(conf, 3)))

    lines = [f"## {args.name} — DC238 재판",
             f"- 검출기 `{args.detector}` · 리더 `{args.reader}` · "
             f"EXIF 지향·앱 확정 규칙 그대로",
             f"- 값 사진 n={pos_n}: " + ", ".join(f"{k} {v}"
                                                  for k, v in pos.items()),
             f"- 함정 사진(코드/시각/꺼짐·mmol/L·불명) n={trap_n}: "
             + ", ".join(f"{k} {v}" for k, v in trap.items()),
             "- 오답 확정·함정통과 명세:"]
    for d in detail:
        if d[1].startswith("오답") or d[1].startswith("함정"):
            lines.append(f"  - {d[0][-16:]}: {d[1]} · 단계 {d[2]} · "
                         f"GT {d[3]} · 판독 {d[4]} · 검출 {d[5]} · 확신 {d[6]}")
    txt = "\n".join(lines)
    print(txt)
    if args.out:
        with open(args.out, "a", encoding="utf-8") as f:
            f.write(txt + "\n\n")
    with open(HERE / "_diag" / f"judge_{args.name[:12]}.jsonl", "w",
              encoding="utf-8") as f:
        for d in detail:
            f.write(json.dumps(dict(zip(
                ("id", "outcome", "stage", "gt", "pred", "det", "conf"), d)),
                ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
