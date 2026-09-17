"""CRNN + CTC 리더 — 옛 리더(ctc_reader_v2.py, TF)는 2026-09-11 재구축에서 폐기됐다.

이 카드는 **구현만** 한다. 본 학습은 다음 카드다.

torch 로 쓴다(옛 리더는 TF 2.10). 이유 셋: ①검출기가 torch 라 한 환경에서
끝단까지 돈다 ②온디바이스 경로가 ONNX 로 정해졌고(docs/DONE.md G28 — tflite
불가) torch→ONNX 가 짧다 ③이 환경의 TF 2.10 은 numpy 1.23 에 묶여 있어
(antipatterns/unpinned-pip-in-frozen-training-env) 더 얹지 않는 편이 낫다.

**크롭을 펴지 않는다.** 기울어진 숫자를 그대로 읽게 학습한다 — 쿼드 펴기는
이 마일스톤에서 폐기됐고, 검출기가 내놓는 것은 축정렬 상자뿐이다.

실행:
    python reader_crnn.py overfit              구현 확인(50장 과적합)
    python reader_crnn.py train --set synth_coco/B --epochs 30
    python reader_crnn.py eval  --set synth_coco/C --ckpt reader_crnn/best.pt
"""
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent

# ─── 상수 한 곳 (AC#2) ────────────────────────────────────────────────────
# charset 은 0~9 뿐이다. HI/LO·소수점은 이 마일스톤 밖이고, 합성 코퍼스에
# 소수점 표본이 0건이다(audit_dot_unit_coverage.py, 2026-09-10).
CHARSET = "0123456789"
BLANK = len(CHARSET)             # 10. 맨 뒤에 둔다 — 그러면 0~9 의 인덱스가
NUM_CLASSES = len(CHARSET) + 1   # 곧 숫자 값이라 argmax 를 그대로 읽을 수 있다.
MAX_LABEL = 3                    # 합성 라벨은 2자리 210 · 3자리 790 (세트 B n=1000)

# 입력 크기. 종횡비 1.5 는 밴드 상자의 실측 중앙값이다. 재는 명령:
#   python reader_crnn.py measure --set synth_coco/A
#   python reader_crnn.py measure --set synth_coco/B --boxes _diag/synthband_v0/B.jsonl
# 세트 A 정답 상자 n=1000: p5 1.314 · p50 1.498 · p95 1.771
# 세트 B 예측 상자 n=999:  p5 1.348 · p50 1.496 · p95 1.710
# 높이 96 은 밴드 높이 중앙값 355px 을 0.27 배로 줄인다. 7-세그 획이 원본에서
# 30~60px 이므로 8~16px 로 남아 획이 뭉개지지 않는다.
IN_H, IN_W = 96, 144
# 시간축은 폭을 4로 줄여 36. CTC 는 길이 3 라벨에 최소 2*3+1=7 스텝이 필요하니
# 넉넉하다. 너무 늘리면 blank 만 배우고 너무 줄이면 붙은 자리를 못 가른다.
TIME_STEPS = IN_W // 4

SEED = 20260916


def encode(label):
    return [CHARSET.index(c) for c in label]


def decode_greedy(logits):
    """CTC greedy — 연속 중복을 접고 blank 를 지운다."""
    best = logits.argmax(-1)
    out = []
    for seq in best:
        prev, s = -1, []
        for k in seq.tolist():
            if k != prev and k != BLANK:
                s.append(CHARSET[k])
            prev = k
        out.append("".join(s))
    return out


