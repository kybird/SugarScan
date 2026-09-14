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

# GM 쿼드는 사람 라벨 우선이다(gm_quads.load_gm_quads, 2026-09-13).
# 구판은 검출기 출력(gmscreen_quads_oriented)만 봤고 그걸 실측이라
# 불렀다 — 사람이 그린 화면 상자 411행이 따로 있었는데 측정 경로
# 어디도 쓰지 않았다.
from gm_quads import quad_rows  # noqa: E402
UP = HERE.parent / "upstream" / "datumo"


def _load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def collect(wide=False):
    quads = {r["id"]: r for r in quad_rows()}
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
        # 가로 크롭은 배치 가족이 다르다(숫자 왼쪽 + 오른쪽 정보 칼럼).
        # --wide 로 그쪽만 따로 잰다(2026-09-13).
        if (gw / gh >= 1.0) != wide:
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


def emit_layouts():
    """LAYOUTS 블록을 실측에서 찍어 낸다 — 손으로 옮겨 적지 않는다.
    2026-09-13: 기기당 '한 점'(중앙값)만 쓰면 합성이 기기 수만큼의 점이 되고,
    검출기가 그 사이를 못 메운다(v1 IoU 0.680 < v0 0.717). 실물은 같은 기기도
    촬영 각도·거리로 종횡비와 밴드 비율이 흔들린다 — p10/중앙/p90 을 함께
    찍어 렌더러가 그 안에서 뽑게 한다. 세로·가로를 한 번에 본다(기기가 어느
    쪽인지도 실측이 정한다)."""
    import numpy as np
    from synth_profiles import PROFILE_DEVICES
    rows = collect(False) + collect(True)
    g = {}
    for r in rows:
        g.setdefault(r["name"], []).append(r)
    want = {n: pid for pid, names in PROFILE_DEVICES.items() for n in names}
    out = {}
    for name, v in g.items():
        pid = want.get(name)
        if pid is None:
            continue
        arr = lambda k: np.asarray([x[k] for x in v], float)
        tri = lambda k: (round(float(np.percentile(arr(k), 10)), 3),
                         round(float(np.median(arr(k))), 3),
                         round(float(np.percentile(arr(k), 90)), 3))
        out[pid] = dict(ar=tri("panel_ar"), bw=tri("band_w"), bh=tri("band_h"),
                        cx=tri("band_cx"), cy=tri("band_cy"), n=len(v))
    print("# device_layout_stats.py emit 산출 — 손으로 고치지 마라")
    for pid, d in sorted(out.items(), key=lambda kv: -kv[1]["n"]):
        print(f'    "{pid}": dict(ar={d["ar"]}, bw={d["bw"]}, bh={d["bh"]},')
        print(f'{" " * (len(pid) + 10)}cx={d["cx"]}, cy={d["cy"]}, n={d["n"]}),')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--wide", action="store_true",
                    help="가로 크롭만 잰다(기본: 세로)")
    ap.add_argument("--emit", action="store_true",
                    help="LAYOUTS 블록을 실측에서 찍어 낸다(세로+가로 합산)")
    args = ap.parse_args()
    if args.emit:
        emit_layouts()
        return 0
    rows = collect(wide=args.wide)
    from synth_profiles import PROFILE_DEVICES
    targets = None if args.all else {n for names in PROFILE_DEVICES.values()
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
