# 글리프 3축 사후 보고 자 — 획 굵기·세그먼트 간격·기울기(2026-09-24).
#
# 카드 「7-세그먼트 글리프 정밀화」 AC#2(사람 승인 2026-09-24 사후 보고로
# 한정): 실사진 분포를 재서 합성 파라미터 범위와 **나란히 보고만 한다**.
# 측정값을 설계에 되먹이지 않는다(patterns/no-real-photo-ruler-for-synth,
# SPEC §6). 합성 설계값은 사람 눈 판정으로만 정한다(이 카드의 16차 스파이크).
#
# 실사진 표본: 사람 밴드 라벨(band_boxes.jsonl) 3자리 값의 균등 슬롯 크롭 —
# make_glyph_compare_sheet.collect_real 과 동일 규약(검출기 출력을 쓰면
# 검출 오차가 글리프 차이로 보인다).
# 합성 표본: synth_profiles._glyph_mask 숫자 마스크(변형 Light/Regular/Bold,
# 이탤릭 제외 — 전단은 별도 축). 결정적이라 n 은 작지만 전수.
#
# 세 축의 정의(양쪽에 동일 적용):
#   stroke — 획 굵기/높이. 잉크=1 입력 distanceTransform(잉크 픽셀의
#            배경까지 거리 = 획 중심 반지름)의 2×p90. 꽉 찬 크롭 경계
#            효과를 끊는 1px 0-패딩 필수 — 없으면 가장자리 획의 반지름이
#            실제 2배로 잡힌다(경계 밖 배경이 없어 한쪽만 계산).
#            (초판 버그 2건 2026-09-24 수리: 패딩 부재·입력 반전 오류)
#   gap    — 세그먼트 간격/높이. 수평 투영(행별 잉크 밀도)의 내부 골 중
#            최대 폭 — 가로획 사이 수직 틈의 대표값.
#   slant  — 기울기(도). 이미지 모멘트 μ11/μ02 = tan(기울기). 숫자 '1'
#            만 쓴다 — 비대칭 숫자(4·7 등)는 형상 자체가 모멘트를 기울인다.
#
# 사용: python measure_glyph_axes.py [--per-digit 16]
import argparse
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent.parent / "docs" / "reports" / "glyph-axes-posthoc-2026-09-24.md"

from make_glyph_compare_sheet import collect_real          # noqa: E402
from synth_profiles import _glyph_mask                      # noqa: E402

H = 200                       # 측정 통일 높이(양쪽 동일)
SYNTH_VARIANTS = ("Light", "Regular", "Bold")


def ink_mask(gray):
    """회색 슬롯 → 극성 정규화된 이진 잉크(잉크=소수)."""
    g = cv2.resize(gray.astype(np.float32), (max(8, int(round(
        gray.shape[1] * H / gray.shape[0]))), H))
    g = (g - g.min()) / max(1e-6, g.max() - g.min())
    b = (g < 0.5).astype(np.uint8)                          # 어두운 쪽=잉크
    if b.mean() > 0.5:                                      # 극성 뒤집힘
        b = 1 - b
    return b


def axes_from_ink(b, digit=None):
    """이진 잉크에서 세 축. 슬롯 전체(한 자릿수)를 하나의 표본으로."""
    ys, xs = np.nonzero(b)
    if len(ys) < 30:
        return None
    # 획 굵기 — 잉크=1 DT + 1px 0-패딩(경계 획의 반지름 보정)
    bp = cv2.copyMakeBorder(b, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    dist = cv2.distanceTransform(bp, cv2.DIST_L2, 5)[1:-1, 1:-1]
    r = dist[dist > 0]
    stroke = 2.0 * float(np.percentile(r, 90)) / H
    # 세그먼트 간격 — 수평 투영 내부 골 최대 폭
    proj = b.sum(axis=1).astype(np.float32)
    peak = max(1.0, float(proj.max()))
    inside = np.where(proj > 0.02 * peak)[0]
    y0, y1 = inside.min(), inside.max()
    run = best = 0
    for y in range(y0, y1 + 1):
        run = run + 1 if proj[y] < 0.05 * peak else 0
        best = max(best, run)
    gap = best / H
    # 기울기 — 모멘트 μ11/μ02(숫자 '1' 한정: 형상 비대칭 격리)
    slant = None
    if digit == "1":
        m = cv2.moments(b.astype(np.float32), binaryImage=True)
        slant = float(np.degrees(np.arctan(m["mu11"] / m["mu02"])))             if m["mu02"] else 0.0
    return stroke, gap, slant


def side_by_side(per_digit):
    real = collect_real(per_digit)
    rows = []
    rr = {"stroke": [], "gap": [], "slant": []}
    n_real = 0
    for d, crops in sorted(real.items()):
        for _, c in crops:
            a = axes_from_ink(ink_mask(c), d)
            if a:
                rr["stroke"].append(a[0]); rr["gap"].append(a[1])
                if a[2] is not None:
                    rr["slant"].append(a[2])
                n_real += 1
    rows.append(("실사진(사람 밴드 라벨 슬롯)", n_real, rr))

    for v in SYNTH_VARIANTS:
        ss = {"stroke": [], "gap": [], "slant": []}
        for d in "0123456789":
            m = _glyph_mask(d, v, H)
            a = axes_from_ink(m.astype(np.uint8), d)
            if a:
                ss["stroke"].append(a[0]); ss["gap"].append(a[1])
                if a[2] is not None:
                    ss["slant"].append(a[2])
        rows.append((f"합성 {v}(숫자 전수)", 10, ss))
    return rows


def fmt(vals):
    if not vals:
        return "—"
    q = np.percentile(vals, (25, 50, 75))
    return f"{q[1]:.3f} (p25 {q[0]:.3f} / p75 {q[2]:.3f})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-digit", type=int, default=16)
    args = ap.parse_args(argv)
    rows = side_by_side(args.per_digit)

    lines = [
        "# 글리프 3축 사후 보고(획 굵기·세그먼트 간격·기울기) — 2026-09-24",
        "",
        "카드 「7-세그먼트 글리프 정밀화」 AC#2 산출. **사후 보고다 — 측정값을",
        "합성 설계에 되먹이지 않는다**(no-real-photo-ruler·SPEC §6, 사람 승인",
        "2026-09-24). 자: `assets_dev/train/measure_glyph_axes.py`(본 문서 산출).",
        "",
        f"- 실사진 표본: 사람 밴드 라벨 3자리 슬롯(자릿수당 {args.per_digit} 상한)",
        f"- 합성 표본: `_glyph_mask` 숫자 0-9 전수(변형별, 결정적)",
        "- 축 정의: stroke=잉크 반전 DT 2×p90/높이 · gap=수평투영 내부 골 최대폭/높이",
        "  · slant=모멘트 μ11/μ02(도, 숫자 '1' 만 — 형상 비대칭 격리)",
        "",
        "| 표본 | n | 획 굵기/높이 (중앙) | 세그먼트 간격/높이 | 기울기(도) |",
        "|---|---|---|---|---|",
    ]
    for name, n, s in rows:
        lines.append(f"| {name} | {n} | {fmt(s['stroke'])} | "
                     f"{fmt(s['gap'])} | {fmt(s['slant'])} |")
    lines += [
        "",
        "읽는 법: 실사진-합성 분포가 겹치는지가 정보다. 값을 설계로 옮기는",
        "절차는 이 문서에 없다 — 설계값은 사람 눈 판정(카드 스파이크 v6~v16)으로",
        "이미 확정됐다.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n-> {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
