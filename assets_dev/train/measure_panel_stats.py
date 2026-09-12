# 물리 패널 재구성 카드 — 실측 기준선 스크립트 (2026-09-12).
#
# 세 축을 직접 잰다(보고서 수치는 남이 쓴 것을 옮기지 않는다 — 원본을 본다):
#   1) 종횡비 — GM 박스(물리 패널) w/h 분포. 표시 좌표계(oriented) 기준.
#      raw 좌표계는 EXIF 미적용이라 83.5% 가 세로 회전 상태 → w/h 뒤집힘.
#   2) 밴드 기하 — 사람 밴드 라벨(97장, 읽기 전용)과 GM 쿼드를 id 조인해
#      밴드가 패널에서 차지하는 폭·높이 비율과 위치를 잰다. 세로/가로 패널별로.
#   3) 밀도 — 숫자 영역(밴드) 밖 Canny 엣지 밀도. 실사진 GM 크롭 vs 합성 패널을
#      같은 자로: 긴 변 896 리사이즈 → (3,3) 블러 → Canny(50,150) →
#      밴드 bbox 밖 픽셀 중 엣지 픽셀 비율.
#
# 사용:
#   conda run -n sugartrain python measure_panel_stats.py aspect
#   conda run -n sugartrain python measure_panel_stats.py band
#   conda run -n sugartrain python measure_panel_stats.py density --limit 97
#   conda run -n sugartrain python measure_panel_stats.py synth-density \
#       --images <dir> --manifest <jsonl>
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE.parent / "upstream" / "datumo"
QUADS_ORIENTED = HERE / "gmscreen_quads_oriented.jsonl"   # 읽기 전용 사본(보고서에 md5 기록)
BAND_BOXES = HERE / "band_boxes.jsonl"                    # git 추적, 읽기 전용
LONG_SIDE = 896        # 카드 AC#7 — 패널 긴 변


def _load_jsonl(p):
    rows = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _rect_of(quad):
    q = np.asarray(quad, np.float64)
    return q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()


def cmd_aspect():
    rows = _load_jsonl(QUADS_ORIENTED)
    ratios = []
    for r in rows:
        x0, y0, x1, y1 = _rect_of(r["quad"])
        ratios.append((x1 - x0) / max(1.0, y1 - y0))
    a = np.asarray(ratios)
    pct = lambda q: float(np.percentile(a, q))
    print(f"n={len(a)}")
    print(f"w/h median={np.median(a):.3f} p10={pct(10):.3f} p90={pct(90):.3f} "
          f"p5={pct(5):.3f} p95={pct(95):.3f}")
    print(f"portrait(w/h<1)={np.mean(a < 1.0) * 100:.1f}%  "
          f"wide(w/h>1)={np.mean(a > 1.0) * 100:.1f}%  "
          f"very-wide(w/h>2)={np.mean(a > 2.0) * 100:.1f}%")
    # 히스토그램(0.1 간격) — 렌더 샘플러 설계용 원본 분포
    hist, edges = np.histogram(a, bins=np.arange(0.0, 3.05, 0.1))
    for h, e in zip(hist, edges):
        if h:
            print(f"  [{e:.1f},{e + 0.1:.1f}) {h:5d} {'#' * int(h / 10)}")


def cmd_band():
    quads = {r["id"]: r for r in _load_jsonl(QUADS_ORIENTED)}
    bands = _load_jsonl(BAND_BOXES)
    joined = 0
    stats = {"portrait": [], "wide": []}
    pos = {"portrait": [], "wide": []}
    for b in bands:
        g = quads.get(b["id"])
        if g is None:
            continue
        joined += 1
        gx0, gy0, gx1, gy1 = _rect_of(g["quad"])
        bx0, by0, bx1, by1 = _rect_of(b["quad"])
        gw, gh = gx1 - gx0, gy1 - gy0
        bw, bh = bx1 - bx0, by1 - by0
        key = "portrait" if gw / gh < 1.0 else "wide"
        stats[key].append((bw / gw, bh / gh))
        pos[key].append(((bx0 + bx1) / 2 - gx0) / gw)   # 밴드 중심 x (패널 좌 frac)
        pos[key].append(0)                                # 자리 표시(아래에서 y 따로)
        pos[key][-1] = ((by0 + by1) / 2 - gy0) / gh
    print(f"join={joined}/{len(bands)}")
    _report_band(stats, pos)


