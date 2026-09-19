# 밴드 검출망을 **Roboflow READING 라벨**로 잰다 (실촬, n≈1,150).
#
# 2026-09-19 사람 결정: Roboflow 를 **측정 한정**으로 쓴다. 이미지가 가중치에
# 들어가지 않고 저장소에 커밋되지도 않으므로 학습 배제 결정(SPEC §5.3,
# docs/LICENSES.md)과 충돌하지 않는다. **학습에는 여전히 쓰지 않는다.**
#
# 왜 필요한가: 우리 손라벨 코퍼스(A)는 272장이고 라벨러가 우리 자신이다.
# Roboflow `glucometer_images-bc9dh` 에는 `READING`(혈당 수치 영역) 상자가
# 1,275개 있다 — **다른 사람이 다른 여백 규약으로 그린 독립 밴드 라벨**이고
# 장수가 4.7배다. 단계 2에서 두 조건의 판정이 갈렸으므로, 라벨 주체가 다른
# 코퍼스에서 다시 재는 것이 값싸고 직접적이다.
#
# 내가 앞서 "Roboflow 라벨은 LCD 라벨이라 밴드 라벨이 없다"고 적어 둔 것은
# **사실과 다르다.** docs/LICENSES.md 는 처음부터 READING 을 적고 있었다.
#
# 지표는 코퍼스 A 와 **같은 정의**다: 검출 · 밴드 전체 포함 · 면적비 · IoU.
# 그래야 두 코퍼스를 나란히 읽을 수 있다. 다만 **합격률을 합성과 한 표에
# 놓지 않는다** — 정답이 다른 물건이다.
#
# 사용: python eval_band_roboflow.py --ckpt band_out/score/bce_s0.pt ...
import argparse
import collections
import json
import time
import zipfile
from pathlib import Path

import cv2
import numpy as np
import torch

from band_net import BandNet, decode
from train_band import letterbox
from eval_band_real import contain, iou, OUT

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "upstream" / "roboflow-glucometer-images"
ZIP = ROOT / "Glucometer_images.coco.zip"
EXT = ROOT / "extracted"


def population():
    """(id -> (이미지경로, READING 상자)). 이미지가 실제로 있는 것만."""
    out = {}
    with zipfile.ZipFile(ZIP) as f:
        for split in ("train", "valid"):
            j = json.loads(f.read(f"{split}/_annotations.coco.json"))
            cat = {c["id"]: c["name"] for c in j["categories"]}
            per = collections.defaultdict(dict)
            for a in j["annotations"]:
                per[a["image_id"]][cat[a["category_id"]]] = a["bbox"]
            for im in j["images"]:
                d = per.get(im["id"], {})
                if "READING" not in d:
                    continue
                p = EXT / split / im["file_name"]
                if not p.exists():
                    continue
                b = d["READING"]
                out[f"rf/{split}/{Path(im['file_name']).stem}"] = (
                    p, [b[0], b[1], b[0] + b[2], b[1] + b[3]])
    return out


@torch.no_grad()
def evaluate(ckpt, conf=0.25, limit=0):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    c = torch.load(ckpt, map_location="cpu", weights_only=False)
    model = BandNet(width=c["width"]).to(dev).eval()
    model.load_state_dict(c["model"])
    size = c["size"]
    name = f"roboflow_{Path(ckpt).stem}"

    pop = population()
    ids = sorted(pop)
    if limit:
        ids = ids[:limit]
    OUT.mkdir(parents=True, exist_ok=True)
    res = OUT / f"{name}.jsonl"
    rows = []
    t0 = time.time()
    with res.open("w", encoding="utf-8") as f:
        for cid in ids:
            path, gt = pop[cid]
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            lb, r, dx, dy = letterbox(img, size)
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            obj, reg = model(x.to(dev))
            b, s = decode(obj.float(), reg.float(), model.stride)
            b = b[0].cpu().numpy()
            sc = float(s[0].cpu())
            p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
            det = sc >= conf
            ga = max(1.0, (gt[2]-gt[0]) * (gt[3]-gt[1]))
            row = {"id": cid, "ow": int(img.shape[1]), "oh": int(img.shape[0]),
                   "score": round(sc, 4), "det": bool(det),
                   "pred": [round(v, 1) for v in p],
                   "gt": [round(v, 1) for v in gt],
                   "iou": round(iou(p, gt), 4) if det else 0.0,
                   "contain": round(contain(gt, p), 4) if det else 0.0,
                   "area_ratio": round(
                       max(0.0, p[2]-p[0]) * max(0.0, p[3]-p[1]) / ga, 4),
                   "wide": bool(img.shape[1] > img.shape[0])}
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n = len(rows)
    hit = [r for r in rows if r["det"]]
    cv_ = np.array([r["contain"] for r in hit]) if hit else np.array([0.0])
    ar = np.array([r["area_ratio"] for r in hit]) if hit else np.array([0.0])
    ok = np.array([r["contain"] >= 0.999 and r["area_ratio"] <= 2.0
                   for r in rows])
    print(f"{name}  n={n} · 검출 실패 {n-len(hit)}")
    print(f"  포함 1.0 {100*(cv_>=0.999).mean():.2f}%  "
          f"· 면적비 p50 {np.median(ar):.2f} p90 {np.percentile(ar,90):.2f}")
    print(f"  **τ=2.0 게이트 {100*ok.mean():.2f}%**  -> {res}")
    print(f"  ({time.time()-t0:.0f}s) · 라벨 주체가 다른 코퍼스다 — "
          f"코퍼스 A 와 절대값을 맞대지 말 것")
    return {"name": name, "n": n, "miss": n-len(hit),
            "gate": float(ok.mean()), "contain1": float((cv_ >= .999).mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    for c in a.ckpt:
        evaluate(c, a.conf, a.limit)
        print()


if __name__ == "__main__":
    main()
