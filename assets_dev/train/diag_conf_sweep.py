# 검출 문턱(conf)을 쓸어 본다 — 검출 실패가 문턱 탓인가.
#
# 왜(2026-09-19): 절차적 배경 조건이 상자 품질은 크게 올렸는데 **검출 실패**가
# 늘었다(코퍼스 B 시드당 3.4 -> 34.8장, Roboflow 1.7 -> 194.5장). 검출 실패는
# 값이 아예 안 나오는 것이라 제품에서 수동 입력으로 떨어진다. 15% 는 못 낸다.
#
# 이 자가 답하는 것: **그 실패가 문턱 0.25 때문인가, 모델이 정말 못 찾는가.**
#
# 이 모델은 물체가 하나라 디코드가 **전역 argmax 하나**다(NMS 없음). 그래서
# 문턱을 낮춰도 상자가 늘지 않는다 — "검출 없음"이 "검출 있음"으로 바뀔 뿐이다.
# 오탐이 늘어나는 구조가 아니므로, 물어야 할 것은 하나다: **낮은 점수로 나온
# 상자가 쓸 만한가.**
#
# 그래서 문턱마다 검출률과 **게이트 통과율을 함께** 본다. 검출률만 보면
# 문턱을 0 으로 내리는 것이 언제나 이긴다 — 쓸 수 없는 답이다.
#
# 게이트는 배포 프레이밍 규약(build_cache_v2.BOX_MARGIN)을 적용한 것이다.
# 규약을 빼고 재면 이 계열의 성적을 체계적으로 낮게 본다(2026-09-19).
#
# 사용: python diag_conf_sweep.py --arms bce,bg
import argparse
import json
from pathlib import Path

import numpy as np

from build_cache_v2 import BOX_MARGIN

HERE = Path(__file__).resolve().parent
REAL = HERE / "_diag" / "band_real"
UP = HERE.parent / "upstream" / "datacluster-glucometer-ocr"


def rows(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def deploy_ok(r, tau):
    """배포 규약을 적용한 뒤 게이트를 통과하는가 (정답이 있는 코퍼스)."""
    q, gt = r["pred"], r["gt"]
    w, h = q[2] - q[0], q[3] - q[1]
    ml, mr, mt, mb = BOX_MARGIN
    e = [q[0] - w * ml, q[1] - h * mt, q[2] + w * mr, q[3] + h * mb]
    ga = max(1.0, (gt[2] - gt[0]) * (gt[3] - gt[1]))
    return (e[0] <= gt[0] and e[1] <= gt[1] and e[2] >= gt[2] and e[3] >= gt[3]
            and max(0.0, e[2]-e[0]) * max(0.0, e[3]-e[1]) / ga <= tau)


def sweep_a(arms, seeds, tau, confs):
    print(f"코퍼스 A (272장, 사람 밴드 라벨) — BOX_MARGIN={BOX_MARGIN} 적용")
    print(f"  {'조건':<6}{'conf':>7}{'검출률':>9}{'게이트':>9}"
          f"{'검출된 것 중 게이트':>20}")
    for arm in arms:
        for c in confs:
            det, gate, cond = [], [], []
            for s in seeds:
                rs = rows(REAL / f"{arm}_s{s}.jsonl")
                if not rs:
                    continue
                d = [r["score"] >= c for r in rs]
                g = [(r["score"] >= c) and deploy_ok(r, tau) for r in rs]
                det.append(100*np.mean(d)); gate.append(100*np.mean(g))
                cond.append(100*np.sum(g)/max(1, np.sum(d)))
            if det:
                print(f"  {arm:<6}{c:>7.2f}{np.mean(det):>8.1f}%"
                      f"{np.mean(gate):>8.1f}%{np.mean(cond):>19.1f}%")
    print()


def sweep_b(arms, seeds, confs):
    """코퍼스 B — 밴드 정답이 없다. **기기 안에 드는 비율**만 본다."""
    from eval_band_real import device_boxes
    dev = device_boxes(UP / "Annotations")
    print("코퍼스 B (CC0 238장) — **밴드 정확도가 아니다**. 기기 밖을 무는 실패만")
    print(f"  {'조건':<6}{'conf':>7}{'검출률':>9}{'≥90% 기기 안':>14}"
          f"{'검출된 것 중':>14}")
    for arm in arms:
        for c in confs:
            det, inb, cond = [], [], []
            for s in seeds:
                rs = rows(REAL / f"datacluster_{arm}_s{s}.jsonl")
                if not rs:
                    continue
                d, ok = [], []
                for r in rs:
                    hit = r["score"] >= c
                    d.append(hit)
                    dd = dev.get(r["id"].split("/", 1)[-1])
                    if not hit or dd is None:
                        ok.append(False)
                        continue
                    p = r["pred"]
                    pa = max(0.0, p[2]-p[0]) * max(0.0, p[3]-p[1])
                    ix = max(0.0, min(p[2], dd[2]) - max(p[0], dd[0]))
                    iy = max(0.0, min(p[3], dd[3]) - max(p[1], dd[1]))
                    ok.append(pa > 0 and ix * iy / pa >= 0.9)
                det.append(100*np.mean(d)); inb.append(100*np.mean(ok))
                cond.append(100*np.sum(ok)/max(1, np.sum(d)))
            if det:
                print(f"  {arm:<6}{c:>7.2f}{np.mean(det):>8.1f}%"
                      f"{np.mean(inb):>13.1f}%{np.mean(cond):>13.1f}%")
    print()


def scores(arms, seeds):
    """점수 분포 — 실패가 문턱 바로 밑에 몰려 있는가."""
    print("점수 분포 (코퍼스 B, 8시드 합산)")
    for arm in arms:
        v = []
        for s in seeds:
            v += [r["score"] for r in rows(REAL / f"datacluster_{arm}_s{s}.jsonl")]
        v = np.asarray(v)
        if not v.size:
            continue
        print(f"  {arm:<6} p05 {np.percentile(v,5):.3f} p10 {np.percentile(v,10):.3f}"
              f" p25 {np.percentile(v,25):.3f} 중앙 {np.median(v):.3f}"
              f" | 0.25 미만 {100*(v<0.25).mean():.1f}%"
              f" · 0.05~0.25 구간 {100*((v>=0.05)&(v<0.25)).mean():.1f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="bce,bg")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--tau", type=float, default=2.0)
    ap.add_argument("--conf", default="0.25,0.15,0.10,0.05,0.02")
    a = ap.parse_args()
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    seeds = [int(x) for x in a.seeds.split(",")]
    confs = [float(x) for x in a.conf.split(",")]
    scores(arms, seeds)
    print()
    sweep_a(arms, seeds, a.tau, confs)
    sweep_b(arms, seeds, confs)
    print("읽는 법: 문턱을 낮춰 **검출률과 게이트가 같이** 오르면 문턱 문제다.")
    print("검출률만 오르고 게이트가 안 오르면 모델이 정말 못 찾는 것이고,")
    print("문턱을 내리는 것은 못 읽을 상자를 읽겠다고 내보내는 셈이다.")


if __name__ == "__main__":
    main()
