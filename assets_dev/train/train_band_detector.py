# 밴드 쿼드 검출기 v0 학습 — 「합성만으로 밴드 쿼드 검출기 v0」 카드 (2026-09-12).
#
# 합성 패널(synth_panel.py 산출: images/*.png + manifest.jsonl 의 quad)만으로
# 소형 CNN 을 학습해 GM 크롭에서 밴드 쿼드를 회귀한다. 사람 라벨은 한 장도
# 쓰지 않는다 — 학습도, 검증도(카드 AC#7 게이트는 별도 스크립트) 아니다.
#
# 입력 규약(카드 AC#5·#6): GM 크롭(LCD 화면)을 자기 종횡비 그대로 256x256
# 정사각 캔버스에 레터박스(114 회색)로 넣는다. 세로형은 좌우, 가로형은 위아래에
# 패딩이 남는다. 좌표는 레터박스 캔버스 기준 0~1 정규화, 순서 TL-TR-BR-BL 고정.
#
# 학습 건전성만 여기서 본다 — 합성 val 점수는 품질 계기가 아니다(카드 지시:
# 쓰레기를 일관되게 그려도 100%가 나온다). 실사진 게이트는 eval_band_detector.py.
#
# 사용:
#   conda run -n sugartrain python train_band_detector.py \
#       --data synth_band_det --epochs 40 --out band_det_v0.pt
import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

IMG_SIZE = 256
PAD_GRAY = 114.0


def letterbox(gray, size=IMG_SIZE):
    """종횡비 보존 레터박스. 반환 (이미지 float32 0~1, scale, pad_x, pad_y)."""
    H, W = gray.shape
    scale = size / max(W, H)
    nw, nh = max(1, int(round(W * scale))), max(1, int(round(H * scale)))
    rs = cv2.resize(gray, (nw, nh), interpolation=cv2.INTER_AREA)
    px = (size - nw) // 2
    py = (size - nh) // 2
    canvas = np.full((size, size), PAD_GRAY, np.float32)
    canvas[py:py + nh, px:px + nw] = rs
    return canvas / 255.0, scale, float(px), float(py)


def quad_to_target(quad, scale, px, py, size=IMG_SIZE):
    q = np.asarray(quad, np.float64) * scale + np.array([px, py])
    return (q / size).astype(np.float32).reshape(-1)


class BandQuadNet(nn.Module):
    """소형 CNN — 256x256 회색 입력에서 쿼드 8좌표를 직접 회귀한다.
    v0 목표는 '제안'이다: 기울기·원근를 담는 좌표 8개면 충분하다(AC#2)."""

    def __init__(self):
        super().__init__()

        def blk(ci, co):
            return nn.Sequential(
                nn.Conv2d(ci, co, 3, stride=2, padding=1),
                nn.BatchNorm2d(co), nn.ReLU(inplace=True),
                nn.Conv2d(co, co, 3, padding=1),
                nn.BatchNorm2d(co), nn.ReLU(inplace=True),
            )
        self.features = nn.Sequential(
            blk(1, 24),    # 128
            blk(24, 48),   # 64
            blk(48, 96),   # 32
            blk(96, 128),  # 16
            blk(128, 128), # 8
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 8 * 8, 512), nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(512, 8),
        )

    def forward(self, x):
        return self.head(self.features(x))


class BandQuadHeat(nn.Module):
    """모서리 네 개를 히트맵으로 내고 soft-argmax 로 좌표를 뽑는다.

    구판(BandQuadNet)은 8x8x128 을 Flatten 해 Linear(8192,512) 로 받았다 —
    파라미터 491만 중 419만(85%)이 그 한 줄이었고, 납작하게 펴는 순간 '어느
    칸에서 온 값인가'가 구조에서 사라져 FC 가 위치를 weight 로 외워야 했다.
    기울기(밴드 양 끝의 미세한 y 차이)가 40k 가 되어서야 배워진 것이 그
    비용으로 보인다(band_det_corner_error.py, corr 0.057 -> 0.616 -> 0.910).

    바꾸는 축은 머리부 하나뿐이다. 특징부는 구판과 같은 블록을 쓰되 마지막
    stride 를 빼 격자를 8x8 -> 16x16 으로 올렸다. soft-argmax 는 칸 안의
    소수점 위치까지 연속으로 내므로 격자 해상도가 상한이 아니다.

    출력 규약은 구판과 동일 — 레터박스 캔버스 0~1 정규화, TL-TR-BR-BL.
    """

    def __init__(self, temp=1.0):
        super().__init__()

        def blk(ci, co, stride=2):
            return nn.Sequential(
                nn.Conv2d(ci, co, 3, stride=stride, padding=1),
                nn.BatchNorm2d(co), nn.ReLU(inplace=True),
                nn.Conv2d(co, co, 3, padding=1),
                nn.BatchNorm2d(co), nn.ReLU(inplace=True),
            )
        self.features = nn.Sequential(
            blk(1, 24),      # 128
            blk(24, 48),     # 64
            blk(48, 96),     # 32
            blk(96, 128),    # 16
        )
        self.head = nn.Sequential(
            nn.Conv2d(128, 128, 3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True),
            nn.Conv2d(128, 4, 1),          # 모서리 4개의 히트맵
        )
        self.temp = temp

    def forward(self, x):
        h = self.head(self.features(x))            # [N,4,G,G]
        n, c, gh, gw = h.shape
        p = torch.softmax(h.reshape(n, c, gh * gw) / self.temp, dim=-1)
        p = p.reshape(n, c, gh, gw)
        # 격자 중심을 0~1 로 — 칸 크기의 절반만큼 안으로 들어온다
        ys = (torch.arange(gh, device=h.device, dtype=h.dtype) + 0.5) / gh
        xs = (torch.arange(gw, device=h.device, dtype=h.dtype) + 0.5) / gw
        ex = (p.sum(dim=2) * xs).sum(dim=-1)       # [N,4]
        ey = (p.sum(dim=3) * ys).sum(dim=-1)
        return torch.stack([ex, ey], dim=-1).reshape(n, 8)


