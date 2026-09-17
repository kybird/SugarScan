# 세트 B 판정용 대지 — "합격 999장이 어떻게 생겼는가"를 보여 준다.
#
# 사람이 999/1000 을 판정하려면 **999 를 봐야 한다.** 실패 1장만 보여 주고
# 판정을 요구한 것이 2026-09-17 의 잘못이었다.
#
# 고르는 법(체리피킹을 막는다):
#   1행  무작위 표본 — 시드를 출력에 박는다. 잘 나온 것만 고르지 않았다는 증거다
#   2행  숫자 필드 포함률이 가장 낮은 것들 — **합격 쪽의 바닥**이다
#   3행  검출 실패 1장
#
# 초록 = 검출기 예측 · 빨강 = 정답 상자
#
# 사용:
#   python make_setb_review_sheet.py --seed 7
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np

from synthband_box_error import digit_field_containment, poly_in_box_ratio

HERE = Path(__file__).resolve().parent
SET = HERE / "synth_coco" / "B"
PRED = HERE / "_diag" / "synthband_v0" / "B.jsonl"
CELL = (330, 420)


def tile(rec, label, field=None):
    img = cv2.imread(str(SET / "train2017" / rec["file_name"]))
    g = [int(v) for v in rec["gt"]]
    cv2.rectangle(img, (g[0], g[1]), (g[2], g[3]), (0, 0, 235), 3)
    if rec["pred"]:
        p = [int(v) for v in rec["pred"]]
        cv2.rectangle(img, (p[0], p[1]), (p[2], p[3]), (0, 225, 0), 3)
    cv2.putText(img, label, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 2)
    s = min(CELL[0] / img.shape[1], CELL[1] / img.shape[0])
    img = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)))
    pad = np.zeros((CELL[1], CELL[0], 3), np.uint8)
    pad[:img.shape[0], :img.shape[1]] = img
    return pad


def band(tiles, title, color, width):
    head = np.full((40, width, 3), 25, np.uint8)
    cv2.putText(head, title, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.72, color, 2)
    row = np.hstack(tiles)
    if row.shape[1] < width:
        row = np.pad(row, ((0, 0), (0, width - row.shape[1]), (0, 0)))
    return np.vstack([head, row[:, :width]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--out", default=str(HERE / "_diag" / "synthband_v0" /
                                         "setB_review.png"))
    args = ap.parse_args()

    rows = [json.loads(l) for l in
            PRED.read_text(encoding="utf-8").splitlines() if l.strip()]
    hit = [r for r in rows if r["pred"]]
    miss = [r for r in rows if not r["pred"]]

    fields = digit_field_containment(SET / "manifest.jsonl")
    for r in hit:
        r["field"] = poly_in_box_ratio(fields[r["file_name"]], r["pred"])

    rnd = random.Random(args.seed).sample(hit, args.n)
    worst = sorted(hit, key=lambda r: r["field"])[:args.n]

    width = args.n * CELL[0]
    parts = [
        band([tile(r, f"score {r['score']:.2f}  fld {r['field']:.2f}")
              for r in rnd],
             f"PASS - random {args.n} of {len(hit)}  (seed {args.seed}, not cherry-picked)",
             (0, 225, 0), width),
        band([tile(r, f"score {r['score']:.2f}  fld {r['field']:.2f}")
              for r in worst],
             f"PASS - WORST {args.n} of {len(hit)} by digit-field coverage (the floor)",
             (0, 215, 255), width),
        band([tile(r, "NO BOX at conf 0.25") for r in miss],
             f"FAIL - {len(miss)} of {len(rows)}", (0, 120, 255), width),
    ]
    legend = np.full((44, width, 3), 25, np.uint8)
    cv2.putText(legend, "green=detector prediction   red=ground truth   "
                        "fld=fraction of digit field inside the box",
                (10, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), np.vstack(parts + [legend]))
    print(f"합격 {len(hit)} · 실패 {len(miss)} -> {out}")
    print(f"  무작위 표본 시드 {args.seed} · 최악은 숫자 필드 포함률 기준")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
