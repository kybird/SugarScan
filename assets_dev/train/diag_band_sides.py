# 예측이 정답 상자에 **어느 변에서 얼마나** 모자라는가.
#
# 왜(2026-09-19 사람 지적): "이전에 추론에서 검출결과가 숫자에 너무 바싹 붙여서
# 나와서 숫자가 잘리는 현상이 있어서 검출기에 여백을 충분히 주는 결정을 한 적이
# 있다. 그것의 영향인지 봐라."
#
# 그 여백은 두 겹이다.
#   BAND_MARGIN = 0.10      정답 쿼드가 숫자 필드를 넘어 감싸는 갭(lcd_layout).
#                           2026-09-15 에 숫자가 잘리는 현상을 보고 둔 안전 여유다.
#   기울기 부풀림 중앙 1.331  정답 상자는 **기울어진 쿼드의 축정렬 외접상자**라
#                           회전을 ±25° 로 넓힌 뒤 밴드보다 중앙 33% 크다
#                           (SPEC §7-1·§9.3).
#
# 절차적 배경 조건이 상자를 조였을 때(면적비 1.72 -> 1.09) 무너진 것이 이
# 여백인지, 그리고 **어느 변**인지를 가른다. 가르는 이유: 처방이 다르다.
#   사방이 고르게 모자라면   -> 여백을 통째로 못 배운 것. 추론 때 부풀리면 된다.
#   모서리/한두 변만 모자라면 -> 기울기 외접상자를 못 맞힌 것. §7-1 의 문제다.
#
# 부호 규약: +면 예측이 정답보다 **넓다**(여유 있음), −면 모자란다.
# 정규화는 정답 상자의 해당 변 길이로 한다 — 무차원이라 장마다 맞댈 수 있다.
#
# 사용: python diag_band_sides.py --arms bce,bg --seeds 0,1,2,3,4,5,6,7
import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REAL = HERE / "_diag" / "band_real"
BANDS = HERE / "band_boxes.jsonl"


def tilt_inflation():
    """사람 밴드 라벨의 **기울기 부풀림** — 축정렬 외접상자 / 쿼드 실면적.

    실촬 정답에도 합성과 같은 부풀림이 있는지 본다. 1.0 이면 반듯한 라벨이고,
    크면 기울어진 밴드를 축정렬 상자로 감싼 만큼 상자가 밴드가 아닌 것을
    품고 있다는 뜻이다.
    """
    out = []
    for line in BANDS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        j = json.loads(line)
        q = j.get("quad")
        if not q:
            continue
        a = np.asarray(q, float)
        bb = (a[:, 0].max()-a[:, 0].min()) * (a[:, 1].max()-a[:, 1].min())
        # 쿼드 실면적 (신발끈 공식)
        x, y = a[:, 0], a[:, 1]
        qa = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
        if qa > 1:
            out.append(bb / qa)
    v = np.asarray(out)
    print(f"사람 밴드 라벨의 기울기 부풀림 (외접상자/쿼드면적) n={len(v)}")
    print(f"  중앙 {np.median(v):.3f} · p90 {np.percentile(v,90):.3f} "
          f"· 최대 {v.max():.3f}")
    print(f"  합성 정답의 부풀림은 중앙 1.331 (SPEC §9.3) — 맞대어 읽을 것")
    return v


def sides(arms, seeds):
    print(f"\n예측 − 정답, 변별 여유 (정답 변 길이로 정규화 · +면 예측이 넓다)")
    print(f"  {'조건':<7}{'왼':>9}{'위':>9}{'오른':>9}{'아래':>9}"
          f"{'모자란 변 수':>13}{'최악 변':>10}")
    for arm in arms:
        L, T, R, B, nneg, worst = [], [], [], [], [], []
        for s in seeds:
            p = REAL / f"{arm}_s{s}.jsonl"
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                if not r["det"] or not r.get("gt"):
                    continue
                g, q = r["gt"], r["pred"]
                gw = max(1.0, g[2]-g[0]); gh = max(1.0, g[3]-g[1])
                l = (g[0]-q[0])/gw; t = (g[1]-q[1])/gh
                rr = (q[2]-g[2])/gw; b = (q[3]-g[3])/gh
                L.append(l); T.append(t); R.append(rr); B.append(b)
                nneg.append(sum(1 for v in (l, t, rr, b) if v < 0))
                worst.append(min(l, t, rr, b))
        f = lambda v: f"{np.median(v):+.3f}"
        print(f"  {arm:<7}{f(L):>9}{f(T):>9}{f(R):>9}{f(B):>9}"
              f"{np.mean(nneg):>12.2f}개{np.median(worst):>+10.3f}")
    print("  읽는 법: 네 변이 고르게 음수면 **여백을 통째로 못 배운 것**이다 —")
    print("  추론 때 부풀리면 회수된다. 한두 변만 크게 음수면 기울기 외접상자를")
    print("  못 맞힌 것이고, 그건 §7-1 의 문제라 부풀려도 안 낫는다.")


def recover(arms, seeds, tau, grows):
    """**추론 때 상자를 부풀리면** 게이트가 얼마나 회수되는가.

    배포에서 실제로 할 수 있는 처방이다(lcd_layout 주석: "밴드를 실제로
    키우려면 … 검출기 출력을 추론 때 부풀린다"). 면적비 상한 τ 는 그대로
    적용한다 — 부풀려서 담는 대신 상자가 커지는 대가를 같이 본다.
    """
    print(f"\n추론 때 사방으로 부풀렸을 때의 게이트 (밴드 전체 포함 ∧ 면적비<=τ={tau})")
    print("  **배포에서 할 수 있는 처방이다** — 학습을 다시 하지 않는다")
    hdr = "".join(f"{g:>10.0%}" for g in grows)
    print(f"  {'조건':<7}{'부풀림 0%':>11}{hdr}")
    for arm in arms:
        cells = []
        for g in [0.0] + list(grows):
            per = []
            for s in seeds:
                p = REAL / f"{arm}_s{s}.jsonl"
                if not p.exists():
                    continue
                ok = []
                for line in p.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    if not r["det"] or not r.get("gt"):
                        ok.append(False)
                        continue
                    q = r["pred"]
                    w, h = q[2]-q[0], q[3]-q[1]
                    e = [q[0]-w*g/2, q[1]-h*g/2, q[2]+w*g/2, q[3]+h*g/2]
                    gt = r["gt"]
                    ga = max(1.0, (gt[2]-gt[0])*(gt[3]-gt[1]))
                    inside = (e[0] <= gt[0] and e[1] <= gt[1]
                              and e[2] >= gt[2] and e[3] >= gt[3])
                    ar = max(0.0, e[2]-e[0]) * max(0.0, e[3]-e[1]) / ga
                    ok.append(inside and ar <= tau)
                if ok:
                    per.append(100*np.mean(ok))
            cells.append(np.mean(per) if per else float("nan"))
        print(f"  {arm:<7}{cells[0]:>10.1f}%"
              + "".join(f"{c:>9.1f}%" for c in cells[1:]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="bce,bg")
    ap.add_argument("--seeds", default="0,1,2,3,4,5,6,7")
    ap.add_argument("--tau", type=float, default=2.0)
    ap.add_argument("--grow", default="0.1,0.2,0.3,0.5")
    a = ap.parse_args()
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    seeds = [int(x) for x in a.seeds.split(",")]
    tilt_inflation()
    sides(arms, seeds)
    recover(arms, seeds, a.tau, [float(x) for x in a.grow.split(",")])


if __name__ == "__main__":
    main()
