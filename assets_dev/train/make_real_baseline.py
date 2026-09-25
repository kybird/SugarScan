# 실사진 기준선 정본 생성기 — 카드 「밴드 라벨 확장 뒤 합성 밀도·기하 기준선을
# 재고정한다」(2026-09-12).
#
# real_baseline.json 은 이 스크립트가 라벨 파일에서 생성한 것만 유효하다.
# 손으로 타이핑한 값이 하나라도 섞이면 정본이 아니다(카드 AC#2). 축을 새로
# 재지 않는다 — 자는 이미 있는 measure_panel_stats · diag_density_where ·
# measure_polarity 를 import 해서 모으기만 한다(§3.7, 2026-09-12 밀도 사고).
#
# 사용:
#   conda run -n sugartrain python make_real_baseline.py             # 정본 갱신
#   conda run -n sugartrain python make_real_baseline.py --markdown  # §3.8 표 출력
#
# 소비처는 셋이다 — synth_panel.py(REAL_DENSITY), validate_synth_panel.py(REAL),
# docs/GLM_TASKS.md §3.8(이 스크립트의 --markdown 출력을 붙여넣는다). 문서의
# 표는 사람이 읽는 렌더링이고 기계의 정본은 JSON 이다.
import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np

import measure_panel_stats as M
import diag_density_where as D
import measure_polarity as P

HERE = Path(__file__).resolve().parent
OUT = HERE / "real_baseline.json"


def _md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _pct(a, q):
    return float(np.percentile(a, q))


def _band_axis(stats, pos, raw_portrait, raw_wide):
    """collect_band 의 stats/pos -> 축별 median·p10·p90 사전 + 가로형 raw 목록.
    raw_wide 는 칼럼 카드(2026-09-12)의 실측 재표본용 — 가로형 분포는 치우쳐
    (median 이 p10~p90 중앙과 다름) 균등 재표본이 median 을 놓친다. 크롭 밖으로
    나간 라벨(x0<0 또는 x1>1)은 합성이 재현할 수 없어 뺀다."""
    out = {}
    for key in ("portrait", "wide"):
        a = np.asarray(stats[key])
        cx = np.asarray(pos[key][0::2])
        cy = np.asarray(pos[key][1::2])
        out[key] = dict(
            n=len(a),
            w_median=float(np.median(a[:, 0])), w_p10=_pct(a[:, 0], 10),
            w_p90=_pct(a[:, 0], 90),
            h_median=float(np.median(a[:, 1])), h_p10=_pct(a[:, 1], 10),
            h_p90=_pct(a[:, 1], 90),
            cx_median=float(np.median(cx)), cx_p10=_pct(cx, 10),
            cx_p90=_pct(cx, 90),
            cy_median=float(np.median(cy)), cy_p10=_pct(cy, 10),
            cy_p90=_pct(cy, 90),
        )
    out["portrait_raw"] = [[round(v, 4) for v in t] for t in raw_portrait]
    out["wide_raw"] = [[round(v, 4) for v in t] for t in raw_wide]
    return out


