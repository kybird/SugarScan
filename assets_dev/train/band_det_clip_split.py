# 밴드 검출 게이트 결과를 「크롭이 밴드를 잘랐나」로 갈라 본다.
#
# 배경(2026-09-12): v0 체크포인트를 54종 평가셋으로 다시 재니 최악 6장이
# 전부 같은 모양이었다 — 사람 라벨이 GM 크롭 왼쪽 가장자리 띠로만 남고
# 검출기는 화면 가운데 정보칼럼을 숫자줄로 집는다. 숫자가 크롭 밖이면 어떤
# 밴드 검출기도 못 이긴다. 그 하드 실링과 나머지를 갈라야 어디를 고칠지
# 정해진다.
#
# 자를 새로 만들지 않는다 — measure_panel_stats 의 로더와 _rect_of 를 쓴다.
# 입력: eval_band_detector.py gate 가 남기는 _diag/band_det_v0/gate_results.jsonl
#
# 사용: python band_det_clip_split.py [--thresh 0.95]
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import measure_panel_stats as M

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "_diag" / "band_det_v0" / "gate_results.jsonl"


def inside_frac():
    """사람 밴드 라벨이 GM 크롭 안에 든 면적 비율. 1.0 이면 온전히 들어왔다."""
    quads = {r["id"]: r for r in M._load_jsonl(M.QUADS_ORIENTED)}
    out = {}
    for b in M._load_jsonl(M.BAND_BOXES):
        g = quads.get(b["id"])
        if g is None:
            continue
        gx, bx = M._rect_of(g["quad"]), M._rect_of(b["quad"])
        ix0, iy0 = max(gx[0], bx[0]), max(gx[1], bx[1])
        ix1, iy1 = min(gx[2], bx[2]), min(gx[3], bx[3])
        inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
        area = max(1e-9, (bx[2] - bx[0]) * (bx[3] - bx[1]))
        out[b["id"]] = inter / area
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thresh", type=float, default=0.95,
                    help="이 비율 미만이면 '잘린 장'")
    ap.add_argument("--results", default=str(RESULTS))
    a = ap.parse_args()

    res = [json.loads(l) for l in Path(a.results).read_text(encoding="utf-8")
           .splitlines() if l.strip()]
    ins = inside_frac()

    f = np.array([ins[r["id"]] for r in res if r["id"] in ins])
    print(f"n={len(f)}  밴드가 GM 크롭 안에 든 비율: "
          f"median={np.median(f):.3f} p10={np.percentile(f, 10):.3f}")
    for th in (0.99, 0.95, 0.80, 0.50):
        print(f"  {th:.2f} 미만(잘림): {int((f < th).sum()):3d}장 "
              f"({100 * np.mean(f < th):.1f}%)")

    ok = np.array([r["iou_det"] for r in res
                   if ins.get(r["id"], 1.0) >= a.thresh])
    cl = np.array([r["iou_det"] for r in res
                   if ins.get(r["id"], 1.0) < a.thresh])
    print(f"\n{'구분':<22} {'n':>4} {'median':>7} {'p10':>7} {'min':>7}")
    for tag, arr in ((f"밴드가 크롭 안(>={a.thresh})", ok), ("잘린 장", cl)):
        if not len(arr):
            continue
        print(f"{tag:<22} {len(arr):4d} {np.median(arr):7.3f} "
              f"{np.percentile(arr, 10):7.3f} {arr.min():7.3f}")

    # 기기별 — 약한 기기가 잘림 탓인지 가른다.
    d = defaultdict(lambda: ([], []))
    for r in res:
        good = ins.get(r["id"], 1.0) >= a.thresh
        d[r["device"]][0 if good else 1].append(r["iou_det"])
    rows = [(np.median(g) if g else 0.0, dev, g, c)
            for dev, (g, c) in d.items() if len(g) + len(c) >= 3]
    print(f"\n{'기기':<30} {'크롭 안':<22} 잘린 장")
    for _, dev, g, c in sorted(rows):
        sg = f"n={len(g):2d} med={np.median(g):.3f}" if g else "없음"
        sc = f"n={len(c):2d} med={np.median(c):.3f}" if c else "-"
        print(f"{dev[:28]:<30} {sg:<22} {sc}")

    worst = sorted(((ins[r["id"]], r["id"]) for r in res if r["id"] in ins))[:12]
    print("\n가장 많이 잘린 12장:")
    for v, i in worst:
        print(f"   {i:<24} {v:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
