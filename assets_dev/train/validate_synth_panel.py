# 물리 패널 합성 검증 — 「합성을 물리 패널 기준으로 재구성」 카드의 AC 자(2026-09-12).
#
# 500장을 렌더해 카드 AC 와 실측 기준선을 같은 자로 나란히 잰다. 주장이 아니라
# 재기다: 모든 수치는 이 스크립트 출력 원문으로 보고서에 들어간다.
#
#   conda run -n sugartrain python validate_synth_panel.py --count 500 --seed 23000
#
# 하드 실패(0 이어야): 배치 겹침 · 쿼드 캔버스 이탈 · 긴 변 896 위반 ·
# 라벨 비숫자 · 요소 패널 이탈. 분포 비교(종횡비·밀도·극성·대비)는 실측 분포와
# 나란히 인쇄해 눈으로 판정한다.
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import synth_panel as sp  # noqa: E402
from measure_panel_stats import edge_density_outside  # noqa: E402

# 실측 기준선 — 정본 real_baseline.json(make_real_baseline.py 가 라벨 파일에서
# 생성)을 읽는다. 이 파일에 수치를 베끼지 않는다(카드 2026-09-12 기준선 정본화).
# 키 이름은 아래 인쇄문의 것을 그대로 쓴다.
with open(HERE / "real_baseline.json", encoding="utf-8") as _f:
    _RB = json.load(_f)
