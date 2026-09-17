# 채택 판단용 대지 — 사람이 보고 예/아니오를 말할 수 있게.
#
# 전처리 레터박스를 운영에 넣을지는 사람이 정한다. 그런데 판단하려면 **바뀐
# 장을 봐야 한다** — 표의 중앙값으로는 "무엇을 잃는가"가 안 보인다.
# 회복한 장과 퇴보한 장을 한 판에 나란히 놓는다.
#
#   파랑 = 운영(지금 쓰는 것, stretch)
#   초록 = letterbox (채택 후보)
#   빨강 = 사람 라벨(있는 장만)
#
# 장 목록은 보고서 「장 단위 — 판정 부류가 갈린 9장」에서 온다. 여기서 다시
# 계산하지 않는다 — 인자로 받는다.
#
# 사용:
#   python make_adoption_sheet.py \
#       --recovered glucose_batch1/1046,glucose_batch1/134,glucose_batch1/607,glucose_batch1/808 \
#       --regressed glucose_batch1/1091,glucose_batch1/606,glucose_batch1/1094
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OPS = HERE / "gmscreen_quads.jsonl"
NEW = HERE / "_diag" / "preproc_ab" / "letterbox.jsonl"
HUMAN = HERE / "screen_boxes.jsonl"


def load(p, pred=lambda j: True):
    out = {}
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if pred(j):
                out[j["id"]] = j
    return out


def rect(q):
    a = np.asarray(q, float)
    return [a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()]


def tile(gid, imgrel, ops, new, human, cell=(520, 660)):
    im = cv2.imread(str(DATUMO / imgrel))
    if im is None:
        return None
    for src, col, th in ((human, (0, 0, 235), 10), (ops, (235, 140, 0), 8),
                         (new, (0, 225, 0), 8)):
        r = src.get(gid)
        if r:
            b = [int(v) for v in rect(r["quad"])]
            cv2.rectangle(im, (b[0], b[1]), (b[2], b[3]), col, th)
    # cv2.putText 는 한글을 못 그린다(물음표로 나온다). 판에 들어가는 글자는
    # 전부 ASCII 로 쓴다.
    txt = gid.split("/")[-1]
    if gid not in ops:
        txt += "  [current: NO BOX]"
    if gid not in new:
        txt += "  [letterbox: NO BOX]"
    cv2.putText(im, txt, (16, 76), cv2.FONT_HERSHEY_SIMPLEX, 2.2,
                (255, 255, 255), 6)
    s = min(cell[0] / im.shape[1], cell[1] / im.shape[0])
    im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)))
    pad = np.zeros((cell[1], cell[0], 3), np.uint8)
    pad[:im.shape[0], :im.shape[1]] = im
    return pad


def band(tiles, title, color, width, cell=(520, 660)):
    head = np.full((44, width, 3), 25, np.uint8)
    cv2.putText(head, title, (10, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                color, 2)
    row = np.hstack(tiles) if tiles else np.zeros((cell[1], width, 3), np.uint8)
    if row.shape[1] < width:
        row = np.pad(row, ((0, 0), (0, width - row.shape[1]), (0, 0)))
    return np.vstack([head, row[:, :width]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recovered", default="")
    ap.add_argument("--regressed", default="")
    ap.add_argument("--out", default=str(HERE / "_diag" / "preproc_ab" /
                                         "adoption_sheet.png"))
    args = ap.parse_args()

    ops = load(OPS)
    new = load(NEW)
    human = load(HUMAN, lambda j: j.get("source") == "human" and j.get("quad"))
    rows = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            rows[j["id"]] = j["image"]

    def tiles_for(spec):
        out = []
        for gid in [g.strip() for g in spec.split(",") if g.strip()]:
            t = tile(gid, rows[gid], ops, new, human)
            if t is not None:
                out.append(t)
        return out

    rec = tiles_for(args.recovered)
    reg = tiles_for(args.regressed)
    width = max(len(rec), len(reg), 1) * 520

    sheet = np.vstack([
        band(rec, f"RECOVERED {len(rec)} - letterbox finds it, current does not",
             (0, 225, 0), width),
        band(reg, f"REGRESSED {len(reg)} - current finds it, letterbox does not / worse",
             (0, 165, 255), width),
    ])
    legend = np.full((46, width, 3), 25, np.uint8)
    cv2.putText(legend, "blue=current(stretch)   green=letterbox   red=human label",
                (10, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), np.vstack([sheet, legend]))
    print(f"회복 {len(rec)}장 · 퇴보 {len(reg)}장 -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
