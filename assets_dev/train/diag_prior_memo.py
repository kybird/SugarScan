# **모델이 학습 분포의 자리를 외운 것인가** — 실촬에서 틀릴 때 무엇으로
# 돌아가는지 본다.
#
# 왜(2026-09-20 사람 관찰): "딱봐도 모델이 그냥 학습할때 LCD 의 위치가
# 있었던 비율을 외운걸로 보인다".
#
# 앞서 기각한 '비율 지름길' 가설과 **다른 질문**이다. 그때는 합성 홀드아웃에서
# 픽셀 없이 맞힐 수 있는지를 봤고(무픽셀 오라클 46.7%/69.4% 대 모델 99.6%),
# 지금은 **실촬에서 틀릴 때 학습 분포의 평균 상자로 돌아가는가**를 본다.
# 잘 맞을 때 픽셀을 본다는 것과, 틀릴 때 사전분포로 떨어진다는 것은 양립한다.
#
# 방법: 예측과 정답을 **레터박스 416 좌표**로 옮겨 정규화한다(사진 크기가
# 제각각이라 원본 좌표로는 못 맞댄다). 학습 코퍼스의 정답 상자로 사전분포를
# 만들고, 예측이 그 평균에 얼마나 가까운지를 정답에 가까운 정도와 맞댄다.
#
#   외웠다면   : 틀린 장에서 예측이 **사전평균에 붙어** 있다.
#   안 외웠다면: 틀린 장에서도 예측이 사전평균과 멀다(엉뚱하되 제각각).
#
# 대조군으로 **상수 상자**(늘 사전평균만 내놓는 검출기)를 같이 낸다.
import argparse
import json
from pathlib import Path

import numpy as np

from report_fail_mix import rows, classify, digit_cell, pad, HERE


def lb_norm(box, ow, oh, size=416):
    """원본 좌표 -> 레터박스 416 -> 0~1. train_band.letterbox 와 같은 규칙."""
    r = min(size / ow, size / oh)
    dx, dy = (size - ow * r) / 2, (size - oh * r) / 2
    return np.array([(box[0] * r + dx) / size, (box[1] * r + dy) / size,
                     (box[2] * r + dx) / size, (box[3] * r + dy) / size])


def cwh(b):
    return np.array([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2,
                     b[2] - b[0], b[3] - b[1]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="atone")
    ap.add_argument("--dir", default="_diag/tone")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--data", default="synth_coco/TC")
    ap.add_argument("--ann", default="instances_curve_07998.json")
    a = ap.parse_args()

    # ── 학습 코퍼스의 사전분포 ──────────────────────────────────────────
    j = json.loads((HERE / a.data / "annotations" / a.ann)
                   .read_text(encoding="utf-8"))
    wh = {im["id"]: (im["width"], im["height"]) for im in j["images"]}
    P = []
    for an in j["annotations"]:
        w, h = wh[an["image_id"]]
        b = an["bbox"]
        P.append(cwh(lb_norm([b[0], b[1], b[0] + b[2], b[1] + b[3]], w, h)))
    P = np.array(P)
    mu, sd = P.mean(0), P.std(0)
    print(f"학습 사전분포 (레터박스 416 정규화, n={len(P)})")
    for i, nm in enumerate(("중심x", "중심y", "폭", "높이")):
        print(f"  {nm:<6} 평균 {mu[i]:.3f}  SD {sd[i]:.3f}")
    prior = np.array([mu[0] - mu[2] / 2, mu[1] - mu[3] / 2,
                      mu[0] + mu[2] / 2, mu[1] + mu[3] / 2])

    # ── 실촬 예측 ────────────────────────────────────────────────────
    dev = set(json.loads((HERE / "rf_split.json")
                         .read_text(encoding="utf-8"))["dev"])
    acc = {}
    base = []
    for r in rows(HERE / a.dir / f"roboflow_{a.arm}_s{a.seed}.jsonl"):
        if r["id"] not in dev or not r.get("gt") or not r.get("det"):
            continue
        p = cwh(lb_norm(r["pred"], r["ow"], r["oh"]))
        g = cwh(lb_norm(r["gt"], r["ow"], r["oh"]))
        # 사전평균 상자가 이 사진에서 통과했을까 (상수 검출기 대조군)
        pr = np.array(prior)
        size, rr = 416, min(416 / r["ow"], 416 / r["oh"])
        dxx, dyy = (416 - r["ow"] * rr) / 2, (416 - r["oh"] * rr) / 2
        pr_orig = [(pr[0] * size - dxx) / rr, (pr[1] * size - dyy) / rr,
                   (pr[2] * size - dxx) / rr, (pr[3] * size - dyy) / rr]
        d = digit_cell(r["gt"]); e = pad(pr_orig)
        const_ok = (e[0] <= d[0] and e[1] <= d[1]
                    and e[2] >= d[2] and e[3] >= d[3])
        ga = max(1.0, (r["gt"][2]-r["gt"][0]) * (r["gt"][3]-r["gt"][1]))
        car = max(0.0, e[2]-e[0]) * max(0.0, e[3]-e[1]) / ga
        me = pad(r["pred"])
        mar = max(0.0, me[2]-me[0]) * max(0.0, me[3]-me[1]) / ga
        mok = (me[0] <= d[0] and me[1] <= d[1]
               and me[2] >= d[2] and me[3] >= d[3])
        base.append((const_ok, const_ok and car <= 2.0, car,
                     mok, mok and mar <= 2.0))
        acc.setdefault(classify(r), []).append(
            (np.linalg.norm(p - mu), np.linalg.norm(p - g),
             np.linalg.norm(g - mu), const_ok))

    print()
    print(f"  {'판정':<8}{'n':>5}{'예측↔사전평균':>14}{'예측↔정답':>12}"
          f"{'정답↔사전평균':>14}{'상수상자 통과':>14}")
    for cls in ("통과", "일부만", "딴 데"):
        v = acc.get(cls)
        if not v:
            continue
        A = np.array([[x[0], x[1], x[2]] for x in v])
        ok = 100 * np.mean([x[3] for x in v])
        print(f"  {cls:<8}{len(v):>5}{np.median(A[:,0]):>14.3f}"
              f"{np.median(A[:,1]):>12.3f}{np.median(A[:,2]):>14.3f}"
              f"{ok:>13.1f}%")
    B = np.array(base, float)
    print()
    print("  **상수 상자 대조군** — 늘 학습 사전평균만 내놓는 검출기")
    print(f"  {'':<20}{'담음':>9}{'담음 ∧ 면적<=2':>16}{'면적비 중앙':>13}")
    print(f"  {'상수 상자':<20}{100*B[:,0].mean():>8.1f}%"
          f"{100*B[:,1].mean():>15.1f}%{np.median(B[:,2]):>13.2f}")
    print(f"  {'모델':<20}{100*B[:,3].mean():>8.1f}%"
          f"{100*B[:,4].mean():>15.1f}%")

    print()
    print("  읽는 법: **외웠다면** 틀린 장(딴 데)에서 `예측↔사전평균`이 작고")
    print("  `예측↔정답`이 커야 한다. 그리고 그 장들에서 `정답↔사전평균`도")
    print("  커야 한다 — 정답이 사전분포에서 먼 장이라 외운 값을 냈다는 뜻이다.")
    print("  `상수상자 통과`는 **늘 사전평균만 내놓는 검출기**의 성적이다.")
    print("  모델이 그것보다 낫지 않으면 픽셀을 안 본 것이다.")


if __name__ == "__main__":
    main()
