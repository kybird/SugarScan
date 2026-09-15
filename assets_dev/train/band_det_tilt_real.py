# 기울기 예산 — 합성이 가르치는 기울기, 모델이 내는 기울기, 게이트가 허용하는 기울기.
#
# 배경(2026-09-15): 사람이 기종 화면에서 r2_40k 오버레이를 보고 「오버레이가
# 사각형인데 실촬은 삐뚤빼뚤이라 검출결과가 숫자를 자른다」고 보고했다.
# 그리는 쪽(devices.html drawPred)은 쿼드 네 점을 그대로 잇는다 — 사각형으로
# 보이는 것은 **예측이 축정렬**이라는 뜻이다.
#
# 실사진에는 기울기 정답이 없다. gmscreen_quads.jsonl(사람)도
# gmscreen_quads_oriented.jsonl(검출기)도 전 장이 0.00° 축정렬이다. 그래서
# 실사진으로는 기울기를 **영영 채점할 수 없다** — 설계로 넣는 수밖에 없다.
#
# 대신 셋을 나란히 인쇄한다:
#   1 합성 코퍼스가 실제로 담은 기울기 (cam_roll 이 만든 것)
#   2 그 모델이 실사진에 내는 기울기
#   3 게이트의 천장 — 사람 라벨이 전부 축정렬이므로, **정답을 기울기까지
#     완벽히 맞힌 예측**조차 축정렬 라벨과는 IoU 가 1 이 안 된다.
#       IoU_max = wh / ((w cos t + h sin t)(h cos t + w sin t))
#     이 값이 지금 게이트 수치보다 낮으면, 게이트는 검출 품질이 아니라
#     기울기 불일치를 재고 있는 것이다.
#
# 사용:
#   python band_det_tilt_real.py
#   python band_det_tilt_real.py --synth synth_r2_10000 --pred band_quads_pred.jsonl
import argparse
import json
from pathlib import Path

import numpy as np

from gm_quads import load_gm_quads
from band_exclusions import load_excluded

HERE = Path(__file__).resolve().parent


def tilt(q):
    """위변·아래변 평균 기울기(도). 시계방향 +."""
    q = np.asarray(q, float)
    a = np.degrees(np.arctan2(q[1, 1] - q[0, 1], q[1, 0] - q[0, 0]))
    b = np.degrees(np.arctan2(q[2, 1] - q[3, 1], q[2, 0] - q[3, 0]))
    return float((a + b) / 2)


def _span(q, i):
    q = np.asarray(q, float)
    return float(q[:, i].max() - q[:, i].min())


def ceiling(r, t_deg):
    """종횡비 h/w = r 인 밴드를 t 도 기울였을 때, 축정렬 라벨과의 IoU 상한."""
    t = np.radians(t_deg)
    return 1.0 * r / ((np.cos(t) + r * np.sin(t)) * (r * np.cos(t) + np.sin(t)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", default="synth_r2_10000")
    ap.add_argument("--pred", default="band_quads_pred.jsonl")
    ap.add_argument("--n", type=int, default=4000)
    args = ap.parse_args()

    # 1 합성이 담은 기울기
    m = HERE / args.synth / "manifest.jsonl"
    if m.exists():
        rows = [json.loads(l) for l in
                m.read_text(encoding="utf-8").splitlines()[:args.n] if l.strip()]
        s = np.abs([tilt(r["quad"]) for r in rows])
        print(f"1 합성 {args.synth}  n={len(s)}")
        print(f"   |기울기| median {np.median(s):.2f}°  p90 {np.percentile(s, 90):.2f}°"
              f"  max {s.max():.2f}°")
    else:
        print(f"1 합성 {args.synth} 없음 — 건너뜀")

    # 2 모델이 실사진에 내는 기울기
    gm, _ = load_gm_quads()
    ex = load_excluded()
    pred = {r["id"]: r for r in map(json.loads,
            (HERE / args.pred).read_text(encoding="utf-8").splitlines())}
    ck = sorted({r.get("ckpt") for r in pred.values() if r.get("ckpt")})
    p = np.abs([tilt(r["quad"]) for k, r in pred.items() if k not in ex])
    print(f"\n2 실사진 예측  {args.pred}  ckpt={ck}  n={len(p)}")
    print(f"   |기울기| median {np.median(p):.2f}°  p90 {np.percentile(p, 90):.2f}°"
          f"  max {p.max():.2f}°")

    # 3 게이트 천장 — 사람 라벨의 실제 종횡비로 계산한다
    hb = []
    for l in open(HERE / "band_boxes.jsonl", encoding="utf-8"):
        b = json.loads(l)
        if b["id"] in ex or "quad" not in b or b["id"] not in gm:
            continue
        G = gm[b["id"]]
        hb.append((_span(G, 0) / max(_span(G, 1), 1e-6),
                   _span(b["quad"], 1) / max(_span(b["quad"], 0), 1e-6)))
    hb = np.array(hb)
    print(f"\n3 게이트 천장 — 사람 밴드 라벨 {len(hb)}장의 종횡비로")
    print(f"   {'기울기':>6}  {'전체':>8} {'세로형':>8} {'가로형':>8}")
    groups = (("전체", np.ones(len(hb), bool)),
              ("세로형", hb[:, 0] <= 1.0), ("가로형", hb[:, 0] > 1.0))
    for t in (2, 4, 6, 8, 10, 12):
        cells = [np.median(ceiling(hb[g, 1], t)) for _, g in groups]
        print(f"   {t:>5}°  {cells[0]:>8.3f} {cells[1]:>8.3f} {cells[2]:>8.3f}")
    print("   = 기울기까지 정확히 맞힌 예측이 축정렬 사람 라벨과 낼 수 있는 IoU 최대값")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
