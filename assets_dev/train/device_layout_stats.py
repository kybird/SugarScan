# 기기별 고정 레이아웃 실측 자 — 카드 「합성 글리프 네 결함」 후속 재구조(2026-09-13).
# 사람 지침: 하나의 디바이스는 레이아웃이 고정이다 — LCD 크기·밴드 기하·요소
# 위치를 기기별로 통일하고, 랜덤은 촬영(프레이밍·광학)에만 남긴다.
# 이 스크립트는 device_labels + gmscreen_quads_oriented + band_boxes 에서
# 프로파일별 중앙값을 잰다(§3.7 — 프로파일에 박는 값의 근거).
#
#   python device_layout_stats.py            # 프로파일별 표
#   python device_layout_stats.py --all      # 라벨 있는 전 기기(참고)
import argparse
import json

import numpy as np

HERE = __import__("pathlib").Path(__file__).resolve().parent
UP = HERE.parent / "upstream" / "datumo"


def _load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def collect():
    quads = {r["id"]: r for r in _load(HERE / "gmscreen_quads_oriented.jsonl")}
    bands = _load(HERE / "band_boxes.jsonl")
    devs = {r["id"]: r for r in _load(HERE / "device_labels.jsonl")}
    rows = []
    for b in bands:
        g = quads.get(b["id"])
        if g is None:
            continue
        d = devs.get(b["id"])
        if not d or d.get("status") != "identified":
            continue
        q, gb = np.asarray(g["quad"]), np.asarray(b["quad"])
        gx0, gx1 = q[:, 0].min(), q[:, 0].max()
        gy0, gy1 = q[:, 1].min(), q[:, 1].max()
        gw, gh = gx1 - gx0, gy1 - gy0
        if gw / gh >= 1.0:      # 가로 크롭은 별도 가족 — 여기선 세로만
            continue
        bx0, bx1 = gb[:, 0].min(), gb[:, 0].max()
        by0, by1 = gb[:, 1].min(), gb[:, 1].max()
        rows.append(dict(
            name=f"{d['brand']} {d['model']}".strip(), id=b["id"],
            panel_ar=gw / gh,
            band_w=(bx1 - bx0) / gw, band_h=(by1 - by0) / gh,
            band_cx=((bx0 + bx1) / 2 - gx0) / gw,
            band_cy=((by0 + by1) / 2 - gy0) / gh))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    rows = collect()
    from synth_panel import _PROFILE_DEVICES
    targets = None if args.all else {n for names in _PROFILE_DEVICES.values()
                                     for n in names}
    groups = {}
    for r in rows:
        if targets is not None and r["name"] not in targets:
            continue
        groups.setdefault(r["name"], []).append(r)
    print(f"{'device':<28} {'n':>2} {'panel_ar':>8} {'bw':>6} {'bh':>6} "
          f"{'cx':>6} {'cy':>6}")
    for name in sorted(groups):
        g = groups[name]
        v = {k: float(np.median([r[k] for r in g]))
             for k in ("panel_ar", "band_w", "band_h", "band_cx", "band_cy")}
        print(f"{name:<28} {len(g):>2} {v['panel_ar']:>8.3f} {v['band_w']:>6.3f} "
              f"{v['band_h']:>6.3f} {v['band_cx']:>6.3f} {v['band_cy']:>6.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
