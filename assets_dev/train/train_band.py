# 밴드 검출망 학습 — 스크래치. 외부 데이터도 외부 가중치도 쓰지 않는다(SPEC §5.3).
#
# 코퍼스 크기 스윕이 목적이다: 모델을 하나로 고정하고 **방향별 장수만** 바꿔
# 일반화가 어디서 포화하는지 본다. 접은 규모 곡선 카드의 교훈을 그대로 쓴다.
#   - **스텝을 고정한다.** 에포크를 고정하면 작은 세트가 적은 스텝을 받아
#     "장수 부족"과 "스텝 부족"이 뒤섞인다.
#   - **중첩 부분집합**으로 자른다. 세트마다 시드를 달리하면 인접 점의 차이에
#     시드 잡음이 섞인다.
#   - 게이트는 IoU 가 아니다(SPEC 7-3). 숫자 필드 포함률을 본다 — eval_band.py.
#
# 검증 세트는 **굽는 시드가 다른** 별도 코퍼스다(SPEC 9.4).
import argparse
import json
import math
import random
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from band_net import BandNet

HERE = Path(__file__).resolve().parent
PAD = 114          # 레터박스 채움값. 평가 경로와 같아야 한다


def letterbox(img, size):
    """긴 변을 size 에 맞추고 나머지를 PAD 로 채운다. (img, r, dx, dy) 반환."""
    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    out = np.full((size, size), PAD, np.uint8)
    dy, dx = (size - nh) // 2, (size - nw) // 2
    out[dy:dy + nh, dx:dx + nw] = cv2.resize(img, (nw, nh),
                                             interpolation=cv2.INTER_LINEAR)
    return out, r, dx, dy


class CocoBand(Dataset):
    """COCO 주석 한 벌 + 그레이스케일 이미지. 정답은 box 하나(SPEC 9.5).

    학습 증강을 넣지 않는다 — 변이는 **생성기가** 만든다(SPEC 9). 여기서 또
    흔들면 생성기가 선언한 분포가 아닌 것을 학습하게 되고, 무엇이 무엇을
    움직였는지 못 가른다.
    """

    def __init__(self, root, ann, size=416, repeat=1):
        root = Path(root)
        j = json.loads((root / "annotations" / ann).read_text(encoding="utf-8"))
        by = {a["image_id"]: a["bbox"] for a in j["annotations"]}
        split = "val2017" if "val" in ann else "train2017"
        self.items = []
        for im in j["images"]:
            b = by.get(im["id"])
            if b is None:
                continue
            self.items.append((str(root / split / im["file_name"]),
                               [b[0], b[1], b[0] + b[2], b[1] + b[3]]))
        self.size = size
        self.repeat = repeat

    def __len__(self):
        return len(self.items) * self.repeat

    def __getitem__(self, i):
        path, box = self.items[i % len(self.items)]
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        img, r, dx, dy = letterbox(img, self.size)
        b = np.array([box[0] * r + dx, box[1] * r + dy,
                      box[2] * r + dx, box[3] * r + dy], np.float32)
        x = torch.from_numpy(img).float().div_(255.).unsqueeze(0)
        return x, torch.from_numpy(b)


def assign(boxes, H, W, stride, radius=1.5):
    """GT 중심 근처 칸을 양성으로. 물체가 하나뿐이라 동적 배정이 필요 없다.

    radius 는 **칸 단위**다. 1.5 면 중심 칸과 그 둘레(대략 3x3)가 양성이 된다.
    양성이 하나뿐이면 학습 신호가 너무 희박하고, 너무 넓으면 변 거리 회귀가
    멀리서부터 큰 값을 배워야 해서 불안정하다.
    """
    B = boxes.shape[0]
    dev = boxes.device
    ys = (torch.arange(H, device=dev).float() + 0.5) * stride
    xs = (torch.arange(W, device=dev).float() + 0.5) * stride
    cy, cx = torch.meshgrid(ys, xs, indexing="ij")
    cx = cx[None].expand(B, H, W)
    cy = cy[None].expand(B, H, W)
    gx = ((boxes[:, 0] + boxes[:, 2]) / 2)[:, None, None]
    gy = ((boxes[:, 1] + boxes[:, 3]) / 2)[:, None, None]
    near = ((cx - gx).abs() <= radius * stride) & ((cy - gy).abs() <= radius * stride)
    inside = ((cx > boxes[:, 0][:, None, None]) & (cx < boxes[:, 2][:, None, None]) &
              (cy > boxes[:, 1][:, None, None]) & (cy < boxes[:, 3][:, None, None]))
    pos = near & inside
    # 상자가 아주 작아 한 칸도 안 들면 가장 가까운 칸 하나를 양성으로 둔다.
    empty = ~pos.view(B, -1).any(1)
    if bool(empty.any()):
        d = (cx - gx) ** 2 + (cy - gy) ** 2
        k = d.view(B, -1).argmin(1)
        flat = pos.view(B, -1).clone()
        flat[empty, k[empty]] = True
        pos = flat.view(B, H, W)
    tgt = torch.stack([cx - boxes[:, 0][:, None, None],
                       cy - boxes[:, 1][:, None, None],
                       boxes[:, 2][:, None, None] - cx,
                       boxes[:, 3][:, None, None] - cy], 1)
    return pos, tgt


