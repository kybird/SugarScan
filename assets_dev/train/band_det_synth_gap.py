# 「훈련이 덜 된 것인가, 합성이 실물과 다른 것인가」를 가른다.
#
# 배경(2026-09-12): v0 를 54종 평가셋에 다시 재니 실사진 det IoU median 0.727
# (잘린 장 제외)이었고, 세로형 실패 시트에서 체계적 편향은 거의 없고 분산만
# 컸다. 그것만 보면 '훈련 부족' 으로 읽힌다. 그런데 학습 로그는 합성 sanity-val
# 손실이 train 보다도 낮았다(epoch 40: train 0.00166 / val 0.00031).
#
# 손실은 IoU 가 아니다. 같은 모델을 합성에 돌려 같은 자(poly_iou)로 IoU 를
# 재야 두 수치가 비교 가능하다. 합성 IoU 가 높으면 훈련 부족이 아니라 도메인
# 격차다 — 에폭을 늘려도 실사진은 안 움직인다.
#
# 자와 예측 경로를 새로 만들지 않는다 — eval_band_detector 의 det_predict ·
# poly_iou 를 그대로 쓴다.
#
# 사용:
#   python band_det_synth_gap.py --images <synth>/images --manifest <synth>/manifest.jsonl
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch

import eval_band_detector as E
from train_band_detector import BandQuadNet

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--ckpt", default=str(HERE / "band_det_v0.pt"))
    ap.add_argument("--limit", type=int, default=300)
    a = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = BandQuadNet().to(dev)
    model.load_state_dict(torch.load(a.ckpt, map_location=dev))
    model.eval()

    imgs = Path(a.images)
    rows = [json.loads(l) for l in Path(a.manifest).read_text(encoding="utf-8")
            .splitlines() if l.strip()][:a.limit]
    ious, por = [], []
    for r in rows:
        p = imgs / (r["id"] + ".png")
        if not p.exists():
            continue
        g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if g is None:
            continue
        pred = E.det_predict(model, g, dev)
        gt = np.asarray(r["quad"], np.float32)
        ious.append(E.poly_iou(pred, gt))
        por.append(r["w"] / r["h"] < 1.0)

    a_ = np.asarray(ious)
    m = np.asarray(por)
    print(f"합성 det IoU  n={len(a_)}  median={np.median(a_):.3f} "
          f"p10={np.percentile(a_, 10):.3f} min={a_.min():.3f}")
    for tag, sel in (("세로형", m), ("가로형", ~m)):
        if sel.sum():
            v = a_[sel]
            print(f"  {tag} n={int(sel.sum()):3d} median={np.median(v):.3f} "
                  f"p10={np.percentile(v, 10):.3f}")
    print("\n비교 — 실사진(잘린 장 제외 246장)은 median 0.727 p10 0.570 이다.")
    print("합성 IoU 가 실사진보다 크게 높으면 훈련 부족이 아니라 도메인 격차다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
