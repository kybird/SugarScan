# 예측 상자가 **숫자 획(잉크)** 을 얼마나 담는가 — 실촬에서.
#
# 왜 필요한가 (2026-09-19): 단계 2에서 절차적 배경 조건이 상자를 밴드 크기로
# 딱 맞게 줄였다(면적비 1.72 -> 1.09). 그러자 사람이 그린 밴드 라벨의 **여백**
# 을 못 담아 게이트가 무너졌다(포함 실패 34% -> 72%). 그 실패가
#   (가) 숫자 획을 잘랐다  — 치명적이다. 리더가 못 읽는다.
#   (나) 사람 여백만 잘랐다 — 무해하고 오히려 바람직할 수 있다.
# 중 어느 것인지 **사람 밴드 라벨만으로는 가릴 수 없다.**
#
# 왜 상자를 추정하지 않고 픽셀을 세는가: 합성의 `digit_box` 는 잉크의 외접
# 상자가 아니라 **배치 슬롯 사각형**(placer 의 band 칸)이라 슬롯 여백을
# 포함한다. 그걸 실촬에서 복원하려 하면 추정 오차 위에 정의 불일치가 겹친다.
# 우리가 실제로 묻는 것은 "획을 잘랐나"이므로 **획 픽셀을 직접 센다.**
#
# **조건 간 공정성**: 잉크 마스크는 사람 밴드 라벨 안에서만, 모델 예측과
# 무관하게 계산된다. 두 조건에 **완전히 같은 마스크**가 쓰인다 — 추출이
# 틀리더라도 조건 간 편향이 아니라 잡음으로만 들어간다. 이것이 이 자를
# 쓸 수 있게 하는 성질이다.
#
# 마스크 만드는 법 (밴드 라벨 안에서만 본다):
#   1. Otsu 로 가르고 **소수 부류를 잉크로** 본다. 숫자는 바탕보다 면적이
#      작다 — 극성(어두운 글자/밝은 글자)을 따로 안 줘도 된다.
#      (polarity_gt 는 272장 중 30장뿐이라 그것만으로는 못 돈다.)
#   2. 작은 점을 열림으로 지운다 — 노이즈·먼지.
#   3. **팽창해서 묶은 뒤** 키가 큰 덩어리만 남긴다. 7세그먼트는 획이 떨어져
#      있어 그냥 성분을 세면 한 숫자가 조각나고, 키로 거르면 짧은 획이
#      통째로 버려진다. 마스크는 덩어리 안의 **원래 잉크**다.
#
# 사용:
#   python measure_ink_coverage.py --validate          # 합성에서 먼저 검증
#   python measure_ink_coverage.py --arms bce,bg       # 실촬 두 조건 비교
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REAL = HERE / "_diag" / "band_real"


def ink_mask(gray, band, open_frac=0.06, glue_frac=0.18, tall_frac=0.55):
    """밴드 상자 안의 숫자 획 마스크. (mask, (x0,y0)) 또는 None."""
    x0, y0, x1, y1 = [int(round(v)) for v in band]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(gray.shape[1], x1), min(gray.shape[0], y1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    crop = cv2.GaussianBlur(gray[y0:y1, x0:x1], (3, 3), 0)
    h = crop.shape[0]
    _, th = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink = th if (th > 0).mean() < 0.5 else (255 - th)
    k = max(1, int(round(h * open_frac)))
    if k > 1:
        ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    d = max(1, int(round(h * glue_frac)))
    glue = cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_RECT, (d, d)))
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(
        (glue > 0).astype(np.uint8), 8)
    if n <= 1:
        return None
    hs = stats[1:, cv2.CC_STAT_HEIGHT]
    ar = stats[1:, cv2.CC_STAT_AREA]
    tp = stats[1:, cv2.CC_STAT_TOP]
    # **지배적인 숫자 행에 고정한다.** 키만으로 고르면 글레어 얼룩이나 화면
    # 반대편의 표기가 같이 뽑혀 마스크가 숫자 밖으로 번진다 — 그 오염은
    # 상자가 좁은 조건에 더 불리하게 작용하므로 조건 간 중립이 깨진다
    # (2026-09-19 검증에서 p10 0.06 으로 드러났다).
    # 먼저 면적x키가 가장 큰 덩어리를 닻으로 잡고, **세로로 그 닻과 겹치는**
    # 덩어리만 더한다. 한 줄에 놓인 숫자들은 서로 겹치고 딴 데 있는 얼룩은
    # 안 겹친다.
    anchor = int(np.argmax(ar.astype(np.float64) * hs))
    a0, a1 = tp[anchor], tp[anchor] + hs[anchor]
    ov = np.minimum(tp + hs, a1) - np.maximum(tp, a0)
    keep = np.flatnonzero((ov >= 0.5 * np.minimum(hs, hs[anchor]))
                          & (hs >= tall_frac * hs[anchor])
                          & (ar > 0.02 * ar[anchor]))
    if keep.size == 0:
        keep = np.array([anchor])
    sel = np.isin(lbl, keep + 1) & (ink > 0)
    if not sel.any():
        return None
    return sel, (x0, y0)


