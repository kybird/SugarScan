# 밴드 쿼드의 '모서리를 얼마나 정확히 찍는가' — 합성 홀드아웃에서 잰다.
#
# 배경(2026-09-14): 사람 질문 「기울어진 사진을 펴려면 네 점이 필요한데 정확한
# 지점을 찍을 수 있냐」. 게이트의 IoU 는 사람 밴드 라벨이 전부 축정렬이라
# 기울기 정확도를 못 잰다(band_det_orient_split.py 머리말). 합성은 GT 가 정확한
# 네 점이므로 거기서는 잴 수 있다 — 단, 합성에서의 성적이지 실사진 성적이 아니다.
#
# 모서리 오차는 밴드 높이로 정규화해 인쇄한다(장마다 해상도가 달라 픽셀
# 절대값은 비교가 안 된다).
#
# 주의: --data 가 그 체크포인트의 학습 코퍼스면 홀드아웃이 아니다. 밤샘 스윕의
# synth_night_5000 은 n5k 의 학습셋이고 n10k 이상에는 홀드아웃이다(시드 75000
# vs 110000).
#
# 사용: python band_det_corner_error.py --ckpt band_det_n40k_ep60.pt \
#          --data synth_night_5000 [--n 800]
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch

from train_band_detector import BandQuadNet
from eval_band_detector import det_predict, poly_iou

HERE = Path(__file__).resolve().parent


def quad_angle(q):
    """위변·아래변 평균 기울기(도)."""
    a = np.degrees(np.arctan2(q[1, 1] - q[0, 1], q[1, 0] - q[0, 0]))
    b = np.degrees(np.arctan2(q[2, 1] - q[3, 1], q[2, 0] - q[3, 0]))
    return (a + b) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="band_det_n40k_ep60.pt")
    ap.add_argument("--data", default="synth_night_5000")
    ap.add_argument("--n", type=int, default=800)
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = BandQuadNet().to(dev)
    model.load_state_dict(torch.load(HERE / args.ckpt, map_location=dev))
    model.eval()

    root = HERE / args.data
    rows = [json.loads(l) for l in open(root / "manifest.jsonl", encoding="utf-8")]
    rows = rows[:args.n]

    cerr, aerr, ious, agt, apr = [], [], [], [], []
    for r in rows:
        img = cv2.imread(str(root / "images" / f"{r['id']}.png"), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        gt = np.asarray(r["quad"], np.float32)
        pr = det_predict(model, img, dev)
        h = np.linalg.norm(gt[3] - gt[0])          # 밴드 높이 = 왼쪽 변
        d = np.linalg.norm(pr - gt, axis=1) / max(h, 1e-6)
        cerr.append(d.mean())
        ga, pa = quad_angle(gt), quad_angle(pr)
        agt.append(ga); apr.append(pa)
        aerr.append(abs(pa - ga))
        ious.append(poly_iou(pr, gt))

    cerr, aerr, ious = map(np.asarray, (cerr, aerr, ious))
    agt, apr = np.asarray(agt), np.asarray(apr)
    print(f"{args.ckpt} on {args.data}  n={len(cerr)}")
    print(f"  쿼드 IoU        median={np.median(ious):.3f} p10={np.percentile(ious,10):.3f}")
    print(f"  모서리 오차      median={np.median(cerr)*100:.2f}% p90={np.percentile(cerr,90)*100:.2f}% "
          f"(밴드 높이 대비, 네 점 평균)")
    print(f"  기울기 오차      median={np.median(aerr):.3f}deg p90={np.percentile(aerr,90):.3f}deg "
          f"max={aerr.max():.2f}deg")
    print(f"  기울기 GT        median|d|={np.median(np.abs(agt)):.3f} p90={np.percentile(np.abs(agt),90):.3f}")
    print(f"  기울기 예측      median|d|={np.median(np.abs(apr)):.3f} p90={np.percentile(np.abs(apr),90):.3f}")
    # 기울기를 '맞히는가' 아니면 '0 으로 뭉개는가'
    base = np.abs(agt)   # 항상 0 을 내는 모델의 기울기 오차
    print(f"  ─ 기울기를 0 으로 뭉갰다면 오차 median={np.median(base):.3f}deg "
          f"→ 실제 {np.median(aerr):.3f}deg "
          f"({'배웠다' if np.median(aerr) < np.median(base) * 0.7 else '못 배웠다'})")
    print(f"  상관 corr(GT,예측)={np.corrcoef(agt, apr)[0,1]:.3f}")


if __name__ == "__main__":
    raise SystemExit(main())