def giou_loss(pred, tgt):
    """l,t,r,b 거리쌍의 GIoU. 좌표가 아니라 거리라 그대로 넓이를 만든다."""
    pl, pt, pr, pb = pred.unbind(-1)
    tl, tt, tr, tb = tgt.unbind(-1)
    pa = (pl + pr) * (pt + pb)
    ta = (tl + tr) * (tt + tb)
    iw = (torch.min(pl, tl) + torch.min(pr, tr)).clamp(min=0)
    ih = (torch.min(pt, tt) + torch.min(pb, tb)).clamp(min=0)
    inter = iw * ih
    union = pa + ta - inter
    cw = torch.max(pl, tl) + torch.max(pr, tr)
    ch = torch.max(pt, tt) + torch.max(pb, tb)
    ca = cw * ch
    iou = inter / union.clamp(min=1e-7)
    giou = iou - (ca - union) / ca.clamp(min=1e-7)
    return (1 - giou), iou


def run(args):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)
    ds = CocoBand(args.data, args.train_ann, args.size, args.repeat)
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True,
                    num_workers=args.workers, drop_last=True, pin_memory=True,
                    persistent_workers=args.workers > 0)
    model = BandNet(width=args.width).to(dev)
    nparam = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=5e-4)
    scaler = torch.amp.GradScaler(dev, enabled=(dev == "cuda"))
    total = args.steps
    warm = max(100, total // 50)

    def lr_at(s):
        if s < warm:
            return args.lr * s / warm
        p = (s - warm) / max(1, total - warm)
        return args.lr * (0.01 + 0.99 * 0.5 * (1 + math.cos(math.pi * p)))

    print(f"장수 {len(ds.items)} (반복 {args.repeat} -> 에포크 {len(ds)}) "
          f"batch {args.batch} steps {total} width {args.width} "
          f"param {nparam/1e6:.3f}M size {args.size}", flush=True)
    step = 0
    t0 = time.time()
    it = iter(dl)
    model.train()
    while step < total:
        try:
            x, b = next(it)
        except StopIteration:
            it = iter(dl)
            x, b = next(it)
        x = x.to(dev, non_blocking=True)
        b = b.to(dev, non_blocking=True)
        for g in opt.param_groups:
            g["lr"] = lr_at(step)
        with torch.amp.autocast(dev, enabled=(dev == "cuda")):
            obj, reg = model(x)
        obj = obj.float()
        reg = reg.float()
        H, W = obj.shape[-2:]
        pos, tgt = assign(b, H, W, model.stride, args.radius)
        lo = F.binary_cross_entropy_with_logits(obj[:, 0], pos.float(),
                                                reduction="none")
        # 양성이 희박하므로 양성 쪽에 가중치를 준다. focal 대신 단순 가중치를
        # 쓰는 이유: 배경이 '어려운 음성'을 거의 안 만든다(단색 판이 많다).
        w = torch.where(pos, float(args.pos_w), 1.0)
        lo = (lo * w).mean()
        pr = reg.permute(0, 2, 3, 1)[pos]
        tg = tgt.permute(0, 2, 3, 1)[pos]
        lb, iou = giou_loss(pr, tg)
        lb = lb.mean()
        loss = lo + args.box_w * lb
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
        scaler.step(opt)
        scaler.update()
        step += 1
        if step % args.log == 0 or step == total:
            print(f"  step {step}/{total} loss {loss.item():.4f} "
                  f"(obj {lo.item():.4f} box {lb.item():.4f}) "
                  f"iou {iou.mean().item():.3f} lr {lr_at(step):.2e} "
                  f"{time.time()-t0:.0f}s", flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "width": args.width,
                "size": args.size, "steps": total,
                "n_images": len(ds.items), "param": nparam}, out)
    print(f"-> {out}  ({time.time()-t0:.0f}s)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--train-ann", default="instances_train2017.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=416)
    ap.add_argument("--width", type=float, default=1.0)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--steps", type=int, default=6000)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--radius", type=float, default=1.5)
    ap.add_argument("--pos-w", type=float, default=50.0)
    ap.add_argument("--box-w", type=float, default=2.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--log", type=int, default=250)
    ap.add_argument("--seed", type=int, default=20260930)
    run(ap.parse_args())


if __name__ == "__main__":
    main()
