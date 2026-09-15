# 밴드 검출기 예측을 웹툴 오버레이 규약으로 내보낸다.
#
# 배경(2026-09-14): 웹툴의 `/api/quads?kind=band` 는 `datumo_quads_v2.jsonl` 을
# 읽는데 그 파일이 저장소에 없다 — 옛 v2 밴드 모델 시절 산물이고 재구축 때
# 사라졌다. 그래서 밴드 예측 오버레이가 빈 채로 돌고 있었다.
#
# 좌표계: **원본 사진 픽셀**(band_boxes.jsonl 과 같은 표시 좌표). 검출기는 GM
# 크롭을 받아 크롭 좌표로 내므로 크롭 원점을 더해 되돌린다. 이 변환을 빼먹으면
# 쿼드가 화면 좌상단으로 쏠려 그려진다 — [[unnamed-coordinate-frame]].
#
# 예측 파일임을 이름과 스키마로 밝힌다: 파일명에 `_pred`, 행마다 `source` 와
# `ckpt`. 라벨 파일과 같은 디렉터리에 같은 스키마로 두면 언젠가 실측으로
# 둔갑한다 — 그 사고가 2026-09-13 에 있었다
# ([[prediction-used-as-ground-truth]]).
#
# 사용:
#   python predict_band_quads.py --ckpt band_det_n80k.pt
#   python predict_band_quads.py --ckpt band_det_heat40k.pt --out band_quads_pred_heat.jsonl
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

import eval_band_detector as E
from eval_reader import load_gray
from train_band_detector import load_detector
from gm_quads import load_gm_quads

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="band_det_n80k.pt")
    ap.add_argument("--out", default="band_quads_pred.jsonl")
    ap.add_argument("--limit", type=int, default=0, help="0 이면 전량")
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model, arch = load_detector(HERE / args.ckpt, dev)
    quads, src, st = load_gm_quads(with_source=True)
    ids = sorted(quads)
    if args.limit:
        ids = ids[:args.limit]
    print(f"{args.ckpt} (arch={arch})  대상 {len(ids)}장 "
          f"— GM 쿼드 사람 {st['human']} · 검출기 {st['detector']}")

    out = HERE / args.out
    n = miss = 0
    t0 = time.time()
    with open(out, "w", encoding="utf-8") as f:
        for i, pid in enumerate(ids):
            img = load_gray(E.UPSTREAM / "extracted" / "TILDE" / (pid + ".jpg"))
            if img is None:
                miss += 1
                continue
            c = E.crop_photo(img, E._rect_of(quads[pid]))
            if c is None:
                miss += 1
                continue
            crop, cx, cy = c
            q = E.det_predict(model, crop, dev) + np.array([cx, cy], np.float32)
            f.write(json.dumps(dict(
                id=pid, quad=np.round(q, 2).tolist(),
                source="detector", ckpt=args.ckpt, arch=arch,
                gm_source=src[pid]), ensure_ascii=False) + "\n")
            n += 1
            if (i + 1) % 250 == 0:
                print(f"  {i + 1}/{len(ids)}  {time.time() - t0:.0f}s", flush=True)
    print(f"{out}  {n}장 기록 · 건너뜀 {miss} · {time.time() - t0:.0f}s")


if __name__ == "__main__":
    raise SystemExit(main())
