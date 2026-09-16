# 사람 밴드 라벨이 없는 장의 예측을, **같은 기기의 라벨 있는 장**과 대조한다.
#
# 배경(2026-09-15): 사람이 기종 화면에서 한 장을 집어 「이 예측이 너의 자로
# 재면 합격이냐」고 물었다. 게이트(IoU vs 사람 밴드 라벨)는 그 장에 라벨이
# 없어 점수를 못 낸다 — 2,494장 중 게이트가 보는 것은 271장(10.9%)뿐이다.
#
# 그래서 있는 것으로 잰다. 밴드의 **화면 안 상대 위치**(화면 쿼드의 폭·높이로
# 정규화한 x0,y0,x1,y1)는 같은 기기에서 거의 같아야 한다 — 액정 인쇄물이니까.
# 그 기기의 라벨 중앙값에서 얼마나 벗어났는지를 낸다.
#
# **이것은 판정이 아니라 의심이다.** 기준이 사람 라벨 몇 장의 중앙값이고,
# 기기에 따라 n 이 한 자릿수다. 합격/불합격을 여기서 선언하면
# [[discovery-ruler-used-as-acceptance-gate]] 다. n 과 퍼짐을 같이 인쇄하는
# 이유가 그것이다 — 기준이 못 미더우면 수치를 보고 물러설 수 있게.
#
# 벗어남의 단위는 **그 기기 밴드 높이 배수**다. 화면 크기가 장마다 다르고,
# 사람이 아는 크기는 픽셀이 아니라 '숫자 몇 개 분'이라서.
#
# 사용:
#   python band_det_unlabeled_check.py glucose_batch1/270
#   python band_det_unlabeled_check.py --device "ACCU-CHEK Instant" --worst 10
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from gm_quads import load_gm_quads
from band_exclusions import load_excluded

HERE = Path(__file__).resolve().parent
EDGES = ("왼", "위", "오른", "아래")


def _norm(band, glass):
    """밴드를 화면 쿼드 기준 상대 사각형으로. (x0,y0,x1,y1) in [0,1]."""
    g = np.asarray(glass, float)
    b = np.asarray(band, float)
    gx0, gy0 = g[:, 0].min(), g[:, 1].min()
    gw = max(g[:, 0].max() - gx0, 1e-6)
    gh = max(g[:, 1].max() - gy0, 1e-6)
    return np.array([(b[:, 0].min() - gx0) / gw, (b[:, 1].min() - gy0) / gh,
                     (b[:, 0].max() - gx0) / gw, (b[:, 1].max() - gy0) / gh])


def device_name(d):
    if not d or d.get("status") != "identified":
        return "(미식별)"
    return (d.get("brand", "") + " " + d.get("model", "")).strip()


def load_all():
    gm, src, _ = load_gm_quads(with_source=True)
    ex = load_excluded()
    devs = {r["id"]: r for r in map(json.loads,
            open(HERE / "device_labels.jsonl", encoding="utf-8"))}
    pred = {r["id"]: r for r in map(json.loads,
            open(HERE / "band_quads_pred.jsonl", encoding="utf-8"))}
    ref = defaultdict(list)          # 기기 -> 사람 라벨의 정규화 사각형
    for r in map(json.loads, open(HERE / "band_boxes.jsonl", encoding="utf-8")):
        if r["id"] in ex or "quad" not in r or r["id"] not in gm:
            continue
        ref[device_name(devs.get(r["id"]))].append(
            (r["id"], _norm(r["quad"], gm[r["id"]])))
    return gm, src, devs, pred, ref


