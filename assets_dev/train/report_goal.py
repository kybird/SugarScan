# 일차 목적 하나만 본다: **검출기가 밴드(숫자 칸)를 포함하여 검출하는가.**
#
# 사람 확인(2026-09-19): "검출기가 밴드를 포함하여 정확하게 검출하는게
# 일차목적이지". 그래서 주 지표는 **숫자 칸을 담는가**다. 면적 상한은
# 부차다 — 상자가 커도 숫자는 들어 있고, 리더는 BOX_MARGIN 여유 안에서
# 프레이밍이 흔들려도 견디게 학습됐다(build_cache_v2 주석).
#
# 숫자 칸은 사람 밴드 라벨에서 역산한다. 라벨 지침(webtool 밴드 모드)과
# 생성기(lcd_layout.BAND_MARGIN)가 같은 값을 쓴다 — 라벨을 사방으로
# 라벨높이의 BAND_MARGIN/(1+2*BAND_MARGIN) 만큼 줄이면 숫자 칸이다.
# 합성에서 검증(n=1000, 변 오차 중앙 +0.006 · p90 +0.017).
# **이것은 잉크 정답이 아니다.** 기울어진 외접상자의 역산이고 사람 여백
# 편차도 있다. 그래서 "숫자 판독 성공률"이라고 부르지 않는다.
#
# 배포 상자는 build_cache_v2.BOX_MARGIN 을 import 해서 쓴다.
#
# **봉인 시험셋**(rf_split.json)을 따로 낸다. test 로는 판정만 한다 —
# 조건 고르기·문턱 정하기에 쓰지 않는다.
import argparse
import json
from pathlib import Path

import numpy as np

from lcd_layout import BAND_MARGIN
from build_cache_v2 import BOX_MARGIN

HERE = Path(__file__).resolve().parent
K = BAND_MARGIN / (1.0 + 2.0 * BAND_MARGIN)


def rows(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def digit_cell(g):
    m = (g[3] - g[1]) * K
    return [g[0] + m, g[1] + m, g[2] - m, g[3] - m]


def pad(q):
    w, h = q[2] - q[0], q[3] - q[1]
    ml, mr, mt, mb = BOX_MARGIN
    return [q[0] - w * ml, q[1] - h * mt, q[2] + w * mr, q[3] + h * mb]


def score(rs, keep=None):
    """(원시 담음%, 배포 담음%, +면적<=2 %, 미검출 수, n)."""
    raw, dep, gate, miss = [], [], [], 0
    for r in rs:
        if keep is not None and r["id"] not in keep:
            continue
        if not r["det"]:
            miss += 1
            raw.append(False); dep.append(False); gate.append(False)
            continue
        if not r.get("gt"):
            continue
        d = digit_cell(r["gt"])
        e = pad(r["pred"])
        ga = max(1.0, (r["gt"][2]-r["gt"][0]) * (r["gt"][3]-r["gt"][1]))
        ea = max(0.0, e[2]-e[0]) * max(0.0, e[3]-e[1])
        cov = lambda b: (b[0] <= d[0] and b[1] <= d[1]
                         and b[2] >= d[2] and b[3] >= d[3])
        raw.append(cov(r["pred"])); dep.append(cov(e))
        gate.append(cov(e) and ea / ga <= 2.0)
    n = len(raw)
    if not n:
        return None
    return (100*np.mean(raw), 100*np.mean(dep), 100*np.mean(gate), miss, n)


def block(title, paths, keep=None):
    vals = [score(rows(p), keep) for p in paths]
    vals = [v for v in vals if v]
    if not vals:
        return
    a = np.array([[v[0], v[1], v[2], v[3]] for v in vals], float)
    print(f"  {title:<28}{a[:,1].mean():>8.1f}%{a[:,1].std(ddof=1) if len(a)>1 else 0:>7.2f}"
          f"{a[:,0].mean():>9.1f}%{a[:,2].mean():>9.1f}%{a[:,3].mean():>9.1f}"
          f"{vals[0][4]:>7}{len(vals):>6}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="bg:_diag/band_real,aug:_diag/audit")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    sp = json.loads((HERE / "rf_split.json").read_text(encoding="utf-8")) \
        if (HERE / "rf_split.json").exists() else None

    print("일차 목적 — **배포 상자가 숫자 칸을 담는가** (사람 라벨에서 역산)")
    print(f"  {'':<28}{'배포담음':>8}{'±SD':>7}{'원시':>9}{'+면적≤2':>9}"
          f"{'미검출':>9}{'n':>7}{'시드':>6}")
    for spec in a.arms.split(","):
        arm, d = spec.split(":")
        d = HERE / d
        print(f"\n[{arm}]")
        block("Datumo 272 (개발)",
              [d / f"{arm}_s{s}.jsonl" for s in seeds])
        rf = [d / f"roboflow_{arm}_s{s}.jsonl" for s in seeds]
        if sp:
            block("Roboflow 개발", rf, set(sp["dev"]))
            block("Roboflow **봉인 시험**", rf, set(sp["test"]))
        else:
            block("Roboflow 전량", rf)

    print("\n  주의: 세 줄은 정답 규약이 다른 코퍼스다. 행 사이를 정확도로")
    print("  비교하지 않는다. **봉인 시험은 판정에만** 쓴다.")


if __name__ == "__main__":
    main()