REAL = dict(
    wh_median=round(_RB["aspect"]["wh_median"], 3),
    wh_p10=round(_RB["aspect"]["wh_p10"], 3),
    wh_p90=round(_RB["aspect"]["wh_p90"], 3),
    portrait=round(_RB["aspect"]["portrait_pct"], 1),
    very_wide=round(_RB["aspect"]["very_wide_pct"], 1),
    density_median=round(_RB["density"]["median"], 4),
    density_p10=round(_RB["density"]["p10"], 4),
    density_p90=round(_RB["density"]["p90"], 4),
    contrast_lt40=round(_RB["polarity"]["contrast_lt40_pct"], 1),  # p95-p5<40 비율
    inverted=round(_RB["polarity"]["inverted_pct"], 1),
    digits2=round(_RB["digits"]["two_digit_pct"], 1),
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=500)
    ap.add_argument("--seed", type=int, default=23000)
    ap.add_argument("--out", default=str(HERE / "_diag" / "panel_rebuild" /
                                         f"validate_{args_seed_local()}"))
    args = ap.parse_args()
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)

    rng = __import__("random").Random(args.seed)
    np.random.seed(args.seed)          # 광학 노이즈도 재현 가능하게
    manifest = []
    hard = {"overlaps": 0, "quad_out": 0, "long_side": 0, "label": 0,
            "clipped": 0, "bezel_inside": 0, "sizes": 0}
    for i in range(args.count):
        val = sp.sample_value(rng)
        s = sp.render_panel(val, rng)
        name = f"panel_{args.seed}_{i}"
        cv2.imwrite(str(out / "images" / f"{name}.png"), s["panel"])
        q = s["quad"]
        W, H, m = s["W"], s["H"], s["margin"]
        rec = dict(id=name, profile=s["profile"], w=W, h=H,
                   wh=round(s["wh"], 4), quad=np.round(q, 2).tolist(),
                   label=s["label"], inverted=s["inverted"],
                   glyph_plane_check=s["glyph_plane_check"],
                   text_heights=s["text_heights"],
                   density=round(float(s["density"]), 5),
                   target_density=s["target_density"], margin=m,
                   bezel=s["bezel"], dropped=s["dropped"],
                   rects=[[round(float(v), 1) for v in r[:4]] + [r[4]]
                          for r in s["rects"]])
        # ── 하드 검사 ────────────────────────────────────────────────
        if _count_overlaps(s["rects"]):
            hard["overlaps"] += 1
        # 글자 크기 종수(AC#3, 카드 「합성 글리프 네 결함」 2026-09-13) —
        # LCD 안 글자 높이는 큰 숫자(dh) 와 보조(aux_h) 2종이 최대다.
        # 베젤(몸체 인쇄)은 계층이 달라 세지 않는다.
        if len(set(s["text_heights"])) > 2:
            hard["sizes"] += 1
        if (q[:, 0].min() < 0 or q[:, 0].max() > W - 1
                or q[:, 1].min() < 0 or q[:, 1].max() > H - 1):
            hard["quad_out"] += 1
        if max(W, H) != sp.LONG_SIDE:
            hard["long_side"] += 1
        if not s["label"].isdigit():
            hard["label"] += 1
        # 요소 패널 이탈(AC#12) — 액정 요소 rect 는 패널 안에 완전히 들어와야 한다.
        # 여백은 사방이 다르다(margins=[t,b,l,r]) — 스칼라 margin 은 그 최댓값이라
        # 좌우에 상하 여백을 들이대 정상 배치를 이탈로 잡는다(리뷰 2026-09-12:
        # 거짓 양성 107/120). 구판 렌더러에는 margins 가 없으므로 스칼라로 떨어진다.
        mg_t, mg_b, mg_l, mg_r = s.get("margins") or (m, m, m, m)
        for x0, y0, x1, y1, nm in s["rects"]:
            if (x0 < mg_l + 1 or y0 < mg_t + 1
                    or x1 > W - mg_r - 1 or y1 > H - mg_b - 1):
                hard["clipped"] += 1
                break
        # 베젤 문자는 느슨한 크롭(링 >= 14)에서만, 그리고 링 위에서만(AC#13)
        if s["bezel"] and m < 14:
            hard["bezel_inside"] += 1
        manifest.append(rec)

    with open(out / "manifest.jsonl", "w", encoding="utf-8") as f:
        for r in manifest:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ── 몽타주: 오버레이 없는 판과 쿼드 있는 판을 모두(지시서 요구) ────────
    sp.montage(out / "montage_plain.png", out / "images", manifest, n=12,
               with_quad=False)
    sp.montage(out / "montage_quad.png", out / "images", manifest, n=12,
               with_quad=True)

    # 리더뷰 스트립(AC#2 참고 산출물) — 패널 -> 320x160 워프로 납작해진 글리프
    strip = []
    for r in manifest[:6]:
        img = cv2.imread(str(out / "images" / f"{r['id']}.png"),
                         cv2.IMREAD_GRAYSCALE)
        s = dict(panel=img, H=r["h"], W=r["w"], quad=np.asarray(r["quad"],
                                                                np.float32))
        rv, rq = sp.reader_view(s)
        rq = np.round(rq).astype(np.int32)
        cv2.polylines(rv, [rq.reshape(-1, 1, 2)], True, 255, 1)
        strip.append(rv)
    cv2.imwrite(str(out / "reader_strip.png"), np.hstack(strip))

    # ── 분포 비교 ────────────────────────────────────────────────────
    wh = np.asarray([r["wh"] for r in manifest])
    dens = np.asarray([r["density"] for r in manifest])
    gpc = np.asarray([r["glyph_plane_check"] for r in manifest])
    inv = np.mean([r["inverted"] for r in manifest]) * 100
    d2 = np.mean([len(r["label"]) == 2 for r in manifest]) * 100
    p = lambda a, q_: float(np.percentile(a, q_))

    # 대비 — 밴드 p95-p5 (실측 자: measure_polarity.polarity_of 와 같은 정의)
    contrasts = []
    for r in manifest:
        img = cv2.imread(str(out / "images" / f"{r['id']}.png"),
                         cv2.IMREAD_GRAYSCALE)
        q = np.asarray(r["quad"])
        H, W = img.shape
        band = img[int(q[:, 1].min()):int(np.ceil(q[:, 1].max())),
                   int(q[:, 0].min()):int(np.ceil(q[:, 0].max()))]
        if band.size:
            contrasts.append(float(np.percentile(band, 95)
                                   - np.percentile(band, 5)))
    contrasts = np.asarray(contrasts)

    print(f"== 합성 n={len(manifest)} (seed {args.seed}) vs 실측 기준선 ==")
    print(f"종횡비 w/h   합성 median={np.median(wh):.3f} p10={p(wh, 10):.3f} "
          f"p90={p(wh, 90):.3f} | 실측 {REAL['wh_median']} "
          f"[{REAL['wh_p10']}, {REAL['wh_p90']}]")
    print(f"세로(<1)     합성 {np.mean(wh < 1) * 100:.1f}% | 실측 "
          f"{REAL['portrait']}%  (가로 x2 부스트 반영)")
    print(f"매우 가로(>2) 합성 {np.mean(wh > 2) * 100:.1f}% | 실측 "
          f"{REAL['very_wide']}%")
    print(f"밀도(밴드 밖) 합성 median={np.median(dens):.4f} "
          f"p10={p(dens, 10):.4f} p90={p(dens, 90):.4f} | 실측 "
          f"{REAL['density_median']} [{REAL['density_p10']}, "
          f"{REAL['density_p90']}]")
    print(f"밴드 대비 p95-p5  median={np.median(contrasts):.0f} "
          f"p10={p(contrasts, 10):.0f} | <40 비율 합성 "
          f"{np.mean(contrasts < 40) * 100:.1f}% vs 실측 {REAL['contrast_lt40']}%")
    print(f"극성 반전     합성 {inv:.1f}% | 실측 {REAL['inverted']}%")
    print(f"2자리 값      합성 {d2:.1f}% | 실측 {REAL['digits2']}%")
    print(f"글리프 평면   gpc median={np.median(gpc):.4f} "
          f"p10={p(gpc, 10):.4f} min={gpc.min():.4f}  (0.9 미만 "
          f"{np.mean(gpc < 0.9) * 100:.1f}%)")
    dropped = {}
    for r in manifest:
        for d in r["dropped"]:
            dropped[d] = dropped.get(d, 0) + 1
    print(f"뺀 요소(배치 실패): {dict(sorted(dropped.items(), key=lambda x: -x[1]))}")
    bez = sum(1 for r in manifest if r["bezel"])
    print(f"베젤 인쇄(링 위): {bez}장 — 문자열: "
          f"{sorted({r['bezel'] for r in manifest if r['bezel']})}")
    print(f"-- 하드 검사: {hard}")
    if any(hard.values()):
        print("하드 실패 1건 이상 — 카드 완료 아님")
        return 1
    print("하드 검사 전부 0")
    return 0


def args_seed_local():
    return "run"


def _count_overlaps(rects):
    n = 0
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, b = rects[i], rects[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                n += 1
    return n


if __name__ == "__main__":
    raise SystemExit(main())