def report(pid, gm, src, devs, pred, ref):
    name = device_name(devs.get(pid))
    if pid not in pred:
        print(f"{pid}  예측이 없다"); return
    if pid not in gm:
        print(f"{pid}  화면 쿼드가 없다 — 정규화 못 한다"); return
    rows = ref.get(name, [])
    p = _norm(pred[pid]["quad"], gm[pid])

    print(f"{pid}   기기: {name}")
    print(f"  화면 쿼드 출처: {src.get(pid)}"
          + ("   ← 검출기 출력이다. 기준틀 자체가 예측이다"
             if src.get(pid) != "human" else ""))
    print(f"  이 장에 사람 밴드 라벨: {'있다' if any(i == pid for i, _ in rows) else '없다 — 게이트 밖'}")
    if len(rows) < 2:
        print(f"  같은 기기 라벨 {len(rows)}장 — 대조할 기준이 없다")
        return
    M = np.array([v for _, v in rows])
    med = np.median(M, axis=0)
    bh = max(med[3] - med[1], 1e-6)          # 기준 밴드 높이(화면 비율)
    spread = (np.percentile(M, 75, axis=0) - np.percentile(M, 25, axis=0)) / bh

    print(f"  기준: 같은 기기 사람 라벨 {len(rows)}장의 중앙값")
    print(f"\n  {'변':<5}{'이 장':>9}{'기준':>9}{'벗어남':>10}{'기준 퍼짐(IQR)':>16}")
    order = (0, 1, 2, 3)
    dev = []
    for k in order:
        # 밖으로 나가면 +, 안으로 들어오면 - (밴드를 깎는 방향이 -)
        d = ((med[k] - p[k]) if k < 2 else (p[k] - med[k])) / bh
        dev.append(d)
        print(f"  {EDGES[k]:<5}{p[k]:>9.3f}{med[k]:>9.3f}{d:>+9.2f}h"
              f"{spread[k]:>14.2f}h")
    worst = int(np.argmin(dev))
    print(f"\n  가장 모자란 변: {EDGES[order[worst]]}  {dev[worst]:+.2f}h"
          f"   (기준 퍼짐 {spread[order[worst]]:.2f}h)")
    if dev[worst] < -spread[order[worst]] - 0.05:
        print("  -> 기준의 퍼짐을 넘어 안쪽으로 들어왔다. 눈으로 볼 것.")
    else:
        print("  -> 기준의 퍼짐 안이다. 이 자로는 짚을 것이 없다.")
    print("\n  판정이 아니라 의심이다 — 기준이 사람 라벨 "
          f"{len(rows)}장의 중앙값이다.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pid", nargs="?", default=None)
    ap.add_argument("--device", default=None, help="기기 전체를 훑는다")
    ap.add_argument("--worst", type=int, default=10)
    args = ap.parse_args()
    gm, src, devs, pred, ref = load_all()

    if args.pid:
        report(args.pid, gm, src, devs, pred, ref)
        return 0

    if not args.device:
        raise SystemExit("사진 id 나 --device 를 달라")
    rows = ref.get(args.device, [])
    if len(rows) < 2:
        raise SystemExit(f"{args.device} 라벨 {len(rows)}장 — 기준을 못 만든다")
    med = np.median(np.array([v for _, v in rows]), axis=0)
    bh = max(med[3] - med[1], 1e-6)
    out = []
    for pid, d in devs.items():
        if device_name(d) != args.device or pid not in pred or pid not in gm:
            continue
        p = _norm(pred[pid]["quad"], gm[pid])
        dv = [(med[0] - p[0]) / bh, (med[1] - p[1]) / bh,
              (p[2] - med[2]) / bh, (p[3] - med[3]) / bh]
        out.append((min(dv), EDGES[int(np.argmin(dv))], pid,
                    pid in {i for i, _ in rows}))
    out.sort()
    print(f"{args.device}  예측 {len(out)}장 · 기준 라벨 {len(rows)}장")
    print(f"{'가장 모자란 변':>14} {'벗어남':>8}  {'라벨':>4}  사진")
    for v, e, pid, has in out[:args.worst]:
        print(f"{e:>14} {v:>+7.2f}h  {'있음' if has else '없음':>4}  {pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
