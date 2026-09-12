# 극성·자릿수 실측 — 물리 패널 재구성 카드 AC#10 의 자(2026-09-12).
#
# 카드가 말하는 "극성은 프로파일 속성이다"를 지키려면 어떤 기기가 어두운 화면인지
# 실사진에서 재야 한다. 밴드 라벨 97장(읽기 전용)과 GM 쿼드를 조인해 GM 크롭을
# 만들고, 밴드 영역 잉크가 배경보다 밝으면 반전으로 센다:
#   bg      = GM 크롭 중앙값(패널 바탕이 크롭의 대부분을 차지한다)
#   ink     = 밴드 영역에서 배경에서 더 먼 꼬리(|p95-bg| vs |p5-bg|)
#   inverted = 밝은 꼬리가 더 먼 경우(어두운 화면 · 밝은 숫자)
# 기기 귀속은 device_labels.jsonl(brand+model) 로 붙인다.
#
# 사용:
#   conda run -n sugartrain python measure_polarity.py polarity
#   conda run -n sugartrain python measure_polarity.py digits
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from eval_reader import load_gray  # EXIF 규약 — 저장소 통일 로더

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE.parent / "upstream" / "datumo"
QUADS_ORIENTED = HERE / "gmscreen_quads_oriented.jsonl"   # 읽기 전용
BAND_BOXES = HERE / "band_boxes.jsonl"                    # 읽기 전용
DEVICE_LABELS = HERE / "device_labels.jsonl"
CORPUS_LABELS = UPSTREAM / "labels.jsonl"


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


def polarity_of(crop, band_frac):
    """crop: GM 크롭 gray. band_frac: 밴드 rect 를 크롭 비율로. -> (inverted, contrast)"""
    H, W = crop.shape
    x0, y0 = int(band_frac[0] * W), int(band_frac[1] * H)
    x1, y1 = int(np.ceil(band_frac[2] * W)), int(np.ceil(band_frac[3] * H))
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    band = crop[y0:y1, x0:x1]
    bg = float(np.median(crop.astype(np.float32)))
    p5, p95 = (float(np.percentile(band.astype(np.float32), q)) for q in (5, 95))
    inverted = abs(p95 - bg) > abs(p5 - bg)
    return inverted, abs(p95 - p5)


def cmd_polarity():
    quads = {r["id"]: r for r in _load_jsonl(QUADS_ORIENTED)}
    devices = {r["id"]: r for r in _load_jsonl(DEVICE_LABELS)}
    bands = _load_jsonl(BAND_BOXES)
    per_device = defaultdict(lambda: [0, 0])   # name -> [inverted, n]
    contrast = []
    n_ok = 0
    for b in bands:
        g = quads.get(b["id"])
        if g is None:
            continue
        rel = UPSTREAM / "extracted" / "TILDE" / (b["id"].replace("/", "\\") + ".jpg")
        if not rel.exists():
            rel = UPSTREAM / "extracted" / "TILDE" / (b["id"] + ".jpg")
        if not rel.exists():
            continue
        img = load_gray(rel)
        if img is None:
            continue
        gx0, gy0, gx1, gy1 = _rect_of(g["quad"])
        gw, gh = gx1 - gx0, gy1 - gy0
        crop = img[max(0, int(gy0)):int(gy1), max(0, int(gx0)):int(gx1)]
        if min(crop.shape) < 24:
            continue
        bx0, by0, bx1, by1 = _rect_of(b["quad"])
        frac = ((bx0 - gx0) / gw, (by0 - gy0) / gh,
                (bx1 - gx0) / gw, (by1 - gy0) / gh)
        r = polarity_of(crop, frac)
        if r is None:
            continue
        inverted, c = r
        n_ok += 1
        contrast.append(c)
        d = devices.get(b["id"])
        name = f"{d['brand']} {d['model']}".strip() if d and \
            d.get("status") == "identified" else "(미식별)"
        per_device[name][0] += int(inverted)
        per_device[name][1] += 1
    inv = sum(v[0] for v in per_device.values())
    a = np.asarray(contrast)
    print(f"n={n_ok}  inverted={inv} ({inv / max(1, n_ok) * 100:.1f}%)")
    print(f"밴드 대비 p95-p5 median={np.median(a):.0f} "
          f"p10={np.percentile(a, 10):.0f} min={a.min():.0f}  (<40: "
          f"{np.mean(a < 40) * 100:.1f}%)")
    print("-- 기기별 (n>=2 만, 반전률 내림차순) --")
    for name, (i, n) in sorted(per_device.items(), key=lambda kv: -kv[1][0]):
        if n >= 2:
            print(f"  {name:28s} n={n:3d}  inverted={i / n * 100:5.1f}%")
    mix = [(name, i, n) for name, (i, n) in per_device.items()]
    dark = [name for name, i, n in mix if n >= 2 and i / n >= 0.5]
    print("-- 반전 우세 기기(반전률>=50%) --")
    for name in dark:
        print(f"  {name}")


def cmd_digits():
    rows = _load_jsonl(CORPUS_LABELS)
    r = np.asarray([row["reading"] for row in rows])
    print(f"n={len(r)} min={r.min()} max={r.max()}")
    for lo, hi in ((10, 99), (100, 999)):
        m = ((r >= lo) & (r <= hi)).sum()
        print(f"  {lo}~{hi}: {m} ({m / len(r) * 100:.1f}%)")


def cmd_synth_polarity(images_dir, manifest):
    """합성 패널의 극성·밴드 대비 — 실사진과 같은 polarity_of 로 잰다.
    합성은 패널만 렌더하므로 crop = 이미지 전체, band = manifest quad 의 bbox.
    자를 새로 짜지 않는 것이 요점이다(2026-09-12 밀도 사고 —
    [[ad-hoc-ruler-beside-the-committed-one]])."""
    import cv2
    imgs = Path(images_dir)
    inv, contrast = [], []
    for r in _load_jsonl(manifest):
        p = imgs / (r["id"] + ".png")
        if not p.exists():
            continue
        g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if g is None:
            continue
        H, W = g.shape
        x0, y0, x1, y1 = _rect_of(r["quad"])
        out = polarity_of(g, (x0 / W, y0 / H, x1 / W, y1 / H))
        if out is None:
            continue
        inv.append(out[0])
        contrast.append(out[1])
    a = np.asarray(contrast)
    print(f"n={len(a)}  inverted={sum(inv)} ({100 * np.mean(inv):.1f}%)")
    print(f"밴드 대비 p95-p5 median={np.median(a):.0f} "
          f"p10={np.percentile(a, 10):.0f} p90={np.percentile(a, 90):.0f} "
          f"min={a.min():.0f}  (<40: {100 * np.mean(a < 40):.1f}%)")


def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "polarity"
    if cmd == "polarity":
        cmd_polarity()
    elif cmd == "synth-polarity":
        if len(sys.argv) < 4:
            print("사용: measure_polarity.py synth-polarity <images_dir> <manifest>",
                  file=sys.stderr)
            return 2
        cmd_synth_polarity(sys.argv[2], sys.argv[3])
    else:
        cmd_digits()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
