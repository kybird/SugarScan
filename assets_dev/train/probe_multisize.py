# 2026-11-19 — 검출기 입력 해상도 축 프로브(자).
#
# 정황: 앱 배포 ONNX 은 640 입력(export_deploy_onnx image[1,1,640,640])인데
# 학습·재판 체크포인트는 416. 실사진(최대 4160px)은 416 레터박스에서 작은
# 밴드가 ~30px 로 찍힌다. 해상도를 훈련 없이 추론만 바꿔서 잰다:
#   1) GEN9 게이트 실패 21건의 점수가 640/832 에서 오르는가
#   2) 640 추론 정책의 전체 성적(앱 확정 규칙 그대로)
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from band_net import BandNet, decode
from train_band import letterbox
from probe_conf_rules import LABELS, load_oriented, load_reader_logits
from eval_reject_stages import (CONF_GATE, MIN_FRAC, VLO, VHI)

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="band_out/ps9_det_neg25.pt")
    ap.add_argument("--reader", default="reader_out/ps9_rdr_neg/best.pt")
    ap.add_argument("--judge", default="_diag/judge_GEN9 둘다(코드화면.jsonl")
    args = ap.parse_args()

    ck = torch.load(args.ckpt, map_location="cpu")
    model = BandNet(width=ck.get("width", 1.0), stride=ck.get("stride", 16))
    model.load_state_dict(ck["model"])
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(dev).eval()

    def run(img, size):
        lb, r, dx, dy = letterbox(img, size)
        x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            o, g = model(x.to(dev))
        b, sc = decode(o.float(), g.float(), model.stride)
        return b[0].cpu().numpy(), float(sc[0].cpu()), (r, dx, dy)

    read = load_reader_logits(args.reader)

    rows = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            rows[j["id"].split("/", 1)[1]] = j

    SIZES = (416, 640, 832)
    gate_miss = set()
    for l in open(args.judge, encoding="utf-8"):
        r = json.loads(l)
        if r["gt"] is not None and r["stage"] == "검출게이트":
            gate_miss.add(r["id"])

    out = {}
    for stem, gt in sorted(rows.items()):
        img = load_oriented(stem)
        rec = {"id": stem, "per": {},
               "gt": gt.get("value") if gt.get("source") == "human" else None}
        for size in SIZES:
            b, score, (r, dx, dy) = run(img, size)
            p = [(b[0] - dx) / r, (b[1] - dy) / r,
                 (b[2] - dx) / r, (b[3] - dy) / r]
            frac = ((p[2] - p[0]) * (p[3] - p[1])
                    / (img.shape[0] * img.shape[1]))
            s_rec = {"score": round(score, 3)}
            if score >= CONF_GATE and frac >= MIN_FRAC:
                crop = img[max(0, int(p[1])):min(img.shape[0], int(p[3])),
                           max(0, int(p[0])):min(img.shape[1], int(p[2]))]
                text, probs = read(crop)
                worst = float(np.min(probs)) if len(probs) else 0.0
                s_rec["text"] = text
                s_rec["worst"] = round(worst, 3)
                s_rec["confirmed"] = bool(text.isdigit()
                                          and VLO <= int(text) <= VHI
                                          and worst >= 0.85)
            rec["per"][size] = s_rec
        best = max(SIZES, key=lambda s: rec["per"][s]["score"])
        rec["best_size"] = best
        rec.update({k: v for k, v in rec["per"][best].items()
                    if k != "score"})
        rec["best"] = rec["per"][best]["score"]
        out[stem] = rec

    # 1) 게이트 실패 21건의 멀티사이즈 최고 점수
    print("GEN9 게이트실패 21건 — 최고사이즈 점수:")
    rescued = 0
    for stem in sorted(gate_miss):
        r = out[stem]
        mark = ""
        if r["best"] >= CONF_GATE:
            rescued += 1
            mark = " (게이트 통과)"
        print(f"  best {r['best']:.3f} @{r['best_size']}{mark} · {stem[-14:]}")
    print(f"통과 {rescued}/{len(gate_miss)}")

    # 2) 크기별 단독 정책 + 최고사이즈 정책 전체 성적
    vals = [r for r in out.values() if r["gt"] is not None]
    traps = [r for r in out.values() if r["gt"] is None]

    def score_of(get):
        """get(r) -> 해당 정책의 rec(None 가능). confirmed rec 의 text 로 채점."""
        c = w = k = 0
        for r in vals:
            rec = get(r)
            if rec and rec.get("confirmed"):
                if int(rec["text"]) == r["gt"]:
                    c += 1
                else:
                    w += 1
        for r in traps:
            rec = get(r)
            if rec and rec.get("confirmed"):
                k += 1
        return c, w, k

    for size in SIZES:
        c, w, k = score_of(lambda r, s=size: r["per"][s])
        print(f"{size} 단독:    정닥 {c:3d}({c/len(vals)*100:4.1f}%) · "
              f"오답 {w:2d}({w/len(vals)*100:4.1f}%) · 함정 {k:2d}/{len(traps)}")
    c, w, k = score_of(lambda r: r if r.get("confirmed") else None)
    print(f"최고사이즈: 정닥 {c:3d}({c/len(vals)*100:4.1f}%) · "
          f"오답 {w:2d}({w/len(vals)*100:4.1f}%) · 함정 {k:2d}/{len(traps)}")
    print("GEN9 416 재판 기준: 정닥 96(46.4%) · 오답 9(4.3%) · 함정 9/31")

    Path(HERE / "_diag").mkdir(exist_ok=True)
    with open(HERE / "_diag" / "multisize_ps9.jsonl", "w", encoding="utf-8") as f:
        for r in out.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