ARCHS = {"fc": BandQuadNet, "heat": BandQuadHeat}


def load_detector(ckpt, dev="cpu"):
    """체크포인트에서 구조를 알아내 모델을 세운다.

    구판 체크포인트 아홉 개는 arch 를 안 적고 저장됐다. state_dict 의 머리부
    모양으로 가른다 — fc 는 head.1.weight 가 (512, 8192), heat 는 머리부가
    전부 Conv 다. 파일에 이름을 적는 방식은 옛 파일에 소급이 안 된다.
    """
    sd = torch.load(ckpt, map_location=dev)
    arch = "fc" if sd.get("head.1.weight", torch.empty(0)).dim() == 2 else "heat"
    model = ARCHS[arch]().to(dev)
    model.load_state_dict(sd)
    model.eval()
    return model, arch


class SynthBandSet(Dataset):
    def __init__(self, root, ids, train):
        self.root = Path(root)
        self.rows = ids
        self.train = train

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        img = cv2.imread(str(self.root / "images" / f"{r['id']}.png"),
                         cv2.IMREAD_GRAYSCALE)
        x, sc, px, py = letterbox(img)
        y = quad_to_target(r["quad"], sc, px, py)
        if self.train and random.random() < 0.5:
            x = np.ascontiguousarray(x[:, ::-1])
            xs = y.reshape(4, 2)[:, 0].copy()
            y = y.reshape(4, 2)
            y[:, 0] = 1.0 - xs           # 좌우 반전 — TL<->TR, BL<->BR
            y = y[[1, 0, 3, 2]].reshape(-1)
        if self.train:
            x = np.clip(x * random.uniform(0.85, 1.15)
                        + random.uniform(-0.08, 0.08), 0, 1)
        return torch.from_numpy(np.ascontiguousarray(x))[None], \
            torch.from_numpy(y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="synth_band_det")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--val", type=int, default=150, help="학습 건전성용 분리")
    ap.add_argument("--out", default="band_det_v0.pt")
    ap.add_argument("--arch", default="fc", choices=sorted(ARCHS),
                    help="fc=구판(Flatten+Linear) · heat=히트맵+soft-argmax. "
                         "구판 체크포인트 아홉 개가 fc 라 기본을 바꾸지 않는다")
    args = ap.parse_args()

    rows = [json.loads(l) for l in
            (Path(args.data) / "manifest.jsonl").read_text(
                encoding="utf-8").splitlines() if l.strip()]
    random.Random(0).shuffle(rows)
    val_rows, train_rows = rows[:args.val], rows[args.val:]
    print(f"train {len(train_rows)} / sanity-val {len(val_rows)}")
    tr = DataLoader(SynthBandSet(args.data, train_rows, True),
                    batch_size=args.batch, shuffle=True, num_workers=4,
                    drop_last=True)
    va = DataLoader(SynthBandSet(args.data, val_rows, False),
                    batch_size=args.batch, num_workers=2)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = ARCHS[args.arch]().to(dev)
    print(f"arch={args.arch}  파라미터 "
          f"{sum(p.numel() for p in model.parameters()):,}")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)
    lossf = nn.SmoothL1Loss()
    for ep in range(args.epochs):
        model.train()
        tot = n = 0
        for xb, yb in tr:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad()
            loss = lossf(model(xb), yb)
            loss.backward()
            opt.step()
            tot += float(loss) * len(xb)
            n += len(xb)
        sched.step()
        model.eval()
        vt = vn = 0
        with torch.no_grad():
            for xb, yb in va:
                xb, yb = xb.to(dev), yb.to(dev)
                vt += float(lossf(model(xb), yb)) * len(xb)
                vn += len(xb)
        print(f"epoch {ep + 1:3d}  train {tot / max(1, n):.5f}  "
              f"sanity-val {vt / max(1, vn):.5f}", flush=True)
    torch.save(model.state_dict(), args.out)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
