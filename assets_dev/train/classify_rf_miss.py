# 로보플로우 완전 미검출 3분할 자 — 구도/열화/이물 (2026-09-21 카드).
#
# 정의(이 자가 정본):
#   완전 미검출 = report_fail_mix.py 의 '미검출' 클래스 — 검출기가 det 상자를
#   하나도 내지 못한 장. 검출기는 aug_s5·aug_s6·aug_s7 세 스냅샷을 보며,
#   **한 팔이라도** 미검출인 dev 장(합집합)을 대상으로 한다. 세 팔 교집합은
#   0장이다 — 미검출 장이 시드마다 바뀌므로 '전 팔 공통' 정의는 비어 있고,
#   합집합이 '이 코퍼스에서 가장 죽기 쉬운 장'의 전수다. 봉인 시험
#   (rf_split.json test 687)은 조건 선택에 쓰지 않는다 — dev 586 만.
#
# 세 축 신호(전부 사진에서 직접 잰다 — 남의 라벨 요약을 옮기지 않는다):
#   구도 proxy — READING 상자의 이미지 내 상대면적(작다=조연), 상자 중심-
#     이미지 중심 거리(멀다=가장자리). 로보플로우에 기기 라벨은 없어 숫자
#     영역이 기기 크기의 대리 지표다(기기가 작으면 숫자도 작다).
#   열화 — READING 영역 라플라시안 분산(낮다=흐림), 전체 라플라시안 분산,
#     JPEG 바이트율(바이트/화소, 낮다=강압축).
#   이물 후보 — 양자화(4bit RGB) 최빈색 비율(높다=단색 배경=스크린샷·광고
#     신호), 고유색 수(적다=합성·UI 신호). **이물 확정은 사람이 한다** —
#     형제 카드(이물층 태그 규약)가 '무인 루프가 태그 값을 만들지 않는다'로
#     못박았다. 이 자는 후보만 띄운다.
#
# 배정 규칙(우선순위: 이물후보 > 열화 > 구도 — 이물은 다른 신호까지 왜곡):
#   이물후보  dom_ratio ≥ dev p95 또는 n_colors ≤ dev p5
#   열화      lap_reading ≤ p5 또는 bpp ≤ p5
#   구도      area_frac ≤ p5 또는 center_dist ≥ p95
#   불명      어느 극단에도 안 속음(시드 경계 의심)
#
# 사용:
#   conda run -n sugartrain python classify_rf_miss.py
#   (출력: 콘솔 표 + _diag/rf_miss_split.json)
import json
import zipfile
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "upstream" / "roboflow-glucometer-images"
ZIP = ROOT / "Glucometer_images.coco.zip"
EXT = ROOT / "extracted"
EVALS = [HERE / "_diag" / "audit" / f"roboflow_aug_{s}.jsonl" for s in
         ("s5", "s6", "s7")]
SPLIT = HERE / "rf_split.json"
OUT = HERE / "_diag" / "rf_miss_split.json"


def population():
    """(id -> (이미지 경로, READING [x0,y0,x1,y1])). eval_band_roboflow.population
    과 같은 규약(train+valid, READING 있음, 이미지 존재 필터) — 그 쪽은
    module level 에서 torch 를 import 해 여기서 다시 짰다."""
    out = {}
    with zipfile.ZipFile(ZIP) as f:
        for split in ("train", "valid"):
            j = json.loads(f.read(f"{split}/_annotations.coco.json"))
            per = {}
            for a in j["annotations"]:
                per.setdefault(a["image_id"], {})[a["category_id"]] = a["bbox"]
            cats = {c["id"]: c["name"] for c in j["categories"]}
            read_id = next(k for k, v in cats.items() if v == "READING")
            for im in j["images"]:
                d = per.get(im["id"], {})
                if read_id not in d:
                    continue
                p = EXT / split / im["file_name"]
                if not p.exists():
                    continue
                b = d[read_id]
                sid = f"rf/{split}/{Path(im['file_name']).stem}"
                out[sid] = (p, [b[0], b[1], b[0] + b[2], b[1] + b[3]])
    return out


def miss_union_dev():
    """세 평가 팔의 미검출 합집합 ∩ dev."""
    dev = set(json.loads(SPLIT.read_text(encoding="utf-8"))["dev"])
    miss = set()
    per_arm = {}
    for p in EVALS:
        ids = set()
        for l in p.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            if not r.get("det"):
                ids.add(r["id"])
        per_arm[p.stem] = sorted(ids & dev)
        miss |= ids
    return sorted(miss & dev), per_arm