def _report_band(stats, pos):
    """밴드 기하 출력 — 실사진(cmd_band)과 합성(cmd_synth_band)이 이 한 코드로
    찍는다. 자가 갈리면 두 수치는 비교 대상이 아니다(2026-09-12 밀도 사고)."""
    for key in ("portrait", "wide"):
        if not stats[key]:
            print(f"{key}: 표본 없음")
            continue
        a = np.asarray(stats[key])
        n = len(a)
        cx = np.asarray(pos[key][0::2])
        cy = np.asarray(pos[key][1::2])
        p = lambda arr, q: float(np.percentile(arr, q))
        print(f"{key} n={n}")
        print(f"  band_w/panel_w median={np.median(a[:, 0]):.3f} "
              f"[p10={p(a[:, 0], 10):.3f} p90={p(a[:, 0], 90):.3f}]")
        print(f"  band_h/panel_h median={np.median(a[:, 1]):.3f} "
              f"[p10={p(a[:, 1], 10):.3f} p90={p(a[:, 1], 90):.3f}]")
        print(f"  band_cx median={np.median(cx):.3f} [p10={p(cx, 10):.3f} "
              f"p90={p(cx, 90):.3f}]")
        print(f"  band_cy median={np.median(cy):.3f} [p10={p(cy, 10):.3f} "
              f"p90={p(cy, 90):.3f}]")


def cmd_synth_band(manifest):
    """합성 패널의 종횡비·밴드 기하 — 실사진과 같은 정의로 잰다.
    패널 = 이미지 전체(합성은 패널만 렌더한다), 밴드 = manifest quad 의 bbox."""
    rows = _load_jsonl(manifest)
    stats = {"portrait": [], "wide": []}
    pos = {"portrait": [], "wide": []}
    asp = []
    for r in rows:
        W, H = r["w"], r["h"]
        q = np.asarray(r["quad"], np.float64)
        bx0, by0 = q[:, 0].min(), q[:, 1].min()
        bx1, by1 = q[:, 0].max(), q[:, 1].max()
        asp.append(W / H)
        key = "portrait" if W / H < 1.0 else "wide"
        stats[key].append(((bx1 - bx0) / W, (by1 - by0) / H))
        pos[key].append((bx0 + bx1) / 2 / W)
        pos[key].append((by0 + by1) / 2 / H)
    a = np.asarray(asp)
    print(f"n={len(a)}")
    print(f"w/h median={np.median(a):.3f} p10={np.percentile(a, 10):.3f} "
          f"p90={np.percentile(a, 90):.3f}")
    print(f"portrait(w/h<1)={np.mean(a < 1.0) * 100:.1f}%  "
          f"wide(w/h>1)={np.mean(a > 1.0) * 100:.1f}%  "
          f"very-wide(w/h>2)={np.mean(a > 2.0) * 100:.1f}%")
    _report_band(stats, pos)


def _crop_by_rect(img, rect, long_side=LONG_SIDE):
    x0, y0, x1, y1 = rect
    x0, y0 = max(0, int(round(x0))), max(0, int(round(y0)))
    x1, y1 = min(img.shape[1], int(round(x1))), min(img.shape[0], int(round(y1)))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    crop = img[y0:y1, x0:x1]
    s = long_side / max(crop.shape)
    return cv2.resize(crop, (max(8, int(round(crop.shape[1] * s))),
                             max(8, int(round(crop.shape[0] * s)))),
                      interpolation=cv2.INTER_AREA)


