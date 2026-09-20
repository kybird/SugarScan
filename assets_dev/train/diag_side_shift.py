# 예측 상자가 **한쪽으로 쏠려 있는가** — 합성 안에서도 그런가, 실촬에서만 그런가.
#
# 왜: 2026-09-20 톤 팔 이후 남은 주 실패는 `일부만`(잘림)이고, 해부해 보니
# 모자란 변이 평균 1.12개로 **거의 항상 한 변**이며 그 변이 오른쪽인 경우가
# Roboflow 52% · Datumo 84% 였다. 라벨 주체가 다른 두 코퍼스에서 같은 쪽으로
# 쏠렸다 — 코퍼스 특성이 아니라 우리 쪽 문제라는 뜻이다.
#
# 그런데 "우리 쪽"이 둘로 갈린다. 처방이 정반대다:
#   합성 안에서도 쏠려 있다   -> 손실/디코드의 문제. 학습 방식을 고친다.
#   합성은 반듯한데 실촬만    -> 도메인 문제. 합성기가 안 보여 준 것이 있다.
#
# 부호 규약은 diag_band_sides.py 와 같다: +면 예측이 정답보다 **넓다**.
# 정규화는 정답 상자의 해당 변 길이. 여기서는 **실패만이 아니라 검출 전체**를
# 본다 — 합성은 게이트가 100% 라 실패만 보면 표본이 없다.
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def rows(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def slack(rs):
    """검출된 장마다 네 변의 여유. 정답은 각 코퍼스의 밴드 상자다."""
    out = []
    for r in rs:
        if not r.get("det") or not r.get("gt"):
            continue
        g, q = r["gt"], r["pred"]
        gw = max(1.0, g[2] - g[0])
        gh = max(1.0, g[3] - g[1])
        out.append([(g[0] - q[0]) / gw, (g[1] - q[1]) / gh,
                    (q[2] - g[2]) / gw, (q[3] - g[3]) / gh])
    return np.asarray(out) if out else np.zeros((0, 4))


def synth_slack(rs):
    """합성은 gt 가 아니라 같은 뜻의 키 이름을 쓴다."""
    out = []
    for r in rs:
        if not r.get("det"):
            continue
        g, q = r["gt"], r["pred"]
        gw = max(1.0, g[2] - g[0])
        gh = max(1.0, g[3] - g[1])
        out.append([(g[0] - q[0]) / gw, (g[1] - q[1]) / gh,
                    (q[2] - g[2]) / gw, (q[3] - g[3]) / gh])
    return np.asarray(out) if out else np.zeros((0, 4))


def show(title, v):
    if not len(v):
        print(f"  {title:<22} 표본 없음")
        return
    med = np.median(v, axis=0)
    neg = 100.0 * np.mean(v < 0, axis=0)
    # 좌우 비대칭: 왼쪽 여유 − 오른쪽 여유. 0 이면 가운데에 놓인 것이다.
    lr = np.median(v[:, 0] - v[:, 2])
    tb = np.median(v[:, 1] - v[:, 3])
    print(f"  {title:<22}" + "".join(f"{m:>+9.3f}" for m in med)
          + f"{lr:>+11.3f}{tb:>+9.3f}{len(v):>8}")
    print(f"  {'  (그 변이 모자란 %)':<22}" + "".join(f"{x:>8.0f}%" for x in neg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="atone")
    ap.add_argument("--dir", default="_diag/tone")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    d = HERE / a.dir
    sp = HERE / "rf_split.json"
    dev = set(json.loads(sp.read_text(encoding="utf-8"))["dev"]) \
        if sp.exists() else None

    print(f"변별 여유 — +면 예측이 정답보다 넓다 · 조건 {a.arm} · 시드 {len(seeds)}개")
    print(f"  {'모집단':<22}{'왼':>9}{'위':>9}{'오른':>9}{'아래':>9}"
          f"{'좌−우 쏠림':>11}{'상−하':>9}{'n':>8}")

    v = np.vstack([synth_slack(rows(d / f"synth_{a.arm}_s{s}.jsonl"))
                   for s in seeds])
    show("합성 홀드아웃 VC", v)

    v = np.vstack([slack(rows(d / f"{a.arm}_s{s}.jsonl")) for s in seeds])
    show("Datumo 272", v)

    rf = []
    for s in seeds:
        rs = rows(d / f"roboflow_{a.arm}_s{s}.jsonl")
        if dev is not None:
            rs = [r for r in rs if r["id"] in dev]
        rf.append(slack(rs))
    show("Roboflow 개발 586", np.vstack(rf))

    print()
    print("  읽는 법: **좌−우 쏠림**이 0 에서 멀면 상자가 한쪽으로 밀린 것이다.")
    print("  합성 줄이 0 근처인데 실촬 줄만 크면 도메인 문제 — 합성기가 보여")
    print("  주지 않은 것이 있다는 뜻이고, 손실을 만져도 낫지 않는다.")


if __name__ == "__main__":
    main()
