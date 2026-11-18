# 2026-11-18 밤 자율주행 ① — 확신도 집계 규칙 스윕(자).
#
# 앱 규약 확신도는 "글자가 나온 스텝의 softmax 최대 확률 중 최약값"(worst)
# 이다 — 한 자리만 애매하면 전체가 깔린다. GEN9 미확정 102건 중 확신도차단이
# 42건(판독정답 29·판독오답 13)으로 최대 통이어서, worst 대신 mean/2nd-worst
# 등으로 집계를 바꾸면 정닥 확정을 몇 건 회수하는지·오답과 함정이 몇 건
# 새로 들어오는지를 잰다. 재판 흐름(eval_real_judge)을 그대로 재현하되
# 리더의 자리별 확률을 따로 저장한다.
#
#   python probe_conf_rules.py --detector band_out/ps9_det_neg25.pt \
#       --reader reader_out/ps9_rdr_neg/best.pt --out _diag/conf_rules_ps9.json
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps

from eval_reject_stages import (CONF_GATE, MIN_FRAC, VLO, VHI,
                                load_detector)
from reader_crnn import CRNN, decode_greedy

HERE = Path(__file__).resolve().parent
DC = HERE.parent / "upstream" / "datacluster-glucometer-ocr"
IMG = DC / "glucometer_images"
LABELS = HERE / "dc238_labels.jsonl"

# blank 는 CHARSET 인덱스 10(reader_crnn · eval_reject_stages.conf_of 와 동일)
BLANK_ID = 10


def load_oriented(stem):
    with Image.open(IMG / f"{stem}.jpg") as im:
        return np.asarray(ImageOps.exif_transpose(im).convert("L"))


def char_probs(logits):
    """conf_of 의 봉우리 논리를 그대로, 최약값 대신 자리별 확률 목록."""
    ids = logits.argmax(axis=1)
    prev = np.r_[-1, ids[:-1]]
    peaks = logits[(ids != prev) & (ids != BLANK_ID)]
    if not len(peaks):
        return []
    e = np.exp(peaks - peaks.max(axis=1, keepdims=True))
    return (e / e.sum(axis=1, keepdims=True)).max(axis=1)


def load_reader_logits(spec):
    """crop -> (text, 자리별 확률 배열). load_reader 와 같은 전처리."""
    ck = torch.load(spec, map_location="cpu")
    model = CRNN()
    model.load_state_dict(ck.get("model", ck))
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(dev).eval()

    def read(crop):
        x = (torch.from_numpy(cv2.resize(crop, (144, 96)).astype(np.float32))
             / 255.0 - 0.5).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            out = model(x.to(dev)).cpu()        # (1,T,C)
        probs = char_probs(out[0].numpy())
        return decode_greedy(out)[0], probs
    return read


RULES = {
    "worst":  lambda p: float(np.min(p)),
    "mean":   lambda p: float(np.mean(p)),
    "p25":    lambda p: float(np.percentile(p, 25)),
    "2ndworst": lambda p: float(np.sort(p)[1]) if len(p) > 1 else float(p[0]),
    "drop1mean": lambda p: float(np.mean(p[1:])) if len(p) > 1 else float(p[0]),
}


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

    recs = []
    for stem, gt in sorted(rows.items()):
        img = load_oriented(stem)
        b, score, (r, dx, dy) = det_run(img)
        p = [(b[0] - dx) / r, (b[1] - dy) / r, (b[2] - dx) / r, (b[3] - dy) / r]
        frac = ((p[2] - p[0]) * (p[3] - p[1]) / (img.shape[0] * img.shape[1]))
        rec = {"id": stem, "det": round(float(score), 3),
               "gt": gt.get("value") if gt.get("source") == "human" else None}
        if score >= CONF_GATE and frac >= MIN_FRAC:
            crop = img[max(0, int(p[1])):min(img.shape[0], int(p[3])),
                       max(0, int(p[0])):min(img.shape[1], int(p[2]))]
            text, probs = read(crop)
            rec["text"] = text
            rec["probs"] = [round(float(x), 4) for x in probs]
            rec["in_range"] = bool(text.isdigit() and VLO <= int(text) <= VHI)
        recs.append(rec)

    vals = [r for r in recs if r["gt"] is not None]
    traps = [r for r in recs if r["gt"] is None]
    nv, nt = len(vals), len(traps)

    def frontier(rule):
        out = []
        for t in np.arange(0.50, 0.96, 0.05):
            c = w = k = 0
            for r in vals:
                if not r.get("in_range") or not r.get("probs"):
                    continue
                conf = RULES[rule](np.array(r["probs"]))
                if conf >= t:
                    if int(r["text"]) == r["gt"]:
                        c += 1
                    else:
                        w += 1
            for r in traps:
                if r.get("in_range") and r.get("probs") \
                        and RULES[rule](np.array(r["probs"])) >= t:
                    k += 1
            out.append((round(float(t), 2), c, w, k))
        return out

    # 안전 제약: 오답확정 ≤ 10건(207의 5%) 안에서 정닥 최대인 문턱.
    result = {"n": [nv, nt], "rules": {}, "recs": [
        {k: v for k, v in r.items() if k != "probs"} | {"probs": r.get("probs")}
        for r in recs]}
    print(f"값 {nv} · 함정 {nt}")
    for rule in RULES:
        fr = frontier(rule)
        best = max((row for row in fr if row[2] <= nv * 0.05),
                   key=lambda row: row[1], default=None)
        result["rules"][rule] = {"frontier": fr, "at5pct": best}
        curve = " ".join(f"{t:.2f}:{c}/{w}/{k}" for t, c, w, k in fr)
        print(f"{rule:10} {curve}")
        print(f"{'':10} 오답≤5% 최적: {best}")

    # 값검증 탈락행의 판독문자열 — 어디서 새는지 가시화(부속 목적)
    dropped = [{"id": r["id"], "gt": r["gt"], "text": r.get("text")}
               for r in vals if r.get("text") and not r.get("in_range")]
    result["value_dropped"] = dropped
    print(f"\n값검증 탈락 {len(dropped)}건 판독문자열(일부):")
    for d in dropped[:20]:
        print(f"  GT {d['gt']:>4} · 판독 {d['text']!r} · {d['id'][-16:]}")

    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False,
                                             indent=1), encoding="utf-8")
        print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
