# 2026-11-19 지시서 §4·§5 — 동일 크롭 리더 분해 + 체크포인트 선택 진단(자).
#
# 검출기(ps10b@640)는 사진당 한 번만 돌리고 그 크롭을 고정해, 같은 바이트를
# rdr10b/rdr10d 의 best·last 에 넣는다. 문자열 차이 / 확신도 차이 /
# 검출기 크롭 차이의 세 부류로 가른다(§4). best(최초 100% 에폭) vs
# last(에폭 100) 비교는 체크포인트 선택 문제의 진단이며 사후 승자 선언이
# 아니다(§5).
import json
from pathlib import Path

import numpy as np
import torch

from eval_reject_stages import (CONF_GATE, MIN_FRAC, VLO, VHI,
                                load_detector)
from probe_conf_rules import LABELS, load_oriented, load_reader_logits

HERE = Path(__file__).resolve().parent
OUT = HERE / "_diag" / "reader_fixed_crops.jsonl"

READERS = {
    "rdr10b_best": "reader_out/ps10b_rdr/best.pt",
    "rdr10b_last": "reader_out/ps10b_rdr/last.pt",
    "rdr10d_best": "reader_out/ps10d_rdr/best.pt",
    "rdr10d_last": "reader_out/ps10d_rdr/last.pt",
}


def main():
    det_run, _ = load_detector("band_out/ps10b_det_neg25.pt")  # 416 학습 →
    # ck['size']=416 로 돈다. 640 정책과 동일 조건을 위해 size 를 덮어쓴
    # 로더가 필요하다 — 아래에서 ck 사본으로 640 세션을 만든다.
    import copy
    ck = torch.load("band_out/ps10b_det_neg25.pt", map_location="cpu")
    ck640 = dict(ck)
    ck640["size"] = 640
    torch.save(ck640, HERE / "_tmp_ps10b_640.pt")
    det640, _ = load_detector(str(HERE / "_tmp_ps10b_640.pt"))

    readers = {name: load_reader_logits(p) for name, p in READERS.items()}

    rows = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            rows[j["id"].split("/", 1)[1]] = j

    out = []
    for stem, gt in sorted(rows.items()):
        img = load_oriented(stem)
        b, score, (r, dx, dy) = det640(img)
        p = [(b[0] - dx) / r, (b[1] - dy) / r,
             (b[2] - dx) / r, (b[3] - dy) / r]
        frac = ((p[2] - p[0]) * (p[3] - p[1])
                / (img.shape[0] * img.shape[1]))
        rec = {"id": stem, "det": round(float(score), 3),
               "gate": bool(score >= CONF_GATE and frac >= MIN_FRAC),
               "gt": gt.get("value") if gt.get("source") == "human" else None}
        if rec["gate"]:
            crop = img[max(0, int(p[1])):min(img.shape[0], int(p[3])),
                       max(0, int(p[0])):min(img.shape[1], int(p[2]))]
            for name, read in readers.items():
                text, probs = read(crop)
                worst = float(np.min(probs)) if len(probs) else 0.0
                inr = bool(text.isdigit() and VLO <= int(text) <= VHI)
                rec[name] = {"text": text, "worst": round(worst, 3),
                             "probs": [round(float(x), 3) for x in probs],
                             "confirmed": bool(inr and worst >= 0.85)}
        out.append(rec)

    with open(OUT, "w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    vals = [r for r in out if r["gt"] is not None]
    traps = [r for r in out if r["gt"] is None]
    print(f"게이트 통과 {sum(1 for r in out if r['gate'])}/238\n")

    def stats(name):
        c = sum(1 for r in vals
                if r["gate"] and r[name]["confirmed"]
                and int(r[name]["text"]) == r["gt"])
        w = sum(1 for r in vals
                if r["gate"] and r[name]["confirmed"]
                and int(r[name]["text"]) != r["gt"])
        k = sum(1 for r in traps
                if r["gate"] and r[name]["confirmed"])
        blocked_ok = sum(1 for r in vals if r["gate"]
                         and r[name]["text"].isdigit()
                         and VLO <= int(r[name]["text"]) <= VHI
                         and r[name]["worst"] < 0.85
                         and int(r[name]["text"]) == r["gt"])
        return c, w, k, blocked_ok

    print(f"{'리더':14} {'정닥확정':>7} {'오답확정':>7} {'함정':>4} "
          f"{'차단(정닥)':>8}")
    for name in READERS:
        c, w, k, bo = stats(name)
        print(f"{name:14} {c:7d} {w:7d} {k:4d} {bo:8d}")

    # §4 분해 — rdr10b_best 대비 rdr10d_best, 같은 크롭에서
    A, B = "rdr10b_best", "rdr10d_best"
    fam = {"문자열상이": 0, "문자열같음_확신도만": 0, "둘다빈값": 0,
           "10b만빈값": 0, "10d만빈값": 0}
    conf_gap_ok = []
    for r in vals:
        if not r["gate"]:
            continue
        ta, tb = r[A]["text"], r[B]["text"]
        if ta == tb:
            if ta == "":
                fam["둘다빈값"] += 1
            elif r[A]["worst"] != r[B]["worst"]:
                fam["문자열같음_확신도만"] += 1
                conf_gap_ok.append((r[B]["worst"] - r[A]["worst"],
                                    ta == str(r["gt"])))
        elif ta == "":
            fam["10b만빈값"] += 1
        elif tb == "":
            fam["10d만빈값"] += 1
        else:
            fam["문자열상이"] += 1
    print(f"\n§4 분해(rdr10b_best vs rdr10d_best, 게이트통과 값사진):")
    for k, v in fam.items():
        print(f"  {k}: {v}")
    gaps = np.array([g for g, _ in conf_gap_ok])
    if len(gaps):
        print(f"  문자열 같은 행의 worst 차(10d−10b): "
              f"중앙 {np.median(gaps):+.3f} · p10 {np.percentile(gaps,10):+.3f}")

    (HERE / "_tmp_ps10b_640.pt").unlink()   # 임시 ck 정리


if __name__ == "__main__":
    main()
