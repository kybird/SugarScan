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

    구판은 학습 증강을 넣지 않았다 — 변이는 생성기가 만든다는 원칙이었다
    (SPEC §9). 그 원칙의 값은 **무엇이 무엇을 움직였는지 가를 수 있다**는
    것이었다.

    2026-09-19 에 사람이 뒤집었다: "데이터증강을 해야하는거아니냐". 근거가
    있다 — 생성기가 아직 안 그리는 축이 SPEC §9.7.4 에 남아 있다(센서 잡음 ·
    JPEG 압축 흔적 · 조명 불균일). 그리고 배율 민감도는 실촬에서 측정됐다
    (가까움 23.1% / 멂 1.3%, 2026-09-18). 증강은 그 둘을 생성기 재작업 없이
    덮는다.

    **--aug 로만 켠다.** 기본은 끔이라, 켠 조건과 끈 조건을 나란히 재면
    원칙이 지키려던 "무엇이 움직였나"도 그대로 답할 수 있다.
    """

    def __init__(self, root, ann, size=416, repeat=1, grow=0.0, aug=False,
                 scale_min=0.55):
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
        # grow: 정답 상자를 **상자 높이 비율**로 사방 확대한다.
        # 왜(2026-09-19): 실촬에서 원시 예측이 숫자 칸을 24.7% 에서 잘랐다.
        # 자르는 것은 치명적이고(리더가 못 읽는다) 큰 것은 싸다(τ=2.0 까지
        # 허용). 정답을 키워 배우게 하면 그 비대칭이 상자에 반영된다.
        # **이미지를 다시 굽지 않는다** — lcd_layout 이 2026-09-16 에 그림용
        # LAYOUT_MARGIN 과 라벨용 BAND_MARGIN 을 갈라 놨기 때문에, 라벨만
        # 키우는 것은 그림과 무관하다. 여기서 적재 시점에 더하는 것은 그
        # 분리를 데이터 재생성 없이 쓰는 것과 같다.
        self.grow = grow
        # 증강 축소 하한. 기본 0.55 는 **사람이 정한 값**이고 여기서
        # 바꾸지 않는다 — 실험은 플래그로 한다(BAND_EXP_PLAN §19.4).
        # 배경: 합성 밴드는 실촬보다 2.3~4배 크다(§19.3). 0.55 로는
        # 학습이 닿는 구간이 [0.266, 0.605]라 실촬 중앙 0.118 에 못 닿는다.
        self.scale_min = scale_min
        self.aug = aug

    def __len__(self):
        return len(self.items) * self.repeat

    def _photo(self, img, rng):
        """광학 열화 — 생성기가 안 그리는 축(SPEC §9.7.4)을 여기서 덮는다.

        순서가 실제 촬영·저장 경로를 닮아야 해석이 쉽다:
        초점 흐림 -> 밝기/대비 -> 센서 잡음 -> JPEG. 최종 이미지에 필터를
        무차별로 거는 것보다 낫다.
        """
        if rng.random() < 0.35:
            k = 2 * rng.randrange(1, 3) + 1
            img = cv2.GaussianBlur(img, (k, k), 0)
        if rng.random() < 0.6:
            a = rng.uniform(0.7, 1.35)          # 대비
            b = rng.uniform(-35, 35)            # 밝기
            img = np.clip(img.astype(np.float32) * a + b, 0, 255).astype(np.uint8)
        if rng.random() < 0.4:
            n = rng.uniform(2, 10)
            img = np.clip(img.astype(np.float32)
                          + np.random.default_rng(rng.getrandbits(64)).normal(0, n, img.shape), 0,
                          255).astype(np.uint8)
        if rng.random() < 0.5:
            q = rng.randrange(35, 92)
            ok, enc = cv2.imencode(".jpg", img,
                                   [int(cv2.IMWRITE_JPEG_QUALITY), q])
            if ok:
                img = cv2.imdecode(enc, cv2.IMREAD_GRAYSCALE)
        return img

    def __getitem__(self, i):
        path, box = self.items[i % len(self.items)]
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if self.aug:
            # DataLoader seeds each worker's Python RNG. Draw per visit rather
            # than from the image index: epochs must not repeat a fixed transform.
            rng = random.Random(random.getrandbits(64))
            img = self._photo(img, rng)
            photo = img
            # **배율·위치 흔들기.** 실촬에서 촬영 거리가 성적을 강하게 물었다
            # (가까움 23.1% / 멂 1.3%). 생성기의 CAM_ZOOM_RANGE 가 덮지 못한
            # 구간을 여기서 넓힌다. 캔버스를 키우거나 잘라 상자를 같이 옮긴다.
            h0, w0 = img.shape
            sc = rng.uniform(self.scale_min, 1.25)
            nw, nh = max(8, int(w0 * sc)), max(8, int(h0 * sc))
            img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
            sx, sy = nw / w0, nh / h0
            box = [box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy]
            # 캔버스를 다시 원본 크기로 — 남는 자리는 PAD, 넘치면 잘린다.
            cvs = np.full((h0, w0), PAD, np.uint8)
            # Keep the entire target visible. Clipping the label would teach
            # that truncated digits are a complete band; retaining an invisible
            # label would supervise content that the input does not contain.
            xmin = max(min(0, w0-nw), math.ceil(-box[0]))
            xmax = min(max(0, w0-nw), math.floor(w0-box[2]))
            ymin = max(min(0, h0-nh), math.ceil(-box[1]))
            ymax = min(max(0, h0-nh), math.floor(h0-box[3]))
            if xmin > xmax or ymin > ymax:
                # A target wider than the canvas cannot be translated into it.
                # Fall back to the original geometry, retaining photo effects.
                img = photo
                box = list(self.items[i % len(self.items)][1])
                return self._tensor(img, box)
            ox = rng.randint(xmin, xmax)
            oy = rng.randint(ymin, ymax)
            sx0, sy0 = max(0, -ox), max(0, -oy)
            dx0, dy0 = max(0, ox), max(0, oy)
            cw = min(nw - sx0, w0 - dx0)
            ch = min(nh - sy0, h0 - dy0)
            if cw > 0 and ch > 0:
                cvs[dy0:dy0+ch, dx0:dx0+cw] = img[sy0:sy0+ch, sx0:sx0+cw]
                img = cvs
                box = [box[0] + ox, box[1] + oy, box[2] + ox, box[3] + oy]
        return self._tensor(img, box)

    def _tensor(self, img, box):
        img, r, dx, dy = letterbox(img, self.size)
        if self.grow > 0:
            m = (box[3] - box[1]) * self.grow
            box = [box[0] - m, box[1] - m, box[2] + m, box[3] + m]
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


def init_worker(_):
    # Each loader process already runs in parallel. OpenCV's own thread pool
    # per worker oversubscribes the host during blur/resize/JPEG augmentation.
    cv2.setNumThreads(1)


def _save(path, model, args, nparam, n_images, steps):
    """중간/최종 체크포인트를 같은 스키마로 쓴다 — 평가기가 구분 없이 읽는다."""
    torch.save({"model": model.state_dict(), "width": args.width,
                "size": args.size, "steps": steps,
                "n_images": n_images, "param": nparam,
                "score_target": args.score_target, "seed": args.seed,
                "grow": args.grow, "under_w": args.under_w,
                "aug_scale_min": args.aug_scale_min,
                "aug": bool(args.aug), "stride": args.stride}, path)


@torch.no_grad()
def _quick_gate(model, args, dev, n=200):
    """중간 품질검사 — **합성 홀드아웃 일부**만 빠르게.

    실촬을 여기서 재지 않는다. 학습 루프 안에서 실촬을 보면 그것으로 고르게
    되고 홀드아웃이 오염된다. 여기서 보는 것은 "학습이 무너지지 않았나"다.
    """
    from band_net import decode
    root = Path(args.mid_data)
    man = {}
    for line in (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            m = json.loads(line)
            man[m["id"]] = m
    ids = sorted(man)[:n]
    model.eval()
    ok = miss = 0
    for cid in ids:
        m = man[cid]
        if m.get("digit_box") is None:
            continue
        img = cv2.imread(str(root / "train2017" / f"{cid}.png"), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        lb, r, dx, dy = letterbox(img, args.size)
        x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
        o, g = model(x.to(dev))
        b, sc = decode(o.float(), g.float(), model.stride)
        b = b[0].cpu().numpy()
        if float(sc[0].cpu()) < 0.25:
            miss += 1
            continue
        p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
        d = [float(v) for v in m["digit_box"]]
        if p[0] <= d[0] and p[1] <= d[1] and p[2] >= d[2] and p[3] >= d[3]:
            ok += 1
    tot = max(1, len(ids))
    return f"합성게이트 {100*ok/tot:.1f}% (n={tot} 미검출 {miss})"


def run(args):
    cv2.setNumThreads(1)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)
    ds = CocoBand(args.data, args.train_ann, args.size, args.repeat,
                  grow=args.grow, aug=args.aug,
                  scale_min=args.aug_scale_min)
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True,
                    num_workers=args.workers, drop_last=True, pin_memory=True,
                    persistent_workers=args.workers > 0,
                    worker_init_fn=init_worker)
    model = BandNet(width=args.width, stride=args.stride).to(dev)
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
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
        pr = reg.permute(0, 2, 3, 1)[pos]
        tg = tgt.permute(0, 2, 3, 1)[pos]
        lb, iou = giou_loss(pr, tg)
        if args.under_w > 1.0:
            # **자르는 것과 큰 것은 대가가 다르다.** 숫자를 자르면 리더가
            # 못 읽고(치명), 크면 τ 안에서는 무해하다. GIoU 는 둘을 같게
            # 본다. 그래서 각 변이 **정답보다 모자란 만큼**에만 추가
            # 벌점을 준다. 넘치는 쪽에는 주지 않는다 — 그건 τ 가 본다.
            short = (tg - pr).clamp(min=0) / tg.clamp(min=1.0)
            lb = lb + (args.under_w - 1.0) * short.sum(-1)
        # 점수 타깃 — 2026-09-18 실패 분해가 병목으로 지목한 자리다.
        # 실촬에서 정답 양성 영역(9칸 남짓) 안의 **최고점 칸**은 38.6%,
        # **최선 칸**은 73.9% 였다. 붙어 있는 칸들인데 상자 품질이 갈리고
        # 점수가 그걸 따라가지 않는다. bce 는 양성 전부에 1.0 을 주므로
        # 순위에 품질 정보가 아예 없다.
        #
        #   bce         현행. 양성이면 1.0.
        #   iou         그 칸이 **실제로 낸 상자**의 GIoU-IoU 를 타깃으로.
        #               detach 한다 — 안 하면 점수를 낮춰서 손실을 줄이는
        #               퇴화 경로가 생긴다. 초반에는 예측이 나빠 타깃이 0
        #               근처라 양성 신호가 죽으므로 1.0 에서 선형으로 넘긴다.
        #   centerness  기하학적 타깃. 변까지 거리의 균형만 본다(FCOS).
        #               예측에 의존하지 않아 안정적이지만, 그 칸이 실제로
        #               좋은 상자를 냈는지는 모른다.
        #
        # FCOS 는 별도 가지를 뒀지만 우리는 objectness 에 접는다. 디코드가
        # argmax 하나(NMS 없음)라 **점수가 곧 순위**이고, 가지를 늘리면
        # 온디바이스 예산을 쓴다. 추론 경로는 세 조건이 완전히 같다.
        if args.score_target == "bce":
            t_obj = pos.float()
        else:
            if args.score_target == "iou":
                q = iou.detach().clamp(0.0, 1.0)
                if args.score_warm > 0 and step < args.score_warm:
                    a = step / args.score_warm
                    q = (1.0 - a) + a * q
            else:
                l_, t_, r_, b_ = tg.unbind(-1)
                q = torch.sqrt(
                    (torch.min(l_, r_) / torch.max(l_, r_).clamp(min=1e-6))
                    * (torch.min(t_, b_) / torch.max(t_, b_).clamp(min=1e-6))
                ).clamp(0.0, 1.0)
            t_obj = torch.zeros_like(pos, dtype=torch.float32)
            t_obj[pos] = q
        lo = F.binary_cross_entropy_with_logits(obj[:, 0], t_obj,
                                                reduction="none")
        # 양성이 희박하므로 양성 쪽에 가중치를 준다. focal 대신 단순 가중치를
        # 쓰는 이유: 배경이 '어려운 음성'을 거의 안 만든다(단색 판이 많다).
        w = torch.where(pos, float(args.pos_w), 1.0)
        lo = (lo * w).mean()
        lb = lb.mean()
        loss = lo + args.box_w * lb
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
        scaler.step(opt)
        scaler.update()
        step += 1
        # **중간 저장 + 중간 품질검사** (2026-09-20 사람 요청: "훈련은 에포크
        # 단위로 짤라서 중간중간 품질검사할수있게해줘"). 스텝 기준 학습이라
        # 에포크가 없으므로 --save-every 스텝을 한 구간으로 본다.
        #
        # 저장은 **덮어쓰지 않는다** — <out>_step<N>.pt 로 따로 남긴다. 그래야
        # 나중에 "언제부터 나빠졌나"를 되짚을 수 있다.
        # 중간 평가는 합성 홀드아웃 일부만 본다(빠르게). 실촬은 여기서 안 잰다 —
        # 학습 루프 안에서 실촬을 보면 그걸로 고르게 되고 홀드아웃이 오염된다.
        if args.save_every and (step % args.save_every == 0) and step < total:
            _p = out_path.with_name(f"{out_path.stem}_step{step}{out_path.suffix}")
            _save(_p, model, args, nparam, len(ds.items), step)
            msg = f"  [중간] step {step} -> {_p.name}"
            if args.mid_eval:
                msg += "  " + _quick_gate(model, args, dev)
            print(msg, flush=True)
            model.train()
        if step % args.log == 0 or step == total:
            print(f"  step {step}/{total} loss {loss.item():.4f} "
                  f"(obj {lo.item():.4f} box {lb.item():.4f}) "
                  f"iou {iou.mean().item():.3f} lr {lr_at(step):.2e} "
                  f"{time.time()-t0:.0f}s", flush=True)
    out = out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    _save(out, model, args, nparam, len(ds.items), total)
    print(f"-> {out}  ({time.time()-t0:.0f}s)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--train-ann", default="instances_train2017.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=416)
    ap.add_argument("--stride", type=int, default=16, choices=(8, 16),
                    help="검출 특징맵 stride. /8 허용은 2026-09-21 사람 결정"
                         "(SPEC §5.3). 기본 16 은 기존 팔과 같다")
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
    ap.add_argument("--score-target", default="bce",
                    choices=("bce", "iou", "centerness"),
                    help="objectness 타깃. 순위에 상자 품질을 넣을지")
    ap.add_argument("--save-every", type=int, default=0,
                    help="이 스텝마다 중간 체크포인트를 따로 남긴다")
    ap.add_argument("--mid-eval", action="store_true",
                    help="중간 저장 때 합성 홀드아웃 일부로 품질검사")
    ap.add_argument("--mid-data", default=str(HERE / "synth_coco" / "VB"),
                    help="중간 품질검사용 홀드아웃")
    ap.add_argument("--aug", action="store_true",
                    help="학습 증강 — 광학 열화 + 배율·위치 흔들기")
    ap.add_argument("--aug-scale-min", type=float, default=0.55,
                    help="증강 축소 하한. 기본값은 사람이 정한 값이다")
    ap.add_argument("--grow", type=float, default=0.0,
                    help="정답 상자를 상자 높이의 이 비율만큼 사방 확대")
    ap.add_argument("--under-w", type=float, default=1.0,
                    help=">1 이면 정답보다 모자란 변에 추가 벌점")
    ap.add_argument("--score-warm", type=int, default=1000,
                    help="score-target=iou 일 때 1.0 에서 넘기는 스텝 수")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
