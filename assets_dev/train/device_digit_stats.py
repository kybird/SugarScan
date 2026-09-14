# 기기별 숫자 글리프 실측 — dh 를 밴드 높이 가정(1.26 제수)이 아니라 실사진
# 숫자 픽셀에서 직접 잰다(사람 지적 2026-09-13: "LCD 대비 숫자가 심하게 작다").
# 방법: 밴드 라벨(사람이 찍은 숫자줄 쿼드) 안에서 잉크 연결성분을 찾고,
# 가장 큰 성분(숫자)의 높이·피치를 유리 크기로 정규화한다.
#   python device_digit_stats.py
import json

import cv2
import numpy as np

from measure_polarity import load_gray

HERE = __import__("pathlib").Path(__file__).resolve().parent
UP = HERE.parent / "upstream" / "datumo"


def _load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def digit_stats():
    quads = {r["id"]: r for r in _load(HERE / "gmscreen_quads_oriented.jsonl")}
    bands = _load(HERE / "band_boxes.jsonl")
    devs = {r["id"]: r for r in _load(HERE / "device_labels.jsonl")}
    out = {}
    for b in bands:
        g = quads.get(b["id"])
        d = devs.get(b["id"])
        if g is None or not d or d.get("status") != "identified":
            continue
        name = f"{d['brand']} {d['model']}".strip()
        q, gb = np.asarray(g["quad"]), np.asarray(b["quad"])
        gw, gh = q[:, 0].max() - q[:, 0].min(), q[:, 1].max() - q[:, 1].min()
        if gw / gh >= 1.0:
            continue
        p = UP / "extracted" / "TILDE" / (b["id"].replace("/", "\\") + ".jpg")
        if not p.exists():
            p = UP / "extracted" / "TILDE" / (b["id"] + ".jpg")
        img = load_gray(p)
        if img is None:
            continue
        bx0, bx1 = int(gb[:, 0].min()), int(np.ceil(gb[:, 0].max()))
        by0, by1 = int(gb[:, 1].min()), int(np.ceil(gb[:, 1].max()))
        crop = img[by0:by1, bx0:bx1].astype(np.float32)
        if min(crop.shape) < 10:
            continue
        p5, p95 = np.percentile(crop, 5), np.percentile(crop, 95)
        if abs(p95 - p5) < 15:
            continue
        thr = np.percentile(np.abs(crop - np.median(crop)), 80)
        m = (np.abs(crop - np.median(crop)) > max(thr, 12)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
        n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
        # 숫자 = 면적 상위 & 높이가 크롭 절반 이상인 성분
        comps = [(st[i, cv2.CC_STAT_AREA], st[i, cv2.CC_STAT_HEIGHT],
                  st[i, cv2.CC_STAT_WIDTH], cen[i]) for i in range(1, n)
                 if st[i, cv2.CC_STAT_HEIGHT] >= crop.shape[0] * 0.45
                 and st[i, cv2.CC_STAT_AREA] >= 80]
        if len(comps) < 2:
            continue
        comps.sort(key=lambda t: -t[0])
        tops = comps[:4]
        dh_px = float(np.median([c[1] for c in tops]))
        xs = sorted(c[3][0] for c in tops)
        diffs = [b_ - a_ for a_, b_ in zip(xs, xs[1:]) if b_ - a_ > 5]
        rec = dict(dh_glass=dh_px / gh, dh_band=dh_px / (by1 - by0),
                   band_glass=(by1 - by0) / gh)
        if diffs:
            rec["pitch_dh"] = float(np.median(diffs)) / dh_px
        out.setdefault(name, []).append(rec)
    return out


def main():
    from synth_panel import _PROFILE_DEVICES
    targets = {n for names in _PROFILE_DEVICES.values() for n in names}
    groups = digit_stats()
    print(f"{'device':<28} {'n':>2} {'dh/glass':>8} {'dh/band':>8} "
          f"{'band/glass':>10} {'pitch/dh':>8}")
    for name in sorted(groups):
        if name not in targets:
            continue
        g = groups[name]
        dhg = np.median([r["dh_glass"] for r in g])
        dhb = np.median([r["dh_band"] for r in g])
        bg = np.median([r["band_glass"] for r in g])
        pd = [r["pitch_dh"] for r in g if "pitch_dh" in r]
        pdv = f"{np.median(pd):.3f}" if pd else "-"
        print(f"{name:<28} {len(g):>2} {dhg:>8.3f} {dhb:>8.3f} {bg:>10.3f} "
              f"{pdv:>8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
