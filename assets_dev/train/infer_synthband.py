# 합성 밴드 검출기(synthband) 추론 — COCO 세트 한 벌에 돌려 상자를 낸다.
#
# 전처리는 YOLOX 의 ValTransform 을 그대로 부른다(레터박스 + BGR). 직접 resize
# 를 짜면 학습은 레터박스인데 추론만 스트레치가 되는 자리가 생긴다 — 그게
# 이미 열려 있는 카드다(GM 검출 추론 전처리를 학습과 맞춘다). 같은 벽을 두 번
# 치지 않으려고 여기서는 기하를 재구현하지 않는다.
#
# 산출: --out jsonl (장마다 pred/gt/iou)  ·  --sheet png (눈 확인판)
#
#   python infer_synthband.py --set synth_coco/C \
#       --ckpt yolox_out/synthband_v0/best_ckpt.pth \
#       --out _diag/synthband_v0/C.jsonl --sheet _diag/synthband_v0/C_pred.png
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

sys.path.insert(0, "D:/tmp/YOLOX")
from yolox.data.data_augment import ValTransform  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402

HERE = Path(__file__).resolve().parent
EXP_FILE = str(HERE / "yolox_synthband_exp.py")


def iou_xyxy(a, b):
    x0 = max(a[0], b[0]); y0 = max(a[1], b[1])
    x1 = min(a[2], b[2]); y1 = min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    ua = ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)
    return inter / ua if ua > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, help="COCO 세트 디렉터리")
    ap.add_argument("--split", default="train2017")
    ap.add_argument("--ann", default=None, help="기본: annotations/instances_<split>.json")
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--exp", default=EXP_FILE)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--sheet-n", type=int, default=10)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--device", default="cuda",
                    help="다른 학습이 GPU 를 쓰는 동안 cpu 로 돌린다")
    ap.add_argument("--nms", type=float, default=0.45)
    args = ap.parse_args()

    root = Path(args.set)
    ann_path = Path(args.ann) if args.ann else \
        root / "annotations" / f"instances_{args.split}.json"
    coco = json.loads(ann_path.read_text(encoding="utf-8"))
    gt = {a["image_id"]: a["bbox"] for a in coco["annotations"]}

    exp = get_exp(args.exp, None)
    dev = torch.device(args.device)
    model = exp.get_model().to(dev).eval()
    ckpt = torch.load(args.ckpt, map_location="cpu")
    model.load_state_dict(ckpt["model"])
    preproc = ValTransform(legacy=False)
    tsize = exp.test_size
    print(f"ckpt {args.ckpt} · test_size {tsize} · conf {args.conf} nms {args.nms}")

    rows = []
    for im in coco["images"]:
        img = cv2.imread(str(root / args.split / im["file_name"]))
        assert img is not None, im["file_name"]
        ratio = min(tsize[0] / img.shape[0], tsize[1] / img.shape[1])
        t, _ = preproc(img, None, tsize)
        with torch.no_grad():
            out = postprocess(
                model(torch.from_numpy(t).unsqueeze(0).float().to(dev)),
                              exp.num_classes, args.conf, args.nms, class_agnostic=True)[0]
        g = gt[im["id"]]
        gxy = [g[0], g[1], g[0] + g[2], g[1] + g[3]]
        rec = {"id": im["id"], "file_name": im["file_name"], "gt": gxy}
        if out is None or len(out) == 0:
            rec.update(pred=None, score=None, iou=0.0)
        else:
            o = out.cpu().numpy()
            o = o[np.argmax(o[:, 4] * o[:, 5])]           # 최고 점수 하나
            p = (o[:4] / ratio).tolist()                   # 레터박스 역산
            rec.update(pred=[round(v, 2) for v in p],
                       score=round(float(o[4] * o[5]), 4),
                       n_det=int(len(out)),
                       iou=round(iou_xyxy(p, gxy), 4))
        rows.append(rec)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ious = np.array([r["iou"] for r in rows])
    miss = sum(1 for r in rows if r["pred"] is None)
    print(f"n={len(rows)} (모집단: {ann_path})  검출 실패 {miss}장")
    print(f"IoU 중앙 {np.median(ious):.4f} · 평균 {ious.mean():.4f} · "
          f"최소 {ious.min():.4f} · >=0.5 {int((ious >= .5).sum())}장 "
          f"· >=0.75 {int((ious >= .75).sum())}장")
    print(f"-> {outp}")

    if args.sheet:
        sheet(root, args.split, rows, Path(args.sheet), args.sheet_n)
    return 0


def sheet(root, split, rows, out_png, n, cols=5):
    """초록=예측 빨강=정답. 예측이 없으면 빨강만 보인다."""
    step = max(1, len(rows) // n)
    picks = [rows[i] for i in range(0, len(rows), step)][:n]
    cell_w, cell_h = 420, 520
    tiles = []
    for r in picks:
        img = cv2.imread(str(root / split / r["file_name"]))
        g = [int(v) for v in r["gt"]]
        cv2.rectangle(img, (g[0], g[1]), (g[2], g[3]), (0, 0, 230), 2)
        if r["pred"]:
            p = [int(v) for v in r["pred"]]
            cv2.rectangle(img, (p[0], p[1]), (p[2], p[3]), (0, 230, 0), 2)
        cv2.putText(img, f"IoU {r['iou']:.2f}", (6, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 230, 0), 2)
        s = min(cell_w / img.shape[1], cell_h / img.shape[0])
        img = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)))
        pad = np.zeros((cell_h, cell_w, 3), np.uint8)
        pad[:img.shape[0], :img.shape[1]] = img
        tiles.append(pad)
    grid = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    w = max(g.shape[1] for g in grid)
    grid = [np.pad(g, ((0, 0), (0, w - g.shape[1]), (0, 0))) for g in grid]
    out_png.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_png), np.vstack(grid))
    print(f"눈 확인판 {len(picks)}장 -> {out_png}")


if __name__ == "__main__":
    raise SystemExit(main())
