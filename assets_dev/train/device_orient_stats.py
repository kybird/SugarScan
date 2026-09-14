# 기기별 세로/가로 판정 — 사람 LCD 라벨(gmscreen+band)의 GM 크롭 종횡비 비율로
# 가로형 기기를 확정한다(사람 지침 2026-09-13: "라벨링 비율 보면 알 수 있다").
#   python device_orient_stats.py
import json

import numpy as np

HERE = __import__("pathlib").Path(__file__).resolve().parent

from gm_quads import quad_rows  # noqa: E402


def main():
    quads = {r["id"]: r for r in (json.loads(l) for l in
             open(HERE / "gmscreen_quads_oriented.jsonl", encoding="utf-8"))}
    devs = [json.loads(l) for l in open(HERE / "device_labels.jsonl", encoding="utf-8")]
    from synth_panel import _PROFILE_DEVICES
    targets = {n for names in _PROFILE_DEVICES.values() for n in names}
    rows = {}
    for d in devs:
        name = f"{d['brand']} {d['model']}".strip()
        if name not in targets or d.get("status") != "identified":
            continue
        g = quads.get(d["id"])
        if g is None:
            continue
        q = np.asarray(g["quad"])
        ar = (q[:, 0].max() - q[:, 0].min()) / max(1, q[:, 1].max() - q[:, 1].min())
        rows.setdefault(name, []).append(ar)
    print(f"{'device':<28} {'n':>3} {'세로':>3} {'가로':>3} {'median AR':>9}")
    for name in sorted(rows):
        a = np.asarray(rows[name])
        n_p = int((a < 1.0).sum())
        n_w = int((a >= 1.0).sum())
        print(f"{name:<28} {len(a):>3} {n_p:>3} {n_w:>3} {np.median(a):>9.3f}"
              + ("   <== 가로 다수" if n_w > n_p else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
Q = {r['id']: r['quad'] for r in quad_rows()}
    devs = [json.loads(l) for l in open(HERE / "device_labels.jsonl", encoding="utf-8")]
    from synth_panel import _PROFILE_DEVICES
    targets = {n for names in _PROFILE_DEVICES.values() for n in names}
    rows = {}
    for d in devs:
        name = f"{d['brand']} {d['model']}".strip()
        if name not in targets or d.get("status") != "identified":
            continue
        g = quads.get(d["id"])
        if g is None:
            continue
        q = np.asarray(g["quad"])
        ar = (q[:, 0].max() - q[:, 0].min()) / max(1, q[:, 1].max() - q[:, 1].min())
        rows.setdefault(name, []).append(ar)
    print(f"{'device':<28} {'n':>3} {'세로':>3} {'가로':>3} {'median AR':>9}")
    for name in sorted(rows):
        a = np.asarray(rows[name])
        n_p = int((a < 1.0).sum())
        n_w = int((a >= 1.0).sum())
        print(f"{name:<28} {len(a):>3} {n_p:>3} {n_w:>3} {np.median(a):>9.3f}"
              + ("   <== 가로 다수" if n_w > n_p else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
