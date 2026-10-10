# 리더 실촉 파인튜닝 평가 — 검출기는 ftk5_g0.06 고정, 리더 ckpt 만 바꿔
# 폴드 holdout 에서 e2e 를 잰다(짝비교: ft 리더 vs gen2lad25000).
# 사용: python _diag/reader_ft_eval.py --reader <ckpt|base> --ids foldN/holdout_ids.json --tag foldN
import argparse
import json
import sys
from pathlib import Path

import cv2
import torch

HERE = Path(__file__).resolve().parent
TRAIN = HERE.parent
sys.path.insert(0, str(TRAIN))
from band_net import BandNet, decode  # noqa: E402
from reader_crnn import CRNN, IN_H, IN_W, NUM_CLASSES, decode_greedy  # noqa: E402
from train_band import letterbox  # noqa: E402

DATUMO = TRAIN.parent / "upstream" / "datumo"
DET = TRAIN / "band_out" / "tone" / "ftk5_g0.06"
BASE_READER = TRAIN / "reader_out" / "gen2lad25000_s8k" / "best.pt"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reader", default="base")
    ap.add_argument("--ids", required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    c = torch.load(DET, map_location="cpu", weights_only=False)
    det = BandNet(width=c["width"], stride=c.get("stride", 16)).to(dev).eval()
    det.load_state_dict(c["model"])
    rp = BASE_READER if a.reader == "base" else Path(a.reader)
    cr = torch.load(rp, map_location="cpu", weights_only=False)
    reader = CRNN(NUM_CLASSES).to(dev).eval()
    reader.load_state_dict(cr.get("model", cr))

    imgs, read = {}, {}
    for ln in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            j = json.loads(ln)
            imgs[j["id"]] = j["image"]
            read[j["id"]] = str(j.get("reading", ""))
    # holdout id는 마지막 세그먼트뿐이다 — batch1/batch2 접두를 역매핑으로 복원
    seg2full = {}
    for full in imgs:
        seg2full.setdefault(full.split("/")[-1], full)
    ids = [seg2full.get(i, "glucose_batch1/" + i) for i in
           json.loads(Path(a.ids).read_text(encoding="utf-8"))]
    e2e = {"right": 0, "wrong": 0, "blank": 0, "det": 0, "skip": 0}
    wrong_ids = []
    with torch.no_grad():
        for pid in ids:
            gt = read.get(pid, "")
            img = cv2.imread(str(DATUMO / imgs[pid]), cv2.IMREAD_GRAYSCALE)
            if img is None:
                e2e["skip"] += 1
                continue
            lb, r, dx, dy = letterbox(img, c["size"])
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            obj, reg = det(x.to(dev))
            b, s = decode(obj.float(), reg.float(), det.stride)
            b = b[0].cpu().numpy()
            sc = float(s[0].cpu())
            p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
            frac = (p[2]-p[0])*(p[3]-p[1]) / max(1., img.shape[1]*img.shape[0])
            if sc < 0.25 or frac < 0.02:
                e2e["det"] += 1
                continue
            x0, y0 = max(0, int(p[0])), max(0, int(p[1]))
            x1 = min(img.shape[1], int(round(p[2])))
            y1 = min(img.shape[0], int(round(p[3])))
            if x1-x0 < 4 or y1-y0 < 4 or not gt.isdigit():
                e2e["skip" if not gt.isdigit() else "det"] += 1
                continue
            crop = cv2.resize(img[y0:y1, x0:x1], (IN_W, IN_H))
            t = torch.from_numpy(crop).float().div_(255.).sub_(0.5).unsqueeze(0).unsqueeze(0)
            logits = reader(t.to(dev))
            pred = decode_greedy(logits[0].cpu().unsqueeze(0))[0]
            if not pred:
                e2e["blank"] += 1
                wrong_ids.append(pid)
            elif pred == str(int(gt)):
                e2e["right"] += 1
            else:
                e2e["wrong"] += 1
                wrong_ids.append(pid)
    m = e2e["right"] + e2e["wrong"] + e2e["blank"]
    res = dict(tag=a.tag, reader=str(rp), n=len(ids), e2e=e2e,
               e2e_rate=round(e2e["right"]/max(1, m), 4),
               wrong_ids=[i.split("/")[-1] for i in wrong_ids])
    print(json.dumps(dict(tag=a.tag, n=len(ids), e2e=e2e,
                          rate=res["e2e_rate"]), ensure_ascii=False))
    out = HERE / "reader_ft" / f"eval_{a.tag}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
