# 리더 per-image 예측 덤프 — 웹툴 프레이밍 열람(/synth)의 데이터원 (2026-09-22).
#
# reader_crnn eval 의 dump 는 콘솔 예시 20건뿐이라 per-image 파일을 낸다.
# 2팔(GT 상자 학습·atone 예측 상자 학습) × 평가 상자 2원(GT·atone 예측)의
# 4조합을 돌려 _diag/reader_dump/<세트>_<팔>_<상자원>.jsonl 을 쓴다.
# 행: {file_name, label, pred, ok}
#
# 사용: python reader_dump.py --set synth_coco/VE
import argparse
import json
from pathlib import Path

import torch

from reader_crnn import BandCrops, CRNN, loaders, decode_greedy

HERE = Path(__file__).resolve().parent
ARMS = {
    "A": HERE / "reader_crnn_tc_gt" / "best.pt",      # 정답 상자로 학습
    "B": HERE / "reader_crnn_tc_pred" / "best.pt",    # atone 예측 상자로 학습
}
BOXES = {
    "gt": None,
    "pred": str(HERE / "_diag" / "reader_boxes" / "ve_atone_s0.jsonl"),
}


def run(ckpt, set_dir, split, boxes, out_path):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = CRNN().to(dev).eval()
    model.load_state_dict(torch.load(ckpt, map_location=dev)["model"])
    ds = BandCrops(set_dir, split, boxes)
    # loader 는 items 순서를 유지하므로(shuffle=False) 묶음 인덱스로 짝 짓는다.
    rows = []
    with torch.no_grad():
        ld = loaders(ds, 64, False)
        it = iter(ld)
        for i0 in range(0, len(ds), 64):
            xs, _, _, labels = next(it)
            preds = decode_greedy(model(xs.to(dev)).cpu())
            for k, p in enumerate(preds):
                fname, _, lab = ds.items[i0 + k]
                rows.append({"file_name": fname, "label": lab,
                             "pred": p, "ok": p == lab})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    acc = sum(r["ok"] for r in rows) / max(len(rows), 1)
    print(f"{out_path.name}: {acc*100:.2f}% (n={len(rows)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default=str(HERE / "synth_coco" / "VE"))
    ap.add_argument("--split", default="train2017")
    a = ap.parse_args()
    set_dir = Path(a.set)
    out_dir = HERE / "_diag" / "reader_dump"
    for arm, ckpt in ARMS.items():
        for src, boxes in BOXES.items():
            run(ckpt, set_dir, a.split, boxes,
                out_dir / f"{set_dir.name}_{arm}_{src}.jsonl")


if __name__ == "__main__":
    main()