def edge_density_outside(gray, band_rect_frac, exclude_frame=0.0):
    """gray: 긴 변 896 정규화 크롭. band_rect_frac: (x0,y0,x1,y1) 를 0~1 비율로.
    exclude_frame>0 이면 양변에서 그 비율만큼 외곽 프레임을 마스크에서 뺀다 —
    베젤 테두리 엣지가 content 밀도를 대신하지 못하게(2026-09-12 파일럿에서
    테두리만으로 3.2% 가 나와 floor 가 허위 통과한 뒤 정정)."""
    H, W = gray.shape
    b = cv2.GaussianBlur(gray, (3, 3), 0)
    e = cv2.Canny(b, 50, 150)
    m = np.ones((H, W), bool)
    x0, y0, x1, y1 = band_rect_frac
    m[int(y0 * H):int(np.ceil(y1 * H)), int(x0 * W):int(np.ceil(x1 * W))] = False
    if exclude_frame > 0:
        mx, my = int(exclude_frame * W), int(exclude_frame * H)
        m[:my, :] = False
        m[H - my:, :] = False
        m[:, :mx] = False
        m[:, W - mx:] = False
    if m.sum() < 100:
        return None
    return float((e > 0)[m].mean())


def cmd_density(limit, frame_exc):
    quads = {r["id"]: r for r in _load_jsonl(QUADS_ORIENTED)}
    bands = _load_jsonl(BAND_BOXES)
    vals = []
    roots = [UPSTREAM / "extracted" / "TILDE"]
    n_ok = 0
    for b in bands[:limit] if limit else bands:
        g = quads.get(b["id"])
        if g is None:
            continue
        rel = None
        for root in roots:
            p = root / (b["id"].replace("/", "\\") + ".jpg")
            p2 = root / (b["id"].replace("/", "/") + ".jpg")
            if p.exists():
                rel = p
                break
            if p2.exists():
                rel = p2
                break
        if rel is None:
            continue
        img = cv2.imread(str(rel), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        gx = _rect_of(g["quad"])
        crop = _crop_by_rect(img, gx)
        if crop is None:
            continue
        # 밴드 rect 를 크롭 좌표계 비율로
        bx = _rect_of(b["quad"])
        gw, gh = gx[2] - gx[0], gx[3] - gx[1]
        frac = ((bx[0] - gx[0]) / gw, (bx[1] - gx[1]) / gh,
                (bx[2] - gx[0]) / gw, (bx[3] - gx[1]) / gh)
        d = edge_density_outside(crop, frac, exclude_frame=frame_exc)
        if d is not None:
            vals.append(d)
            n_ok += 1
    a = np.asarray(vals)
    print(f"n={n_ok} frame_exc={frame_exc}")
    print(f"density median={np.median(a):.4f} p10={np.percentile(a, 10):.4f} "
          f"p90={np.percentile(a, 90):.4f} min={a.min():.4f} max={a.max():.4f}")


def cmd_synth_density(images_dir, manifest, frame_exc):
    imgs = Path(images_dir)
    rows = _load_jsonl(manifest)
    vals = []
    for r in rows:
        p = imgs / (r["id"] + ".png")
        if not p.exists():
            continue
        gray = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        q = np.asarray(r["quad"], np.float64)
        x0, y0 = q[:, 0].min(), q[:, 1].min()
        x1, y1 = q[:, 0].max(), q[:, 1].max()
        H, W = gray.shape
        frac = (x0 / W, y0 / H, x1 / W, y1 / H)
        d = edge_density_outside(gray, frac, exclude_frame=frame_exc)
        if d is not None:
            vals.append(d)
    a = np.asarray(vals)
    print(f"n={len(a)} frame_exc={frame_exc}")
    print(f"density median={np.median(a):.4f} p10={np.percentile(a, 10):.4f} "
          f"p90={np.percentile(a, 90):.4f} min={a.min():.4f} max={a.max():.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["aspect", "band", "density", "synth-density",
                                    "synth-band"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--frame-exc", type=float, default=0.0)
    ap.add_argument("--images")
    ap.add_argument("--manifest")
    a = ap.parse_args()
    if a.cmd == "aspect":
        cmd_aspect()
    elif a.cmd == "band":
        cmd_band()
    elif a.cmd == "density":
        cmd_density(a.limit, a.frame_exc)
    elif a.cmd == "synth-band":
        if not a.manifest:
            print("--manifest 가 필요하다", file=sys.stderr)
            return 2
        cmd_synth_band(a.manifest)
    else:
        if not (a.images and a.manifest):
            print("--images 와 --manifest 가 필요하다", file=sys.stderr)
            return 2
        cmd_synth_density(a.images, a.manifest, a.frame_exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