# ─── 데이터 ───────────────────────────────────────────────────────────────
class BandCrops(torch.utils.data.Dataset):
    """COCO 세트의 상자로 크롭해 (1,IN_H,IN_W) 회색조와 라벨을 낸다.

    상자 출처가 둘이다:
      - boxes=None        매니페스트의 정답 상자
      - boxes=<jsonl>     infer_synthband.py 가 낸 예측 상자
    다음 카드가 예측 상자로 학습하므로 여기서 갈래를 미리 열어 둔다.
    크롭은 **펴지 않고** IN_W×IN_H 로 늘린다 — 상자 종횡비가 1.31~1.84 로
    흩어져 있어 늘리는 것 자체가 리더가 견뎌야 할 변형이다.
    """

    def __init__(self, set_dir, split="train2017", boxes=None, limit=None,
                 jitter=0.0):
        self.root = Path(set_dir)
        self.split = split
        coco = json.loads((self.root / "annotations" /
                           f"instances_{split}.json").read_text(encoding="utf-8"))
        labels = {}
        for line in (self.root / "manifest.jsonl").read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                m = json.loads(line)
                labels[f"{m['id']}.png"] = m["label"]

        if boxes:
            src = {}
            for line in Path(boxes).read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    if r["pred"]:
                        src[r["file_name"]] = r["pred"]
            self.skipped = sum(1 for im in coco["images"]
                               if im["file_name"] not in src)
        else:
            src = {}
            gt = {a["image_id"]: a["bbox"] for a in coco["annotations"]}
            for im in coco["images"]:
                b = gt[im["id"]]
                src[im["file_name"]] = [b[0], b[1], b[0] + b[2], b[1] + b[3]]
            self.skipped = 0

        self.items = [(f, src[f], labels[f]) for f in
                      (im["file_name"] for im in coco["images"]) if f in src]
        if limit:
            rng = random.Random(SEED)
            self.items = rng.sample(self.items, min(limit, len(self.items)))
        self.jitter = jitter

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        fname, box, label = self.items[i]
        img = cv2.imread(str(self.root / self.split / fname), cv2.IMREAD_GRAYSCALE)
        x0, y0, x1, y1 = box
        if self.jitter:
            w, h = x1 - x0, y1 - y0
            r = np.random.uniform(-self.jitter, self.jitter, 4)
            x0 += r[0] * w; x1 += r[1] * w; y0 += r[2] * h; y1 += r[3] * h
        x0 = max(0, int(x0)); y0 = max(0, int(y0))
        x1 = min(img.shape[1], int(round(x1))); y1 = min(img.shape[0], int(round(y1)))
        if x1 - x0 < 4 or y1 - y0 < 4:          # 지터가 상자를 뭉갠 경우
            x0, y0, x1, y1 = [int(v) for v in box]
        crop = cv2.resize(img[y0:y1, x0:x1], (IN_W, IN_H))
        t = torch.from_numpy(crop).float().div_(255.).sub_(0.5).unsqueeze(0)
        return t, torch.tensor(encode(label)), len(label), label


def collate(batch):
    xs = torch.stack([b[0] for b in batch])
    ys = torch.cat([b[1] for b in batch])
    lens = torch.tensor([b[2] for b in batch])
    return xs, ys, lens, [b[3] for b in batch]


# ─── 모델 ─────────────────────────────────────────────────────────────────
class CRNN(nn.Module):
    """작은 CRNN. 높이는 전부 접고 폭만 4로 줄여 시간축으로 남긴다."""

    def __init__(self, num_classes=NUM_CLASSES):
        super().__init__()

        def blk(i, o, pool):
            return nn.Sequential(nn.Conv2d(i, o, 3, 1, 1), nn.BatchNorm2d(o),
                                 nn.ReLU(inplace=True), nn.MaxPool2d(pool))

        self.cnn = nn.Sequential(
            blk(1, 32, (2, 2)),      # 48 x 72
            blk(32, 64, (2, 2)),     # 24 x 36
            blk(64, 128, (2, 1)),    # 12 x 36
            blk(128, 128, (2, 1)),   #  6 x 36
            blk(128, 256, (2, 1)),   #  3 x 36
        )
        self.proj = nn.Linear(256 * 3, 256)
        self.rnn = nn.LSTM(256, 192, num_layers=2, bidirectional=True,
                           batch_first=True, dropout=0.1)
        self.head = nn.Linear(192 * 2, num_classes)

    def forward(self, x):
        f = self.cnn(x)                        # B,256,3,36
        b, c, h, w = f.shape
        f = f.permute(0, 3, 1, 2).reshape(b, w, c * h)
        f = torch.relu(self.proj(f))
        f, _ = self.rnn(f)
        return self.head(f)                    # B,T,NUM_CLASSES


# ─── 학습 / 평가 ──────────────────────────────────────────────────────────
def run_epoch(model, loader, crit, opt, dev):
    model.train()
    tot = n = 0
    for xs, ys, lens, _ in loader:
        xs = xs.to(dev)
        logits = model(xs)
        lp = logits.log_softmax(-1).permute(1, 0, 2)       # T,B,C
        inl = torch.full((xs.size(0),), logits.size(1), dtype=torch.long)
        loss = crit(lp, ys, inl, lens)
        opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        opt.step()
        tot += loss.item() * xs.size(0); n += xs.size(0)
    return tot / n


@torch.no_grad()
def evaluate(model, loader, dev, dump=None):
    model.eval()
    ok = n = 0
    wrong = []
    for xs, _, _, labels in loader:
        pred = decode_greedy(model(xs.to(dev)).cpu())
        for p, g in zip(pred, labels):
            ok += int(p == g); n += 1
            if p != g and len(wrong) < 20:
                wrong.append((g, p))
    if dump and wrong:
        print(f"  오독 예시(최대 20): {wrong}")
    return ok / n, n