def build():
    aspect = np.asarray(M.collect_aspect())
    joined, total, stats, pos = M.collect_band()
    # raw 튜플(w,h,cx,cy) — 가로형 empirical 재표본용(위 _band_axis 설명).
    # 로더·좌표 변환은 collect_band 와 같은 함수를 쓴다.
    raw_portrait, raw_wide = [], []
    raw_ids = {"portrait": [], "wide": []}
    quads = {r["id"]: r for r in M._load_jsonl(M.QUADS_ORIENTED)}
    for b in M._load_jsonl(M.BAND_BOXES):
        g = quads.get(b["id"])
        if g is None:
            continue
        gx = M._rect_of(g["quad"])
        bx = M._rect_of(b["quad"])
        gw, gh = gx[2] - gx[0], gx[3] - gx[1]
        fx = ((bx[0] - gx[0]) / gw, (bx[2] - gx[0]) / gw)
        t = ((bx[1] - gx[1]) / gh + (bx[3] - gx[1]) / gh) / 2   # cy
        key = "portrait" if gw / gh < 1.0 else "wide"
        if key == "wide" and (fx[0] < 0 or fx[1] > 1):
            continue   # 크롭 밖으로 나간 밴드 라벨 — 합성이 재현 불가
        (raw_portrait if key == "portrait" else raw_wide).append(
            ((fx[1] - fx[0]), ((bx[3] - bx[1]) / gh),
             (fx[0] + fx[1]) / 2, t))
        raw_ids[key].append(b["id"])
    # 기기 균등 밴드 기하(사람 결정 (가) 2026-09-24: 프로파일 12종 균등을
    # 기기 충실로 유지 — 비교 기준도 사진 가중이 아닌 기기 균등이어야 한다).
    # 기기별 중앙값을 낸 뒤 기기 분포의 p10/p90 — 대규모 단말의 사진 수
    # 가중이 사라진다. 극성은 이미 기기 단위(by_device)다.
    dev = {}
    for l in (HERE / "device_labels.jsonl").read_text(
            encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            dev[j["id"]] = (j["brand"] + " " + j["model"] + " "
                            + j.get("variant", "")).strip()
    band_du = {}
    for key, raw in (("portrait", raw_portrait), ("wide", raw_wide)):
        ids = raw_ids[key]
        by_dev = {}
        for cid, t in zip(ids, raw):
            by_dev.setdefault(dev.get(cid, "?"), []).append(t)
        arr = np.asarray([np.median(np.asarray(v, float), axis=0)
                          for v in by_dev.values()])
        band_du[key] = {
            "n_devices": len(by_dev),
            "w_median": float(np.median(arr[:, 0])),
            "h_p10": float(np.percentile(arr[:, 1], 10)),
            "h_p90": float(np.percentile(arr[:, 1], 90)),
            "h_median": float(np.median(arr[:, 1])),
            "cx_p10": float(np.percentile(arr[:, 2], 10)),
            "cx_p90": float(np.percentile(arr[:, 2], 90)),
            "cx_median": float(np.median(arr[:, 2])),
            "cy_p10": float(np.percentile(arr[:, 3], 10)),
            "cy_p90": float(np.percentile(arr[:, 3], 90)),
            "cy_median": float(np.median(arr[:, 3])),
        }

    dens = np.asarray(M.collect_density(frame_exc=0.0))
    ring = np.asarray([r for r in (D.stat_ring(g, b)
                                   for g, b in D.iter_real()) if r is not None])
    den = np.asarray([r for r in (D.stat_denoise(g, b)
                                  for g, b in D.iter_real()) if r is not None])
    pol = P.collect_polarity()
    contrast = np.asarray(pol["contrast"])
    ok = den[:, 0] > 0   # 밀도 0인 장은 질감 기여가 정의되지 않는다
    texture = (den[ok, 0] - den[ok, 1]) / den[ok, 0]

    hist, edges = np.histogram(aspect, bins=np.arange(0.0, 3.05, 0.1))
    corpus_rows = P._load_jsonl(P.CORPUS_LABELS)
    readings = np.asarray([r["reading"] for r in corpus_rows])

    return dict(
        provenance=dict(
            generated_at=datetime.datetime.now().astimezone().isoformat(timespec="minutes"),
            generator="assets_dev/train/make_real_baseline.py",
            rulers=["measure_panel_stats.py", "diag_density_where.py",
                    "measure_polarity.py"],
            labels=dict(
                band_boxes=dict(path="assets_dev/train/band_boxes.jsonl",
                                rows=total, joined=joined, md5=_md5(M.BAND_BOXES)),
                gmscreen_quads_oriented=dict(
                    path="assets_dev/train/gmscreen_quads_oriented.jsonl",
                    rows=len(M._load_jsonl(M.QUADS_ORIENTED)),
                    md5=_md5(M.QUADS_ORIENTED)),
                corpus=dict(path=str(P.CORPUS_LABELS.relative_to(M.UPSTREAM.parent)),
                            rows=len(corpus_rows)),
            ),
            handles=dict(density="frame_exc=0.0, long_side=896",
                         ring="ring=0.15",
                         contrast="밴드 p95-p5 (measure_polarity.polarity_of)"),
        ),
        aspect=dict(
            n=len(aspect), wh_median=float(np.median(aspect)),
            wh_p10=_pct(aspect, 10), wh_p90=_pct(aspect, 90),
            portrait_pct=float(np.mean(aspect < 1.0) * 100),
            very_wide_pct=float(np.mean(aspect > 2.0) * 100),
            hist_0p1={f"[{e:.1f},{e + 0.1:.1f})": int(h)
                      for e, h in zip(edges[:-1], hist) if h},
        ),
        band=_band_axis(stats, pos, raw_portrait, raw_wide),
        band_du=band_du,
        density=dict(
            n=len(dens), frame_exc=0.0,
            median=float(np.median(dens)), p10=_pct(dens, 10), p90=_pct(dens, 90),
            min=float(dens.min()), max=float(dens.max()),
            values=[round(float(v), 6) for v in dens],
        ),
        ring=dict(
            n=len(ring),
            outer_median=float(np.median(ring[:, 0])),
            inner_median=float(np.median(ring[:, 1])),
        ),
        denoise=dict(
            n=len(den),
            orig_median=float(np.median(den[:, 0])),
            denoised_median=float(np.median(den[:, 1])),
            texture_pct_median=float(np.median(texture) * 100),
            texture_n=int(ok.sum()),
        ),
        polarity=dict(
            n=pol["n"],
            inverted_pct=float(np.mean(pol["inverted"]) * 100),
            contrast_median=float(np.median(contrast)),
            contrast_p10=_pct(contrast, 10), contrast_p90=_pct(contrast, 90),
            contrast_min=float(contrast.min()),
            contrast_lt40_pct=float(np.mean(contrast < 40) * 100),
            by_device={name: dict(inverted=v[0], n=v[1])
                       for name, v in sorted(pol["per_device"].items())},
        ),
        digits=dict(
            n=len(readings),
            two_digit_pct=float(np.mean((readings >= 10) & (readings <= 99)) * 100),
            three_digit_pct=float(np.mean((readings >= 100) & (readings <= 999)) * 100),
        ),
    )


def markdown_table(b):
    a, band, d, r, de, po, di = (b["aspect"], b["band"], b["density"], b["ring"],
                                 b["denoise"], b["polarity"], b["digits"])
    lines = [
        "| 축 | 실사진 | n |",
        "|---|---|---|",
        f"| 종횡비 w/h | median {a['wh_median']:.3f} · p10 {a['wh_p10']:.3f} "
        f"· p90 {a['wh_p90']:.3f} · portrait {a['portrait_pct']:.1f}% | {a['n']} |",
        f"| 세로형 밴드 w/h 비 | w/panel_w {band['portrait']['w_median']:.3f} "
        f"· h/panel_h {band['portrait']['h_median']:.3f} "
        f"· cx {band['portrait']['cx_median']:.3f} "
        f"· cy {band['portrait']['cy_median']:.3f} | {band['portrait']['n']} |",
        f"| 가로형 밴드 w/h 비 | w/panel_w {band['wide']['w_median']:.3f} "
        f"· h/panel_h {band['wide']['h_median']:.3f} "
        f"· cx {band['wide']['cx_median']:.3f} "
        f"· cy {band['wide']['cy_median']:.3f} | {band['wide']['n']} |",
        f"| 엣지 밀도(밴드 밖) 전체 | median {d['median'] * 100:.2f}% "
        f"· p10 {d['p10'] * 100:.2f}% · p90 {d['p90'] * 100:.2f}% | {d['n']} |",
        f"| 엣지 밀도 — 바깥 링(15%) | median {r['outer_median'] * 100:.2f}% | {r['n']} |",
        f"| 엣지 밀도 — 안쪽 | median {r['inner_median'] * 100:.2f}% | {r['n']} |",
        f"| 극성 반전 | {po['inverted_pct']:.1f}% | {po['n']} |",
        f"| 밴드 대비 p95-p5 | median {po['contrast_median']:.0f} "
        f"· p10 {po['contrast_p10']:.0f} · p90 {po['contrast_p90']:.0f} "
        f"· min {po['contrast_min']:.0f} · 40미만 {po['contrast_lt40_pct']:.1f}% | {po['n']} |",
        f"| 질감 기여(denoise) | {de['texture_pct_median']:.1f}% | {de['texture_n']} |",
        f"| 자릿수 | 2자리 {di['two_digit_pct']:.1f}% · 3자리 {di['three_digit_pct']:.1f}% | {di['n']} |",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true",
                    help="JSON 을 쓰지 않고 §3.8 표만 출력한다")
    a = ap.parse_args()
    if a.markdown:
        b = json.loads(OUT.read_text(encoding="utf-8"))
        print(markdown_table(b))
        return 0
    b = build()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=1)
    print(f"written: {OUT}")
    print(markdown_table(b))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
