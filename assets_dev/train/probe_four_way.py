# 2026-11-18 밤 자율주행 ② — 4방향 회전 검출 프로브(자).
#
# 리더는 구조적으로 90° 회전 숫자를 못 읽는다(높이축 풀링). 해법 가설은
# "프레임을 0/90/180/270 돌려 검출점수가 가장 높은 방향으로 세워서 판독".
# 이 프로브는 그 가설의 전제를 잰다:
#   1) 게이트실패 21건이 회전하면 점수가 오르는가
#   2) rot90 태그 사진의 최고 방향 점수
#   3) 최고 방향에서 판독하면 정닥이 나오는가 (확신도는 현행 worst@0.85)
#
#   python probe_four_way.py --detector band_out/ps9_det_neg25.pt \
#       --reader reader_out/ps9_rdr_neg/best.pt --out _diag/four_way_ps9.jsonl
import argparse
import json
from pathlib import Path

import numpy as np

from eval_reject_stages import (CONF_GATE, MIN_FRAC, READ_CONF, VLO, VHI,
                                load_detector)
from probe_conf_rules import LABELS, load_oriented, load_reader_logits

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detector", required=True)
    ap.add_argument("--reader", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    det_run, _ = load_detector(args.detector)
    read = load_reader_logits(args.reader)

    rows = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            rows[j["id"].split("/", 1)[1]] = j

    out_rows = []
    for stem, gt in sorted(rows.items()):
        img = load_oriented(stem)
        best = None
        scores = []
        for k in range(4):
            im = np.ascontiguousarray(np.rot90(img, k))
            b, score, (r, dx, dy) = det_run(im)
            scores.append(round(float(score), 3))
            p = [(b[0] - dx) / r, (b[1] - dy) / r,
                 (b[2] - dx) / r, (b[3] - dy) / r]
            frac = ((p[2] - p[0]) * (p[3] - p[1])
                    / (im.shape[0] * im.shape[1]))
            if best is None or score > best[0]:
                best = (score, k, p, frac, im)
        score, k, p, frac, im = best
        rec = {"id": stem, "scores": scores, "best_k": k,
               "best": round(float(score), 3),
               "gt": gt.get("value") if gt.get("source") == "human" else None}
        if score >= CONF_GATE and frac >= MIN_FRAC:
            crop = im[max(0, int(p[1])):min(im.shape[0], int(p[3])),
                      max(0, int(p[0])):min(im.shape[1], int(p[2]))]
            text, probs = read(crop)
            rec["text"] = text
            rec["worst"] = round(float(np.min(probs)), 3) if len(probs) else 0.0
            rec["in_range"] = bool(text.isdigit()
                                   and VLO <= int(text) <= VHI)
            rec["confirmed"] = bool(rec["in_range"] and rec["worst"] >= READ_CONF)
        out_rows.append(rec)

    vals = [r for r in out_rows if r["gt"] is not None]
    traps = [r for r in out_rows if r["gt"] is None]
    c = sum(1 for r in vals if r.get("confirmed") and int(r["text"]) == r["gt"])
    w = sum(1 for r in vals if r.get("confirmed") and int(r["text"]) != r["gt"])
    k = sum(1 for r in traps if r.get("confirmed"))
    print(f"4방향(최고방향 판독, worst@0.85): 값 {len(vals)} 중 "
          f"정닥 {c} ({c/len(vals)*100:.1f}%) · 오답 {w} ({w/len(vals)*100:.1f}%) · "
          f"함정 {k}/{len(traps)} ({k/len(traps)*100:.1f}%)")
    print("기준(GEN9 0방향): 정닥 96 (46.4%) · 오답 9 (4.3%) · 함정 9/31")

    # 게이트실패·rot90 사진의 방향별 점수
    labels = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labels[j["id"].split("/", 1)[1].rsplit(".", 1)[0]] = \
                [t for t in ("rot90", "rot45", "faint") if j.get(t)]
    gate_fail = [r for r in out_rows if max(r["scores"]) < CONF_GATE]
    print(f"\n4방향 최고점수로도 게이트 미달: {len(gate_fail)}건")
    rot90 = [r for r in out_rows if "rot90" in labels.get(r["id"], [])]
    print(f"rot90 태그 {len(rot90)}건 — 방향별 점수:")
    for r in rot90:
        mark = "확정" if r.get("confirmed") else " "
        gt_v = r["gt"]
        got = r.get("text")
        ok = "O" if (r.get("confirmed") and got is not None
                     and gt_v is not None and int(got) == gt_v) else "X"
        print(f"  {mark} {ok} 점수{r['scores']} best k={r['best_k']} "
              f"GT {gt_v} 판독 {got!r} · {r['id'][-14:]}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for r in out_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"-> {args.out}")


if __name__ == "__main__":
    main()
