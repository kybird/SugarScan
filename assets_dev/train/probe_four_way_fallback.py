# 2026-11-18 밤 자율주행 ② — 4방향 폴백 정책 프로브(자).
#
# probe_four_way 결과: 최고점수 방향 선택은 오히려 전체를 악화(84/17 vs
# 96/9) — 반듯한 사진에서 다른 방향이 spuriously 높게 나오면 엉뚱한 판독.
# 반면 rot90 태그 14건 중 5건이 회전 후 정확 확정. 그래서 실제 후보는
# '폴백' 정책이다: 0° 에서 확정(게이트·판독·값검증·확신도 전부 통과)이면
# 그대로 두고, 실패한 사진만 90/180/270 중 최고점수 방향으로 다시 판독.
# 현재 성적을 깎을 수 없는 구조(확정된 사진은 재시도 안 함) — 오답 증가
# 가능성만 잰다.
#
#   python probe_four_way_fallback.py --detector ... --reader ... --out ...
import argparse
import json
from pathlib import Path

import numpy as np

from eval_reject_stages import (CONF_GATE, MIN_FRAC, READ_CONF, VLO, VHI,
                                load_detector)
from probe_conf_rules import LABELS, load_oriented, load_reader_logits


def read_at(read, im, det_run):
    """한 방향에서 게이트→판독→(text, worst, in_range, confirmed)."""
    b, score, (r, dx, dy) = det_run(im)
    p = [(b[0] - dx) / r, (b[1] - dy) / r, (b[2] - dx) / r, (b[3] - dy) / r]
    frac = ((p[2] - p[0]) * (p[3] - p[1]) / (im.shape[0] * im.shape[1]))
    if score < CONF_GATE or frac < MIN_FRAC:
        return {"gate": False, "score": round(float(score), 3)}
    crop = im[max(0, int(p[1])):min(im.shape[0], int(p[3])),
              max(0, int(p[0])):min(im.shape[1], int(p[2]))]
    text, probs = read(crop)
    worst = round(float(np.min(probs)), 3) if len(probs) else 0.0
    inr = bool(text.isdigit() and VLO <= int(text) <= VHI)
    return {"gate": True, "score": round(float(score), 3), "text": text,
            "worst": worst, "in_range": inr,
            "confirmed": bool(inr and worst >= READ_CONF)}


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
        r0 = read_at(read, np.ascontiguousarray(img), det_run)
        rec = {"id": stem, "k0": r0,
               "gt": gt.get("value") if gt.get("source") == "human" else None}
        # 폴백: 0° 미확정일 때만 3방향 최고점수로 판독
        if not r0.get("confirmed"):
            cands = []
            for k in (1, 2, 3):
                rr = read_at(read, np.ascontiguousarray(np.rot90(img, k)),
                             det_run)
                rr["k"] = k
                cands.append(rr)
            best = max(cands, key=lambda x: x["score"])
            rec["fb"] = best
        out_rows.append(rec)

    # 집계 — 확정은 k0 확정 or 폴백 확정
    vals = [r for r in out_rows if r["gt"] is not None]
    traps = [r for r in out_rows if r["gt"] is None]
    base_c = sum(1 for r in vals if r["k0"].get("confirmed")
                 and int(r["k0"]["text"]) == r["gt"])
    base_w = sum(1 for r in vals if r["k0"].get("confirmed")
                 and int(r["k0"]["text"]) != r["gt"])

    def fb_outcome(r):
        fb = r.get("fb")
        if not fb or not fb.get("confirmed"):
            return None
        return int(fb["text"]) == r["gt"] if r["gt"] is not None else "trap"

    fb_c = base_c + sum(1 for r in vals if r["k0"].get("confirmed") is False
                        and fb_outcome(r) is True)
    fb_w = base_w + sum(1 for r in vals if r["k0"].get("confirmed") is False
                        and fb_outcome(r) is False)
    base_k = sum(1 for r in traps if r["k0"].get("confirmed"))
    fb_k = base_k + sum(1 for r in traps if not r["k0"].get("confirmed")
                        and fb_outcome(r) == "trap")
    nv, nt = len(vals), len(traps)
    print(f"기준(0°만):    정닥 {base_c} ({base_c/nv*100:.1f}%) · "
          f"오답 {base_w} ({base_w/nv*100:.1f}%) · 함정 {base_k}/{nt}")
    print(f"폴백 4방향:    정닥 {fb_c} ({fb_c/nv*100:.1f}%) · "
          f"오답 {fb_w} ({fb_w/nv*100:.1f}%) · 함정 {fb_k}/{nt}")
    print("\n폴백으로 새로 확정된 사진:")
    for r in out_rows:
        if not r["k0"].get("confirmed") and r.get("fb", {}).get("confirmed"):
            ok = fb_outcome(r)
            gt = r["gt"]
            mark = "정닥" if ok is True else ("오답" if ok is False else "함정")
            print(f"  {mark} · k={r['fb']['k']} GT {gt} 판독 "
                  f"{r['fb']['text']!r} worst {r['fb']['worst']} · "
                  f"{r['id'][-14:]}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for r in out_rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"-> {args.out}")


if __name__ == "__main__":
    main()
