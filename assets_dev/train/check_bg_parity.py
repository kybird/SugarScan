# 절차적 배경 자가검사 — **배경만 바뀌었는가** (SPEC §9.7.2 선결 조건)
#
# 단계 2 비교는 "데이터에서 배경 하나만 다르다"를 전제로 한다. 그 전제가
# 깨지면 비교가 아니라 두 개의 다른 실험이 된다. 그래서 학습을 걸기 전에
# 같은 시드로 두 코퍼스를 한 장씩 만들어 세 가지를 확인한다.
#
#   1. 기기·자세·라벨이 같은가 — 프로파일·값·상자·유리 쿼드·캔버스 크기
#   2. **기기 내부 픽셀이 같은가** — 커버리지가 꽉 찬(255) 자리에서 두 이미지가
#      바이트까지 같아야 한다. 배경 합성이 기기 안을 건드리면 여기서 걸린다.
#   3. 경계의 반투명 혼합은 정상 — 0<cover<255 자리는 다를 수 있다. 그 자리가
#      전체에서 얼마나 되는지도 함께 적는다(너무 넓으면 마스크가 샌 것이다).
#
# 전경 마스크는 **렌더가 아는 커버리지**다. 픽셀값이 bg_col 과 같은지로
# 추정하지 않는다 — 실제 기기 픽셀이 우연히 같은 밝기일 수 있다
# (2026-09-19 자문 지적).
#
# 사용: python check_bg_parity.py --n 40 --seed 41000
import argparse
import random

import numpy as np

import synth_panel as sp


def one(seed0, i, bg):
    """같은 (seed0, i) 로 한 장. bg 만 바꿔 두 번 부른다."""
    sp.PROCEDURAL_BG = (bg == "procedural")
    rng = random.Random(seed0)
    for _ in range(i):          # 앞 장들이 소비한 난수를 그대로 흘려보낸다
        v = sp.sample_value(rng)
        sp.render_panel(v, rng)
    val = sp.sample_value(rng)
    return val, sp.render_panel(val, rng)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=41000)
    a = ap.parse_args()

    bad_meta = bad_inner = 0
    edge_frac, diff_frac = [], []
    for i in range(a.n):
        v0, s0 = one(a.seed, i, "flat")
        v1, s1 = one(a.seed, i, "procedural")
        # 1) 기기·자세·라벨
        same = (v0 == v1 and s0["profile"] == s1["profile"]
                and s0["W"] == s1["W"] and s0["H"] == s1["H"]
                and s0["label"] == s1["label"]
                and np.allclose(s0["quad"], s1["quad"], atol=1e-4)
                and np.allclose(s0["digit_box"], s1["digit_box"], atol=1e-4)
                and np.allclose(s0["glass_quad"], s1["glass_quad"], atol=1e-4))
        if not same:
            bad_meta += 1
            print(f"  [{i}] **기기/자세/라벨이 다르다** — 난수 흐름이 섞였다")
            continue
        # 2) 기기 내부 (커버리지 255)
        c = s0["cover"]
        assert np.array_equal(c, s1["cover"]), f"[{i}] 커버리지가 다르다"
        inner = c >= 255
        d = (s0["panel"].astype(np.int16) - s1["panel"].astype(np.int16))
        n_in = int(inner.sum())
        n_diff = int((d[inner] != 0).sum()) if n_in else 0
        if n_diff:
            bad_inner += 1
            print(f"  [{i}] **기기 내부가 {n_diff}px 달라졌다** (내부 {n_in}px)")
        # 3) 경계 반투명 폭
        edge = (c > 0) & (c < 255)
        edge_frac.append(edge.mean())
        diff_frac.append((d != 0).mean())

    n = a.n
    print(f"n={n}  seed0={a.seed}")
    print(f"  기기/자세/라벨 불일치 {bad_meta}장")
    print(f"  기기 내부 픽셀 변조   {bad_inner}장")
    if edge_frac:
        print(f"  경계 반투명 면적 비율  중앙 {np.median(edge_frac)*100:.3f}%"
              f" · 최대 {max(edge_frac)*100:.3f}%")
        print(f"  전체에서 바뀐 픽셀 비율 중앙 {np.median(diff_frac)*100:.1f}%"
              f" (배경이 차지하는 면적이다)")
    ok = (bad_meta == 0 and bad_inner == 0)
    print("  => " + ("**통과** — 배경만 바뀌었다. 학습을 걸어도 된다."
                     if ok else "**실패** — 학습을 걸지 않는다."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
