# **우리 상자가 숫자를 실제로 자르는가** — 남의 라벨을 믿지 않고 사진에서 잰다.
#
# 왜(2026-09-20 사람 지적: "왜 나한테 라벨링을 시켰는지 제대로 설명해"):
# Roboflow 의 좌-우 쏠림 +0.247 을 놓고 "라벨 규약 차이"라고 결론 내린 뒤
# 그것을 확인하는 일을 사람에게 넘겼다. 그런데 정작 알아야 할 것은 누구
# 라벨이 옳으냐가 아니라 **숫자가 잘렸느냐**이고, 그건 잉크가 답을 갖고 있다.
#
# 방법: READING 상자 주변을 넉넉히 잘라 **획(잉크)의 외접상자**를 찾는다.
# 검출이 아니라 **이미 주어진 영역 안에서** 찾는 것이라 쉬운 문제다
# (2026-09-19 에 포기한 잉크 추정은 영역 없이 하려던 것이라 실패했다).
#
#   1) 그레이 -> 국소 대비 정규화(CLAHE) -> Otsu
#   2) READING 상자 안에서 다수 화소가 밝으면 어두운 쪽이 획, 반대면 반대
#   3) 작은 덩어리(잡티)는 버린다 — 면적이 최대 덩어리의 8% 미만
#   4) 남은 덩어리의 외접상자 = 잉크 범위
#
# **자가 맞는지 먼저 본다**(--check): 통과한 장에서 잉크 범위가 READING
# 상자 안에 들어오는지. 안 들어오면 이 자가 틀린 것이므로 결과를 못 쓴다.
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from report_fail_mix import rows, classify, digit_cell, pad

HERE = Path(__file__).resolve().parent


