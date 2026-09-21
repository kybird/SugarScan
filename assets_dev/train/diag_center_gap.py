# **혈당기가 화면 어디에 있는가** — 학습 코퍼스와 실촬이 다른가.
#
# 왜(2026-09-20 사람 관찰): "테스트 실촬을 보면 혈당기가 화면구석에 있는
# 경향이 있다 화면중앙이아니라. 모델의 예측은 배경이 어떻게 생겼든지간에
# 화면 가운데에 위치한다".
#
# 두 주장을 따로 잰다. 한쪽이 맞아도 다른 쪽은 틀릴 수 있다.
#   ① 코퍼스가 실촬보다 가운데로 쏠려 있는가
#   ② 모델 예측이 **정답과 무관하게** 가운데에 붙는가
#
# ②를 보려면 정답이 중앙에서 먼 장만 떼어 봐야 한다. 전체 평균으로는
# 가려진다 — 중앙 근처 장이 다수라 평균이 중앙으로 끌린다.
#
# 좌표는 레터박스 416 정규화다. 사진 크기가 제각각이라 원본 좌표로는 못 맞댄다.
# **증강을 켠 뒤의 분포**도 같이 낸다 — 모델이 실제로 보는 것은 그쪽이다.
import argparse
import json
from pathlib import Path

import numpy as np

from report_fail_mix import rows, classify, HERE
from diag_prior_memo import lb_norm, cwh


def stat(nm, A):
    c = np.hypot(A[:, 0] - 0.5, A[:, 1] - 0.5)
    print(f"  {nm:<24}{A[:,0].mean():>8.3f}{A[:,0].std():>7.3f}"
          f"{A[:,1].mean():>9.3f}{A[:,1].std():>7.3f}"
          f"{np.median(c):>11.3f}{np.percentile(c,90):>9.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="atone")
    ap.add_argument("--dir", default="_diag/tone")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--data", default="synth_coco/TC")
    ap.add_argument("--ann", default="instances_curve_07998.json")
    ap.add_argument("--aug-n", type=int, default=1500)
    a = ap.parse_args()

    j = json.loads((HERE / a.data / "annotations" / a.ann)
                   .read_text(encoding="utf-8"))
    wh = {im["id"]: (im["width"], im["height"]) for im in j["images"]}
    T = np.array([cwh(lb_norm([an["bbox"][0], an["bbox"][1],
                               an["bbox"][0] + an["bbox"][2],
                               an["bbox"][1] + an["bbox"][3]],
                              *wh[an["image_id"]]))
                  for an in j["annotations"]])

    dev = set(json.loads((HERE / "rf_split.json")
                         .read_text(encoding="utf-8"))["dev"])
    G, P, CL = [], [], []
    for r in rows(HERE / a.dir / f"roboflow_{a.arm}_s{a.seed}.jsonl"):
        if r["id"] not in dev or not r.get("gt") or not r.get("det"):
            continue
        G.append(cwh(lb_norm(r["gt"], r["ow"], r["oh"])))
        P.append(cwh(lb_norm(r["pred"], r["ow"], r["oh"])))
        CL.append(classify(r))
    G, P, CL = np.array(G), np.array(P), np.array(CL)

    print("레터박스 416 정규화 · 밴드 중심 (0.5,0.5 = 화면 한가운데)")
    print(f"  {'':24}{'중심x':>8}{'SD':>7}{'중심y':>9}{'SD':>7}"
          f"{'중심거리 중앙':>11}{'p90':>9}")
    stat("학습 코퍼스 정답", T)
    if a.aug_n:
        from train_band import CocoBand
        ds = CocoBand(a.data, a.ann, 416, 1, 0.0, True)
        rng = np.random.default_rng(7)
        A = []
        for i in rng.integers(0, len(ds), a.aug_n):
            _, b = ds[int(i)]
            b = np.asarray(b, float) / 416.0
            A.append([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])
        stat("**증강 뒤** (모델이 봄)", np.array(A))
    stat("실촬 정답", G)
    stat("실촬 모델 예측", P)

    c = np.hypot(G[:, 0] - 0.5, G[:, 1] - 0.5)
    m = c >= np.percentile(c, 75)
    print("\n  정답이 중앙에서 먼 장만 (상위 25%) — ②를 가르는 자리다")
    stat("그 장들 정답", G[m])
    stat("그 장들 모델 예측", P[m])

    print("\n  중심거리 사분위별 실패 구성")
    q = np.percentile(c, [25, 50, 75])
    b = np.digitize(c, q)
    for i in range(4):
        k = b == i
        print(f"    Q{i+1} {c[k].min():.3f}~{c[k].max():.3f}  n={k.sum():>3}"
              f"  통과 {100*np.mean(CL[k]=='통과'):>5.1f}%"
              f"  일부만 {100*np.mean(CL[k]=='일부만'):>5.1f}%"
              f"  딴 데 {100*np.mean(CL[k]=='딴 데'):>5.1f}%")

    print("\n  주의: 코퍼스가 실촬과 다르다는 것이 곧 '증강을 넓혀라'가 아니다.")
    print("  배율 축에서 같은 논리로 하한을 내렸다가 단조롭게 나빠졌다(§20.1).")


if __name__ == "__main__":
    main()