def coverage(sel_off, pred):
    """예측 상자가 담는 잉크 픽셀 비율."""
    sel, (ox, oy) = sel_off
    ys, xs = np.nonzero(sel)
    px, py = xs + ox, ys + oy
    inside = ((px >= pred[0]) & (px <= pred[2])
              & (py >= pred[1]) & (py <= pred[3]))
    return float(inside.mean())


def validate(root, split, limit=0):
    """합성에서 — 잉크 기준과 참 digit_box 기준이 **같은 판정을 주는가**.

    digit_box 는 슬롯 사각형이라 잉크보다 넓다. 그래서 두 지표가 완전히
    같을 수는 없다. 보는 것은 **일치율**이다: digit_box 를 다 담은 장은
    잉크도 다 담아야 한다(그 반대는 성립할 필요 없다).
    """
    root = Path(root)
    rows = [json.loads(l) for l in
            (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    if limit:
        rows = rows[:limit]
    same, viol, n, miss = 0, 0, 0, 0
    covs = []
    for r in rows:
        img = cv2.imread(str(root / split / f"{r['id']}.png"), cv2.IMREAD_GRAYSCALE)
        if img is None or r.get("digit_box") is None:
            continue
        m = ink_mask(img, [float(v) for v in r["box"]])
        if m is None:
            miss += 1
            continue
        db = [float(v) for v in r["digit_box"]]
        c = coverage(m, db)          # 슬롯 상자가 잉크를 담는 비율
        covs.append(c)
        n += 1
        same += c >= 0.999
        viol += c < 0.99
    covs = np.array(covs)
    print(f"합성 검증 — **참 digit_box(슬롯)가 추출한 잉크를 담는가** n={n} "
          f"· 마스크 실패 {miss}")
    print(f"  담는 비율  p01 {np.percentile(covs,1):.4f} "
          f"p10 {np.percentile(covs,10):.4f} 중앙 {np.median(covs):.4f}")
    print(f"  100% 담은 장 {100*same/n:.2f}%  ·  99% 미만 {100*viol/n:.2f}%")
    print("  읽는 법: 슬롯은 잉크보다 넓으므로 100% 에 가까워야 한다. 낮으면"
          " 마스크가 슬롯 밖의 것(단위 표기·반사)을 잉크로 주웠다는 뜻이다.")
    return covs


def arms(names, seeds, tau):
    from eval_band_real import population, DATUMO
    ids, band, lab, _ = population()
    masks = {}
    print(f"잉크 마스크 만드는 중 (사람 밴드 라벨 안에서만, **조건과 무관**) "
          f"n={len(ids)}")
    for cid in ids:
        img = cv2.imread(str(DATUMO / lab[cid]), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        m = ink_mask(img, band[cid])
        if m is not None:
            masks[cid] = m
    print(f"  마스크 {len(masks)}장 (실패 {len(ids)-len(masks)})")

    print(f"\n실촬 코퍼스 A — **잉크 기준** (τ={tau})")
    print(f"  {'조건':<8}{'잉크 100%':>11}{'±SD':>7}{'잉크≥99%':>11}"
          f"{'+면적≤τ':>10}{'잉크 밖 p50':>12}")
    out = {}
    for arm in names:
        full, near, gate, lost = [], [], [], []
        for s in seeds:
            p = REAL / f"{arm}_s{s}.jsonl"
            if not p.exists():
                continue
            rs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
                  if l.strip()]
            f1, n1, g1, l1 = [], [], [], []
            for r in rs:
                if r["id"] not in masks:
                    continue
                c = coverage(masks[r["id"]], r["pred"]) if r["det"] else 0.0
                f1.append(c >= 0.999)
                n1.append(c >= 0.99)
                g1.append((c >= 0.999) and r["area_ratio"] <= tau)
                l1.append(1.0 - c)
            full.append(100*np.mean(f1)); near.append(100*np.mean(n1))
            gate.append(100*np.mean(g1)); lost.append(np.median(l1)*100)
        full, near, gate = np.array(full), np.array(near), np.array(gate)
        out[arm] = gate
        print(f"  {arm:<8}{full.mean():>10.1f}%{full.std(ddof=1):>7.2f}"
              f"{near.mean():>10.1f}%{gate.mean():>9.1f}%{np.mean(lost):>11.2f}%")
    if len(names) == 2 and all(a in out for a in names):
        a, b = names
        print(f"\n  짝 차이({b} − {a}) {out[b].mean()-out[a].mean():+.2f}점 "
              f"(시드 평균 기준)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--arms", default="")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--tau", type=float, default=2.0)
    ap.add_argument("--data", default=str(HERE / "synth_coco" / "V"))
    ap.add_argument("--split", default="train2017")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if a.validate:
        validate(a.data, a.split, a.limit)
    if a.arms:
        arms([x.strip() for x in a.arms.split(",") if x.strip()],
             [int(x) for x in a.seeds.split(",")], a.tau)
    if not (a.validate or a.arms):
        ap.error("--validate 또는 --arms")


if __name__ == "__main__":
    main()