def signals(path, box):
    """한 장의 세 축 신호. box 는 원본 화소 좌표 [x0,y0,x1,y1]."""
    img = cv2.imread(str(path))
    if img is None:
        return None
    H, W = img.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lap_full = cv2.Laplacian(
        cv2.resize(gray, (512, int(512 * H / max(W, 1)))), cv2.CV_64F).var()
    crop = gray[y0:y1, x0:x1]
    lap_read = cv2.Laplacian(crop, cv2.CV_64F).var() if crop.size else 0.0
    bw, bh = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2 / W, (y0 + y1) / 2 / H
    diag = (W ** 2 + H ** 2) ** 0.5 / 2
    center_dist = ((cx - 0.5) * W) ** 2 + ((cy - 0.5) * H) ** 2
    # 4bit 양자화 색 히스토그램 — 스크린샷·광고의 단색 배경 신호
    small = cv2.resize(img, (256, 256), interpolation=cv2.INTER_AREA)
    q = (small >> 4).astype(np.int32)
    key = q[..., 0] * 4096 + q[..., 1] * 64 + q[..., 2]
    hist = np.bincount(key.ravel(), minlength=16 ** 3)
    return {
        "w": W, "h": H,
        "area_frac": round(bw * bh / (W * H), 5),
        "center_dist": round((center_dist ** 0.5) / diag, 4),
        "box_ar": round(bw / max(bh, 1), 3),
        "lap_full": round(float(lap_full), 1),
        "lap_reading": round(float(lap_read), 1),
        "bpp": round(path.stat().st_size / (W * H), 4),
        "dom_color_ratio": round(float(hist.max() / hist.sum()), 4),
        "n_colors": int((hist > (256 * 256 * 0.0005)).sum()),
    }


def pct_rank(dist, v):
    """dist 안에서 v 의 백분위(0~100)."""
    return 100.0 * sum(1 for d in dist if d <= v) / max(len(dist), 1)


def main():
    pop = population()
    targets, per_arm = miss_union_dev()
    print(f"미검출 합집합 ∩ dev = {len(targets)}장 "
          f"(팔별 dev 미검출: "
          + ", ".join(f"{k.split('_')[-1]} {len(v)}" for k, v in per_arm.items())
          + ")")

    # dev 전체 신호 → 분포(백분위 기준). 재는 자는 대상 장과 동일해야 한다.
    all_sig = {}
    for sid, (p, box) in pop.items():
        if sid in json.loads(SPLIT.read_text(encoding="utf-8"))["dev"] \
                or sid in set(targets):
            s = signals(p, box)
            if s:
                all_sig[sid] = s
    dev_sig = {k: v for k, v in all_sig.items()
               if k in set(json.loads(SPLIT.read_text(encoding="utf-8"))
                           ["dev"])}
    keys = ("area_frac", "center_dist", "lap_full", "lap_reading", "bpp",
            "dom_color_ratio", "n_colors")
    dist = {k: [v[k] for v in dev_sig.values()] for k in keys}
    p5 = {k: float(np.percentile(dist[k], 5)) for k in keys}
    p95 = {k: float(np.percentile(dist[k], 95)) for k in keys}
    print(f"dev 분포 n={len(dev_sig)} · p5/p95 기준:")
    for k in keys:
        print(f"  {k:16s} p5={p5[k]:<10g} p95={p95[k]:<10g}")

    rows = []
    for sid in targets:
        s = all_sig.get(sid)
        if s is None:
            rows.append({"id": sid, "assign": "측정불가(디코드 실패)"})
            continue
        r = {k: pct_rank(dist[k], s[k]) for k in keys}
        if s["dom_color_ratio"] >= p95["dom_color_ratio"] \
                or s["n_colors"] <= p5["n_colors"]:
            a = "이물후보(사람 확인 전)"
        elif s["lap_reading"] <= p5["lap_reading"] \
                or s["bpp"] <= p5["bpp"]:
            a = "열화"
        elif s["area_frac"] <= p5["area_frac"] \
                or s["center_dist"] >= p95["center_dist"]:
            a = "구도"
        else:
            a = "불명(시드 경계 의심)"
        rows.append({"id": sid, "signals": s, "pct": r, "assign": a,
                     "path": str(pop[sid][0])})

    # 분할 표
    from collections import Counter
    n = len(rows)
    print("\n== 완전 미검출 3분할 (dev 합집합 기준) ==")
    for a, c in Counter(x["assign"] for x in rows).most_common():
        print(f"  {a:24s} {c:3d}장  {100 * c / n:5.1f}%")
    print(f"  {'합계':24s} {n:3d}장")
    print("\n== 장별 신호(백분위) ==")
    for x in rows:
        if "signals" not in x:
            print(f"  {x['id']}: {x['assign']}")
            continue
        s, r = x["signals"], x["pct"]
        print(f"  {x['assign']:22s} {x['id']}")
        print(f"     면적 {s['area_frac']}(p{r['area_frac']:.0f}) "
              f"중심거리 {s['center_dist']}(p{r['center_dist']:.0f}) "
              f"라플라시안(R) {s['lap_reading']}(p{r['lap_reading']:.0f}) "
              f"bpp {s['bpp']}(p{r['bpp']:.0f}) "
              f"최빈색 {s['dom_color_ratio']}(p{r['dom_color_ratio']:.0f}) "
              f"색수 {s['n_colors']}(p{r['n_colors']:.0f})")

    OUT.write_text(json.dumps(
        {"targets": rows,
         "dev_n": len(dev_sig),
         "arm_miss_dev": per_arm,
         "thresholds": {"p5": p5, "p95": p95}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
