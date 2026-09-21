# **밴드가 특징맵에서 몇 칸인가**로 층을 갈라 성적을 낸다.
#
# 왜(2026-09-20, §21.5): 실패가 밴드 크기와 함께 움직이는데, 크기를 화면
# 비율로 보면 왜 거기서 무너지는지가 안 보인다. /16 격자의 **칸 수**로 보면
# 2.5칸 밑에 절벽이 있다 — objectness 후보가 몇 개 없고 그 칸 중심에서
# 네 변을 전부 회귀해야 하는 구간이다.
#
# **층은 416 기준으로 고정한다.** 팔마다 입력 크기가 달라도 층이 같아야
# 맞댈 수 있다. 층은 사진의 속성이지 모델의 속성이 아니다 — 팔의 입력
# 크기로 층을 나누면 같은 사진이 팔마다 다른 층에 들어가 비교가 깨진다.
#
# 게이트를 함께 낸다. '담음' 단독은 상수 상자가 54.3% 를 받는 물렁한 자다
# (§21.1). 담음이 올라도 게이트가 내려가면 이득이 아니다.
import argparse
import json
from pathlib import Path

import numpy as np

from report_fail_mix import rows, classify, digit_cell, pad, HERE

STRIDE = 16
REF_SIZE = 416          # 층을 정하는 기준 입력. 팔이 달라도 이 값으로 나눈다.
EDGES = (2.5, 3.5, 5.0, 8.0)


def cells(r, size=REF_SIZE):
    """밴드가 /16 특징맵에서 차지하는 세로 칸 수 (레터박스 기준)."""
    rr = min(size / r["ow"], size / r["oh"])
    return (r["gt"][3] - r["gt"][1]) * rr / STRIDE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="atone:_diag/tone,abig:_diag/fix7")
    ap.add_argument("--seeds", default="0,1,2,3")
    ap.add_argument("--tau", type=float, default=2.0)
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    dev = set(json.loads((HERE / "rf_split.json")
                         .read_text(encoding="utf-8"))["dev"])

    names = []
    per = {}
    for spec in a.arms.split(","):
        nm, d = spec.split(":")
        names.append(nm)
        acc = {}
        for s in seeds:
            for r in rows(HERE / d / f"roboflow_{nm}_s{s}.jsonl"):
                if r["id"] not in dev or not r.get("gt"):
                    continue
                c = classify(r)
                if not c:
                    continue
                ok = c == "통과"
                gate = False
                if r.get("det"):
                    e = pad(r["pred"])
                    g = r["gt"]
                    ga = max(1.0, (g[2]-g[0]) * (g[3]-g[1]))
                    ar = max(0.0, e[2]-e[0]) * max(0.0, e[3]-e[1]) / ga
                    gate = ok and ar <= a.tau
                acc.setdefault(r["id"], [cells(r), [], [], []])
                acc[r["id"]][1].append(ok)
                acc[r["id"]][2].append(gate)
                acc[r["id"]][3].append(c == "딴 데")
        per[nm] = acc

    base = per[names[0]]
    ids = sorted(set.intersection(*[set(per[n]) for n in names]))
    cl = np.array([base[i][0] for i in ids])
    lab = ["  ~2.5", "2.5~3.5", "3.5~5", "5~8", "8~"]
    b = np.digitize(cl, EDGES)

    print(f"416 기준 /16 격자의 밴드 세로 칸 수로 나눈 층 "
          f"(Roboflow 개발 {len(ids)}장, 시드 {len(seeds)})")
    print(f"  층은 사진의 속성이다 — 팔의 입력 크기와 무관하게 같은 층이다.")
    hdr = "".join(f"{n:>22}" for n in names)
    print(f"\n  {'세로 칸 수':<10}{'n':>5}{hdr}")
    print(f"  {'':<10}{'':>5}" + "".join(f"{'통과 / 게이트 / 딴데':>22}"
                                         for _ in names))
    for k in range(5):
        m = b == k
        if m.sum() < 5:
            continue
        cells_txt = ""
        for n in names:
            A = per[n]
            ok = 100*np.mean([np.mean(A[i][1]) for i in np.array(ids)[m]])
            gt = 100*np.mean([np.mean(A[i][2]) for i in np.array(ids)[m]])
            dj = 100*np.mean([np.mean(A[i][3]) for i in np.array(ids)[m]])
            cells_txt += f"{ok:>7.1f}{gt:>7.1f}{dj:>8.1f}"
        print(f"  {lab[k]:<10}{m.sum():>5}{cells_txt}")

    print(f"\n  전체")
    cells_txt = ""
    for n in names:
        A = per[n]
        ok = 100*np.mean([np.mean(A[i][1]) for i in ids])
        gt = 100*np.mean([np.mean(A[i][2]) for i in ids])
        dj = 100*np.mean([np.mean(A[i][3]) for i in ids])
        cells_txt += f"{ok:>7.1f}{gt:>7.1f}{dj:>8.1f}"
    print(f"  {'':<10}{len(ids):>5}{cells_txt}")
    print("\n  노린 층은 **2.5칸 미만**이다. 거기가 안 움직였는데 전체가")
    print("  올랐으면 기전 설명이 틀린 것이므로 그렇게 적는다.")


if __name__ == "__main__":
    main()
