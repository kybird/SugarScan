# atone_s0 예측 박스의 스케일 보정 상한을 잰다 — 재추론 없는 후처분석.
#
# 동기(2026-09-27): 순수 수동 라벨 홀드아웃 134장에서 atone_s0 IoU 중앙
# 0.8532 · 밴드 전체 온전 포함 44.0% · 면적비 p90 1.28 — 모델이 상자를
# 계통적으로 크게 그린다는 관찰이 있다. 크기 오차가 병목의 얼마인지,
# 균일 보정(scale)만으로 IoU·포함률이 어디까지 회복되는지를 잰 뒤
# 구조 개선에 들어간다(사람 결정: ft 폐기, 순수 합성 학습 안에서 개선).
#
# 질문 셋:
#   1. 균일 스케일 s(중심 고정)를 0.86~1.10까지 훑으며 IoU 중앙·포함률 곡선
#   2. 장마다 최적 s(오라클)의 IoU — 균일 보정의 상한이 어디인지
#   3. 오차 분해: 중심 이동 / 폭비 / 높이비 — 병록이 크기인지 위치인지
#
# 사용:
#   python band_scale_sweep.py                     # 최근 atone_s0.jsonl
#   python band_scale_sweep.py --rows _diag/band_real/atone_s0.jsonl
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def load(p):
    rows = [json.loads(l) for l in
            Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if r.get("det") and r.get("iou") is not None]


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def contain(gt, p):
    x0, y0 = max(gt[0], p[0]), max(gt[1], p[1])
    x1, y1 = min(gt[2], p[2]), min(gt[3], p[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    a = (gt[2]-gt[0]) * (gt[3]-gt[1])
    return inter / a if a > 0 else 0.0


def scaled(p, s):
    cx, cy = (p[0]+p[2])/2, (p[1]+p[3])/2
    w, h = (p[2]-p[0])/2*s, (p[3]-p[1])/2*s
    return [cx-w, cy-h, cx+w, cy+h]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(HERE / "_diag" / "band_real" / "atone_s0.jsonl"))
    a = ap.parse_args()
    rows = load(a.rows)
    n = len(rows)
    print(f"행 {n} · 원본(보정 없음): IoU 중앙 "
          f"{np.median([r['iou'] for r in rows]):.4f} · 포함률1.0 "
          f"{100*sum(1 for r in rows if r['contain'] >= 0.999)/n:.1f}%")

    print("\n[1] 균일 스케일 곡선 (중심 고정)")
    print(f"{'s':>6}{'IoU중앙':>10}{'포함1.0':>9}{'면적비p50':>10}")
    for s in np.arange(0.86, 1.101, 0.02):
        ious, cont, ars = [], 0, []
        for r in rows:
            p = scaled(r["pred"], s)
            g = r["gt"]
            ious.append(iou(p, g))
            cont += contain(g, p) >= 0.999
            ars.append((p[2]-p[0])*(p[3]-p[1]) / max(1., (g[2]-g[0])*(g[3]-g[1])))
        print(f"{s:6.2f}{np.median(ious):10.4f}{100*cont/n:8.1f}%"
              f"{np.median(ars):10.2f}")

    print("\n[2] 장마다 최적 s(오라클) — 균일 보정의 상한")
    best_ious, best_s = [], []
    for r in rows:
        cand = [(iou(scaled(r["pred"], s), r["gt"]), s)
                for s in np.arange(0.80, 1.201, 0.01)]
        bi, bs = max(cand)
        best_ious.append(bi)
        best_s.append(bs)
    print(f"IoU 중앙 {np.median(best_ious):.4f} · 최적s 중앙 {np.median(best_s):.2f} "
          f"(p10 {np.percentile(best_s,10):.2f} · p90 {np.percentile(best_s,90):.2f})")

    print("\n[3] 오차 분해 (정규화: 중심오차=대각선/2 기준, 폭·높이비=pred/gt)")
    cofs, wrs, hrs = [], [], []
    for r in rows:
        p, g = r["pred"], r["gt"]
        pc = np.array([(p[0]+p[2])/2, (p[1]+p[3])/2])
        gc = np.array([(g[0]+g[2])/2, (g[1]+g[3])/2])
        diag = np.hypot(g[2]-g[0], g[3]-g[1]) / 2
        cofs.append(np.linalg.norm(pc - gc) / diag)
        wrs.append((p[2]-p[0]) / max(1., g[2]-g[0]))
        hrs.append((p[3]-p[1]) / max(1., g[3]-g[1]))
    print(f"중심오차 중앙 {np.median(cofs):.3f} (p90 {np.percentile(cofs,90):.3f})")
    print(f"폭비 중앙 {np.median(wrs):.3f} (p10 {np.percentile(wrs,10):.3f} · p90 {np.percentile(wrs,90):.3f})")
    print(f"높이비 중앙 {np.median(hrs):.3f} (p10 {np.percentile(hrs,10):.3f} · p90 {np.percentile(hrs,90):.3f})")


if __name__ == "__main__":
    main()
