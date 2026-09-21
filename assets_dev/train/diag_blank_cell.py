# **라벨이 꺼진 앞자리 칸을 포함하는가** — 두 코퍼스의 규약을 가른다.
#
# 왜(2026-09-20 사람 관찰): "이 실촬 라벨링은 내가한게 아닌가보다 두글자
# 혈당을 딱 두글자만 라벨링햇네". /arms 화면에서 눈으로 본 것이다.
#
# §18.6 에서 Roboflow 의 좌-우 쏠림 +0.247 을 "규약 차이"로 추정하고,
# 확정하려면 사람이 79장을 라벨해야 한다고 적었다. **필요 없다** — 잉크로
# 가를 수 있다.
#
# 자: 잉크 가로폭 / 라벨 상자 가로폭.
#   빈 칸을 포함하는 규약  2자리 사진에서 이 값이 **확 떨어진다**(빈 칸만큼
#                        상자가 넓다). 자릿수에 따라 두 봉우리가 생긴다.
#   켜진 숫자만 감싸는 규약 자릿수와 무관하게 값이 같다. 봉우리가 하나다.
#
# 자 검증은 우리 라벨(Datumo)로 한다 — 거기는 판독값을 알아 자릿수를 안다.
import argparse
import collections
import json
from pathlib import Path

import cv2
import numpy as np

from diag_ink_clip import ink_bbox

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"


def ours():
    read = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            read[j["id"]] = str(j.get("reading", "")).strip()
    im = DATUMO / "extracted" / "TILDE"
    by = collections.defaultdict(list)
    for l in (HERE / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        j = json.loads(l)
        q = j.get("quad")
        if not q:
            continue
        img = cv2.imread(str(im / (j["id"] + ".jpg")), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        a = np.asarray(q, float)
        gt = [a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()]
        ib = ink_bbox(img, gt)
        if ib is None:
            continue
        n = len([c for c in read.get(j["id"], "") if c.isdigit()])
        if n in (2, 3):
            by[n].append((ib[2] - ib[0]) / max(1.0, gt[2] - gt[0]))
    return by


def theirs(limit):
    from eval_band_roboflow import population
    pop = population()
    v = []
    for cid in sorted(pop)[:limit]:
        p, gt = pop[cid]
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        ib = ink_bbox(img, gt)
        if ib is None:
            continue
        v.append((ib[2] - ib[0]) / max(1.0, gt[2] - gt[0]))
    return np.asarray(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--cut", type=float, default=0.65)
    a = ap.parse_args()

    by = ours()
    print("자 검증 — 우리 라벨(Datumo), 자릿수를 아는 표본")
    print(f"  {'':<8}{'n':>5}{'중앙':>9}{'p25':>8}{'p75':>8}")
    for n in (2, 3):
        v = np.asarray(by[n])
        if len(v):
            print(f"  {n}자리{'':<4}{len(v):>5}{np.median(v):>9.3f}"
                  f"{np.percentile(v,25):>8.3f}{np.percentile(v,75):>8.3f}")
    if by[2] and by[3]:
        print(f"  두 무리가 갈린다 — 2자리 p75 {np.percentile(by[2],75):.3f} "
              f"< 3자리 p25 {np.percentile(by[3],25):.3f}. 자가 듣는다.")

    v = theirs(a.limit)
    print(f"\nRoboflow READING  n={len(v)}")
    print(f"  중앙 {np.median(v):.3f} · p25 {np.percentile(v,25):.3f} "
          f"· p75 {np.percentile(v,75):.3f}")
    h, e = np.histogram(v, bins=12, range=(0.3, 1.2))
    for i in range(12):
        print(f"   {e[i]:.2f}~{e[i+1]:.2f} {'#' * int(h[i]*50/max(1,h.max()))} {h[i]}")
    lo = 100.0 * (v < a.cut).mean()
    ours2 = 100.0 * len(by[2]) / max(1, len(by[2]) + len(by[3]))
    print(f"\n  {a.cut} 미만   Roboflow {lo:.1f}%   (참고: 우리 표본의 2자리 비율 {ours2:.1f}%)")
    print("  읽는 법: 빈 칸을 포함하는 규약이면 2자리만큼의 **봉우리**가 따로")
    print("  생긴다. 얇게 퍼진 꼬리는 봉우리가 아니라 자의 실패다.")


if __name__ == "__main__":
    main()
