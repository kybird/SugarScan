# 이 표본으로 **무엇을 가를 수 있는가**. 실험을 걸기 전에 본다.
#
# 왜(2026-09-20 사람 지적): "왜 16번돌려 뭘구분할수있지?"
# 시드를 늘리는 것과 사진을 늘리는 것은 **다른 잡음**을 줄인다. 어느 쪽이
# 지배적인지 보지 않고 시드만 늘리면 시간만 쓰고 아무것도 못 가른다.
#
# 분산을 둘로 가른다.
#   시드 잡음   같은 사진, 다른 시드. 시드를 늘리면 1/sqrt(k) 로 준다.
#   사진 잡음   같은 시드, 다른 사진 표본. **시드를 아무리 늘려도 안 준다.**
#
# 그리고 짝비교의 실질 한계를 낸다. 팔 B 가 팔 A 의 실패 사진 k 장을 고쳤을
# 때 95% 구간이 0 을 지나지 않으려면 대략 sqrt(k) > 1.96, 즉 **k >= 4 장**이
# 뒤집혀야 한다(McNemar 의 정규 근사). 실패가 애초에 4장이 안 되면 **완전히
# 고쳐도 유의하지 않다** — 그 지표는 그 모집단에서 잴 수 없는 것이다.
import argparse
import json
from pathlib import Path

import numpy as np

from report_fail_mix import (CLASSES, rows, classify, HERE)


def load(d, arm, seeds, pfx, keep):
    out = []
    for s in seeds:
        rs = rows(HERE / d / (pfx + f"{arm}_s{s}.jsonl"))
        m = {}
        for r in rs:
            if keep is not None and r["id"] not in keep:
                continue
            c = classify(r)
            if c:
                m[r["id"]] = c
        if m:
            out.append(m)
    return out


def decompose(ss, cls):
    """시드 잡음과 사진 잡음을 갈라 낸다 (단위 %포인트)."""
    ids = sorted(ss[0])
    M = np.array([[m[i] == cls for i in ids] for m in ss], float)  # 시드 x 사진
    per_seed = 100.0 * M.mean(axis=1)
    seed_sd = per_seed.std(ddof=1) if len(per_seed) > 1 else 0.0
    # 사진 잡음: 시드 평균 벡터를 사진에 대해 붓스트랩한 표준편차.
    p = M.mean(axis=0)
    n = len(p)
    photo_sd = 100.0 * np.sqrt(max(p.mean() * (1 - p.mean()), 1e-12) / n)
    return per_seed.mean(), seed_sd, photo_sd, n, p.sum()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="atone")
    ap.add_argument("--dir", default="_diag/tone")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    sp = json.loads((HERE / "rf_split.json").read_text(encoding="utf-8"))

    pops = [("Datumo 272", "", None),
            ("Roboflow 개발 586", "roboflow_", set(sp["dev"])),
            ("Roboflow 봉인 687", "roboflow_", set(sp["test"])),
            ("Roboflow 전량 1273", "roboflow_", None)]

    print(f"조건 {a.arm} · 시드 {len(seeds)}개 — **무엇을 가를 수 있는가**")
    print(f"  {'모집단':<20}{'분류':<8}{'비율':>8}{'실패 장수':>10}"
          f"{'시드잡음':>9}{'사진잡음':>9}{'지배':>7}{'판정':>28}")
    for title, pfx, keep in pops:
        ss = load(a.dir, a.arm, seeds, pfx, keep)
        if not ss:
            continue
        for cls in ("일부만", "딴 데"):
            mean, ssd, psd, n, k = decompose(ss, cls)
            k8 = ssd / np.sqrt(len(ss))          # 시드 8개로 줄인 뒤
            dom = "사진" if psd > k8 else "시드"
            if k < 4:
                v = f"**완전히 고쳐도 못 가른다** ({k:.0f}장)"
            elif k < 8:
                v = f"거의 다 고쳐야 갈린다 (>={4:.0f}/{k:.0f}장)"
            else:
                v = f"{4/k:.0%} 이상 고치면 갈린다 ({k:.0f}장 중 4장)"
            print(f"  {title:<20}{cls:<8}{mean:>7.2f}%{k:>10.0f}"
                  f"{k8:>9.3f}{psd:>9.3f}{dom:>7}{v:>28}")

    print()
    print("  시드잡음은 **시드 수로 나눈 뒤**의 값이다(SD/sqrt(k)). 사진잡음보다")
    print("  작으면 시드를 더 늘려도 소용없다 — 사진을 늘려야 한다.")
    print("  판정 칸은 짝비교에서 몇 장이 뒤집혀야 95% 구간이 0 을 벗어나는가다.")


if __name__ == "__main__":
    main()