def ink_bbox(img, gt, pad_r=0.25, dbg=None):
    """READING 상자 주변에서 획의 외접상자를 찾는다. 실패하면 None.

    첫 판(2026-09-20)은 잘라 낸 영역을 통째로 잉크로 잡았다 — 외접상자가
    정확히 잘라 낸 크기의 1.70배로 나왔다. 화면(LCD) 자체가 하나의 큰
    덩어리로 잡힌 것이다. 그래서 **덩어리를 거른다**:
      · 잘라 낸 가장자리에 닿은 것  -> 화면·몸통이다. 버린다.
      · 키가 상자 높이의 0.25 미만  -> 단위·날짜 같은 잔글씨. 버린다.
      · 키가 상자 높이의 1.30 초과  -> 테두리. 버린다.
      · READING 상자와 안 겹치는 것 -> 다른 자리의 무늬. 버린다.
    남은 것들의 합집합이 획의 범위다.
    """
    h, w = img.shape
    bw, bh = gt[2] - gt[0], gt[3] - gt[1]
    x0 = max(0, int(gt[0] - bw * pad_r)); x1 = min(w, int(gt[2] + bw * pad_r))
    y0 = max(0, int(gt[1] - bh * pad_r)); y1 = min(h, int(gt[3] + bh * pad_r))
    if x1 - x0 < 12 or y1 - y0 < 12:
        return None
    crop = cv2.createCLAHE(2.0, (8, 8)).apply(img[y0:y1, x0:x1])
    _, th = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ix0, iy0 = max(0, int(gt[0]) - x0), max(0, int(gt[1]) - y0)
    ix1, iy1 = int(gt[2]) - x0, int(gt[3]) - y0
    inner = th[iy0:iy1, ix0:ix1]
    if inner.size == 0:
        return None
    ink = (th == 0) if inner.mean() > 127 else (th == 255)
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    ch, cw = th.shape
    out = []
    for i in range(1, n):
        L, T = st[i, cv2.CC_STAT_LEFT], st[i, cv2.CC_STAT_TOP]
        W, H = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
        if L <= 0 or T <= 0 or L + W >= cw or T + H >= ch:
            continue                              # 가장자리에 닿음 = 화면/몸통
        if H < bh * 0.25 or H > bh * 1.30:
            continue                              # 잔글씨 / 테두리
        if L + W < ix0 or L > ix1 or T + H < iy0 or T > iy1:
            continue                              # READING 상자와 안 겹침
        out.append((L, T, L + W, T + H))
    if not out:
        return None
    a = np.array(out)
    if dbg is not None:
        dbg.append(len(out))
    return [x0 + a[:, 0].min(), y0 + a[:, 1].min(),
            x0 + a[:, 2].max(), y0 + a[:, 3].max()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="atone")
    ap.add_argument("--dir", default="_diag/tone")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--split", default="dev")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dump", default="",
                    help="장별 결과를 jsonl 로 — 웹툴 눈검사(/inkclip)가 읽는다")
    a = ap.parse_args()

    from eval_band_roboflow import population
    pop = {k: v[0] for k, v in population().items()}
    keep = set(json.loads((HERE / "rf_split.json")
                          .read_text(encoding="utf-8"))[a.split])
    rs = [r for r in rows(HERE / a.dir / f"roboflow_{a.arm}_s{a.seed}.jsonl")
          if r["id"] in keep and r.get("gt") and r.get("det")]
    if a.limit:
        rs = rs[:a.limit]

    stat = {}
    sane_in, sane_n = 0, 0
    dump = []
    for r in rs:
        p = pop.get(r["id"])
        if p is None:
            continue
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        ib = ink_bbox(img, r["gt"])
        cls = classify(r)
        if ib is None:
            stat.setdefault(cls, {"잉크실패": 0})
            stat[cls]["잉크실패"] = stat[cls].get("잉크실패", 0) + 1
            continue
        # 자 검사: 잉크가 READING 상자 안에 들어오는가 (약간의 여유 허용)
        g = r["gt"]
        mw, mh = (g[2]-g[0]) * 0.06, (g[3]-g[1]) * 0.06
        sane_n += 1
        sane = (ib[0] >= g[0]-mw and ib[1] >= g[1]-mh
                and ib[2] <= g[2]+mw and ib[3] <= g[3]+mh)
        if sane:
            sane_in += 1
        e = pad(r["pred"])
        cut = not (e[0] <= ib[0] and e[1] <= ib[1]
                   and e[2] >= ib[2] and e[3] >= ib[3])
        if a.dump:
            # 어느 변이 얼마나 모자란지도 같이 낸다 — 눈으로 볼 때
            # "어디가 잘렸다는 건지"를 바로 알 수 있어야 한다.
            short = {"왼": e[0] - ib[0], "위": e[1] - ib[1],
                     "오른": ib[2] - e[2], "아래": ib[3] - e[3]}
            dump.append({"id": r["id"], "cls": cls, "cut": bool(cut),
                         "sane": bool(sane),
                         "gt": [round(float(v), 1) for v in r["gt"]],
                         "digit": [round(float(v), 1) for v in digit_cell(r["gt"])],
                         "deploy": [round(float(v), 1) for v in e],
                         "ink": [round(float(v), 1) for v in ib],
                         "short": {k: round(float(v), 1)
                                   for k, v in short.items() if v > 0}})
        d = stat.setdefault(cls, {})
        d["n"] = d.get("n", 0) + 1
        d["잉크잘림"] = d.get("잉크잘림", 0) + int(cut)

    print(f"자 검사 — 잉크 범위가 READING 상자 안에 들어오는 비율 "
          f"{100*sane_in/max(1,sane_n):.1f}% (n={sane_n})")
    print("  낮으면 이 잉크 자가 틀린 것이다 — 아래 수치를 쓰지 말 것\n")
    print(f"  {'판정':<8}{'장수':>6}{'잉크가 잘린 장':>15}{'비율':>8}{'잉크실패':>9}")
    for cls in ("통과", "일부만", "딴 데"):
        d = stat.get(cls)
        if not d or not d.get("n"):
            continue
        print(f"  {cls:<8}{d['n']:>6}{d.get('잉크잘림', 0):>15}"
              f"{100*d.get('잉크잘림',0)/d['n']:>7.1f}%{d.get('잉크실패',0):>9}")
    if a.dump:
        q = HERE / a.dump
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text("".join(json.dumps(x, ensure_ascii=False) + chr(10)
                             for x in dump), encoding="utf-8")
        print()
        print(f"  -> {q}  ({len(dump)}장 · 잘림 "
              f"{sum(1 for x in dump if x['cut'])}장)")

    print("\n  읽는 법: `일부만`의 잉크잘림이 낮으면 **숫자는 안 잘렸다** —")
    print("  라벨 규약 차이로 떨어진 것이다. 높으면 진짜 잘린 것이다.")


if __name__ == "__main__":
    main()
