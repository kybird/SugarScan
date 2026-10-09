# 파인튜닝 검출기 폴드 평가 — IoU·포함률(라벨 대비) + e2e 판독률(리더 25k).
# 배포와 같은 게이트(conf 0.25 / 면적 2%). 기준선은 gen2_v1_step8000 의
# det_latest_holdout.json + rescore_20261009.jsonl 로 같은 id 집합만 뽑아 비교.
# 사용: python _diag/det_ft_eval.py --ckpt <pt> --ids foldN/holdout_ids.json --tag foldN
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from band_net import BandNet, decode  # noqa: E402
from reader_crnn import CRNN, IN_H, IN_W, NUM_CLASSES, decode_greedy  # noqa: E402
from train_band import letterbox  # noqa: E402

TRAIN = HERE.parent
DATUMO = TRAIN.parent / "upstream" / "datumo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    cd = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    det = BandNet(width=cd["width"], stride=cd.get("stride", 16)).to(dev).eval()
    det.load_state_dict(cd["model"])
    cr = torch.load(TRAIN / "reader_out" / "gen2lad25000_s8k" / "best.pt",
                    map_location="cpu", weights_only=False)
    reader = CRNN(NUM_CLASSES).to(dev).eval()
    reader.load_state_dict(cr["model"])

    human = {}
    for ln in (TRAIN / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            human[r["id"]] = r["quad"]
    imgs, read = {}, {}
    for ln in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            j = json.loads(ln)
            imgs[j["id"]] = j["image"]
            read[j["id"]] = str(j.get("reading", ""))

    ids = json.loads(Path(a.ids).read_text(encoding="utf-8"))
    ious, covers = [], []
    e2e = {"right": 0, "wrong": 0, "blank": 0, "det": 0, "skip": 0}
    with torch.no_grad():
        for pid in ids:
            q = human.get(pid)
            gt_read = read.get(pid, "")
            img = cv2.imread(str(DATUMO / imgs[pid]), cv2.IMREAD_GRAYSCALE)
            if img is None or q is None:
                e2e["skip"] += 1
                continue
            lb, r, dx, dy = letterbox(img, cd["size"])
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            obj, reg = det(x.to(dev))
            b, s = decode(obj.float(), reg.float(), det.stride)
            b = b[0].cpu().numpy()
            sc = float(s[0].cpu())
            p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
            gx0 = min(t[0] for t in q); gy0 = min(t[1] for t in q)
            gx1 = max(t[0] for t in q); gy1 = max(t[1] for t in q)
            ix0, iy0 = max(p[0], gx0), max(p[1], gy0)
            ix1, iy1 = min(p[2], gx1), min(p[3], gy1)
            inter = max(0., ix1-ix0) * max(0., iy1-iy0)
            union = (p[2]-p[0])*(p[3]-p[1]) + (gx1-gx0)*(gy1-gy0) - inter
            ious.append(inter/max(1., union))
            covers.append(inter/max(1., (gx1-gx0)*(gy1-gy0)))
            frac = (p[2]-p[0])*(p[3]-p[1]) / max(1., img.shape[1]*img.shape[0])
            if sc < 0.25 or frac < 0.02:
                e2e["det"] += 1
                continue
            x0, y0 = max(0, int(p[0])), max(0, int(p[1]))
            x1 = min(img.shape[1], int(round(p[2])))
            y1 = min(img.shape[0], int(round(p[3])))
            if x1-x0 < 4 or y1-y0 < 4 or not gt_read.isdigit():
                e2e["det" if x1-x0 < 4 or y1-y0 < 4 else "skip"] += 1
                continue
            crop = cv2.resize(img[y0:y1, x0:x1], (IN_W, IN_H))
            t = torch.from_numpy(crop).float().div_(255.).sub_(0.5).unsqueeze(0).unsqueeze(0)
            logits = reader(t.to(dev))
            pred = decode_greedy(logits[0].cpu().unsqueeze(0))[0]
            if not pred:
                e2e["blank"] += 1
            elif pred == str(int(gt_read)):
                e2e["right"] += 1
            else:
                e2e["wrong"] += 1
    ious = np.array(ious)
    m = e2e["right"] + e2e["wrong"] + e2e["blank"]
    res = dict(tag=a.tag, n=len(ids),
               iou_median=round(float(np.median(ious)), 4),
               iou_p10=round(float(np.percentile(ious, 10)), 4),
               iou_lt05=int((ious < 0.5).sum()), iou_lt07=int((ious < 0.7).sum()),
               cover_lt09=int((np.array(covers) < 0.9).sum()),
               e2e=e2e,
               e2e_rate=round(e2e["right"]/max(1, m), 4))
    print(json.dumps(res, ensure_ascii=False))
    out = HERE / "det_ft" / f"eval_{a.tag}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
