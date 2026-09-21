# **작아진 밴드의 획이 실촬만큼 살아 있는가** — 배율을 내린 뒤 반드시 볼 것.
#
# 왜(2026-09-20): 증강으로 배율 하한을 내렸을 때 단조롭게 나빠졌다(§20.1).
# 가설은 "이미 그려진 그림을 또 줄여 획이 뭉갰다"였다. 생성기 쪽에서 배율을
# 내릴 때도 같은 일이 나면 같은 실패를 반복한다.
#
# 자: 모델이 **실제로 받는 416 레터박스 입력**에서 밴드를 잘라, 획 에지의
# 세기를 밴드 대비로 정규화해 잰다. 밴드 픽셀 높이를 맞춰 비교해야 한다 —
# 큰 밴드가 선명한 건 당연하다.
#
#   sharp = mean(|grad|) / (p95 - p5)
#
# 대비로 나누는 이유: 밝기 스케일이 다른 코퍼스끼리 맞대야 하기 때문이다.
# 값이 크면 획 경계가 서 있다는 뜻이다.
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np

from train_band import letterbox
from report_fail_mix import rows, HERE


def sharp(img, box):
    x0, y0 = int(max(0, box[0])), int(max(0, box[1]))
    x1, y1 = int(min(img.shape[1], box[2])), int(min(img.shape[0], box[3]))
    if x1 - x0 < 6 or y1 - y0 < 4:
        return None
    c = img[y0:y1, x0:x1].astype(np.float32)
    gx = cv2.Sobel(c, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(c, cv2.CV_32F, 0, 1, ksize=3)
    contrast = float(np.percentile(c, 95) - np.percentile(c, 5))
    if contrast < 5:
        return None
    return float(np.hypot(gx, gy).mean()) / contrast, y1 - y0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--scene", default="mixed")
    ap.add_argument("--size", type=int, default=416)
    a = ap.parse_args()

    out = {}

    # ── 합성: 생성기를 그 자리에서 돌린다(코퍼스를 다시 굽기 전에 본다) ──
    import synth_panel as sp
    v = []
    for i in range(a.n):
        rng = random.Random(90000 + i)
        s = sp.render_panel(rng.choice([74, 122, 189, 212, 95]), rng,
                            scene=a.scene)
        img = s["panel"] if "panel" in s else None
        if img is None:
            continue
        q = np.asarray(s["quad"], float)
        lb, r, dx, dy = letterbox(img, a.size)
        b = [q[:, 0].min()*r+dx, q[:, 1].min()*r+dy,
             q[:, 0].max()*r+dx, q[:, 1].max()*r+dy]
        t = sharp(lb, b)
        if t:
            v.append(t)
    out["합성 (새 생성기)"] = v

    # ── 실촬: 같은 레터박스를 통과시킨다 ─────────────────────────────
    from eval_band_roboflow import population
    pop = population()
    dev = set(json.loads((HERE / "rf_split.json")
                         .read_text(encoding="utf-8"))["dev"])
    v = []
    for cid in sorted(k for k in pop if k in dev)[:a.n]:
        p, gt = pop[cid]
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        lb, r, dx, dy = letterbox(img, a.size)
        b = [gt[0]*r+dx, gt[1]*r+dy, gt[2]*r+dx, gt[3]*r+dy]
        t = sharp(lb, b)
        if t:
            v.append(t)
    out["실촬 Roboflow"] = v

    print(f"416 레터박스 입력에서 밴드 획의 선명도 (에지세기/대비)")
    print(f"  {'':<20}{'n':>5}{'밴드높이px':>11}{'선명도 중앙':>13}")
    for nm, v in out.items():
        if not v:
            continue
        A = np.array([x[0] for x in v]); Hh = np.array([x[1] for x in v])
        print(f"  {nm:<20}{len(v):>5}{np.median(Hh):>11.0f}"
              f"{np.median(A):>13.4f}")

    # 밴드 픽셀 높이를 맞춰 다시 — 크기가 다르면 선명도는 당연히 다르다.
    print()
    print("  **밴드 높이를 맞춰서** (양쪽에 다 있는 구간만)")
    print(f"  {'밴드높이px':<14}{'합성 n':>8}{'합성':>9}{'실촬 n':>8}{'실촬':>9}")
    for lo, hi in ((20, 40), (40, 60), (60, 90), (90, 140)):
        row = []
        for nm in out:
            A = [x[0] for x in out[nm] if lo <= x[1] < hi]
            row.append((len(A), np.median(A) if A else float("nan")))
        if row[0][0] >= 5 and row[1][0] >= 5:
            print(f"  {lo}~{hi:<10}{row[0][0]:>8}{row[0][1]:>9.4f}"
                  f"{row[1][0]:>8}{row[1][1]:>9.4f}")
    print()
    print("  합성이 실촬보다 **낮으면 획이 뭉갠 것**이다 — 증강으로 줄였을 때의")
    print("  실패(§20.1)를 생성기 쪽에서 반복하는 셈이므로 굽기 전에 고친다.")


if __name__ == "__main__":
    main()