def loaders(ds, bs, shuffle=True):
    return torch.utils.data.DataLoader(ds, batch_size=bs, shuffle=shuffle,
                                       collate_fn=collate, num_workers=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["overfit", "train", "eval", "measure"])
    ap.add_argument("--set", default=str(HERE / "synth_coco" / "B"))
    ap.add_argument("--split", default="train2017")
    ap.add_argument("--boxes", default=None, help="예측 상자 jsonl(없으면 정답 상자)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--jitter", type=float, default=0.0)
    ap.add_argument("--out", default=str(HERE / "reader_crnn"))
    ap.add_argument("--ckpt", default=None)
    args = ap.parse_args()

    if args.cmd == "measure":
        # IN_H/IN_W 의 종횡비 근거를 내는 자. 상수를 바꾸려면 이걸 먼저 돌린다.
        ds = BandCrops(args.set, args.split, args.boxes)
        ar = np.array([(b[2] - b[0]) / (b[3] - b[1]) for _, b, _ in ds.items])
        lens = np.array([len(l) for _, _, l in ds.items])
        print(f"모집단 {args.set}/{args.split} · 상자 {args.boxes or '정답'} "
              f"· n={len(ar)} (건너뜀 {ds.skipped})")
        print("  종횡비 " + " ".join(f"p{q}={np.percentile(ar, q):.3f}"
                                   for q in (5, 25, 50, 75, 95)))
        print(f"  라벨 길이 " + " ".join(
            f"{k}자리={int((lens == k).sum())}" for k in sorted(set(lens.tolist()))))
        print(f"  현재 상수: IN_H={IN_H} IN_W={IN_W} (종횡비 {IN_W/IN_H:.3f}) "
              f"· TIME_STEPS={TIME_STEPS} · MAX_LABEL={MAX_LABEL}")
        return 0

    torch.manual_seed(SEED); np.random.seed(SEED); random.seed(SEED)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    model = CRNN().to(dev)
    crit = nn.CTCLoss(blank=BLANK, zero_infinity=True)

    if args.cmd == "overfit":
        # 구현이 학습되는지만 본다. 성적이 아니다(AC#1).
        ds = BandCrops(args.set, args.split, args.boxes, limit=50)
        ld = loaders(ds, 16)
        opt = torch.optim.Adam(model.parameters(), lr=2e-3)
        print(f"과적합 확인: {len(ds)}장 (모집단 {args.set}/{args.split})")
        for ep in range(1, 801):
            loss = run_epoch(model, ld, crit, opt, dev)
            if ep % 20 == 0 or ep == 1:
                acc, n = evaluate(model, loaders(ds, 32, False), dev)
                print(f"  ep{ep:3d} loss {loss:.4f}  완전일치 {acc*100:.1f}% (n={n})")
                if acc >= 1.0:
                    print(f"과적합 도달: 완전일치 100% / {n}장 · {ep} 에폭")
                    torch.save({"model": model.state_dict()}, out / "overfit50.pt")
                    return 0
        print("과적합 실패 — 구현을 의심할 것")
        return 1

    if args.cmd == "eval":
        model.load_state_dict(torch.load(args.ckpt, map_location=dev)["model"])
        ds = BandCrops(args.set, args.split, args.boxes)
        acc, n = evaluate(model, loaders(ds, 64, False), dev, dump=True)
        print(f"완전일치 {acc*100:.2f}% (n={n}, 모집단 {args.set}/{args.split}, "
              f"상자 {args.boxes or '정답'}, 건너뜀 {ds.skipped})")
        return 0

    ds = BandCrops(args.set, args.split, args.boxes, jitter=args.jitter)
    print(f"학습 {len(ds)}장 (모집단 {args.set}, 상자 {args.boxes or '정답'}, "
          f"건너뜀 {ds.skipped})")
    ld = loaders(ds, args.batch)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)
    best = -1.0
    for ep in range(1, args.epochs + 1):
        loss = run_epoch(model, ld, crit, opt, dev)
        sched.step()
        acc, n = evaluate(model, loaders(ds, 64, False), dev)
        print(f"  ep{ep:3d} loss {loss:.4f}  학습셋 완전일치 {acc*100:.2f}% (n={n})")
        if acc > best:
            best = acc
            torch.save({"model": model.state_dict(), "epoch": ep, "acc": acc},
                       out / "best.pt")
    torch.save({"model": model.state_dict(), "epoch": args.epochs},
               out / "last.pt")
    print(f"최고 학습셋 완전일치 {best*100:.2f}% -> {out/'best.pt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
