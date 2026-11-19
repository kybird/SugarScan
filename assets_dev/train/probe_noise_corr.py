# 2026-11-19 — 노이즈 공간 상관 측정(자).
#
# 가설: 렌더 그레인은 픽셱 iid 가우시안, 실촬 센서 노이즈는 디모자이크를
# 거쳐 공간 상관이 있다(GT329 '디더링처럼 픽셀 혼재' 관찰). 이 축을
# 만들기 전에 자로 확인한다 — 실촉 faint 사진과 합성 저대비 프레임의
# 고주파 잔차 자기상관(lag 1~4, 가로·세로)을 잰다. iid 면 lag≥1 에서
# ≈0, 상관 노이즈면 lag 1~2 에서 뚜렷한 피크.
#
#   python probe_noise_corr.py
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from probe_conf_rules import LABELS, load_oriented  # noqa: E402


def acorr(resid, axis, lag):
    """잔차의 정규화 자기상관 — axis 0=세로 lag, 1=가로 lag."""
    if axis == 1:
        a, b = resid[:, :-lag], resid[:, lag:]
    else:
        a, b = resid[:-lag, :], resid[lag:, :]
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def measure(patch):
    """패치 잔차(고역통과)의 자기상관 프로파일."""
    g = cv2.GaussianBlur(patch.astype(np.float32), (0, 0), 1.5)
    r = patch.astype(np.float32) - g
    return {"h1": acorr(r, 1, 1), "h2": acorr(r, 1, 2), "h4": acorr(r, 1, 4),
            "v1": acorr(r, 0, 1), "v2": acorr(r, 0, 2), "v4": acorr(r, 0, 4)}


def main():
    # ── 실촉: faint 태그 값 사진의 밴드 주변 패치 ─────────────────────────
    labs = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labs[j["id"].split("/", 1)[1].rsplit(".", 1)[0]] = j
    faint = [(stem, j) for stem, j in labs.items()
             if j.get("faint") and j.get("value") is not None]
    print(f"faint 태그 값 사진: {len(faint)}건")
    real = []
    for stem, j in faint:
        img = load_oriented(stem)
        q = np.array(j["quad"]) if j.get("quad") else None
        if q is None:
            continue
        x0, x1 = int(q[:, 0].min()), int(q[:, 0].max())
        y0, y1 = int(q[:, 1].min()), int(q[:, 1].max())
        # 밴드 바로 아래 96px 띠(숫자 없는 LCD 영역) — 디지털 획 오염 회피
        py0 = min(img.shape[0], y1 + 6)
        py1 = min(img.shape[0], y1 + 102)
        px0 = max(0, x0)
        px1 = min(img.shape[1], x1)
        if py1 - py0 < 48 or px1 - px0 < 96:
            continue
        real.append(measure(img[py0:py1, px0:px1]))
    print(f"측정 가능: {len(real)}건")
    for k in ("h1", "h2", "h4", "v1", "v2", "v4"):
        v = [r[k] for r in real]
        print(f"  실촉 {k}: 중앙 {np.median(v):+.3f} "
              f"(범위 {np.min(v):+.3f}~{np.max(v):+.3f})")

    # ── 합성: GEN9_READER 저대비 프레임의 같은 위치 패치 ──────────────────
    mf = [json.loads(l) for l in
          (HERE / "synth_coco" / "GEN9_READER" / "manifest.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    pos = [m for m in mf if m.get("has_band", 1) and m.get("box")]
    # 밴드 대비 재서 저대비(그레인 실제 적용된) 행 선별
    picked = []
    import random
    rng = random.Random(7)
    for m in rng.sample(pos, min(400, len(pos))):
        p = HERE / "synth_coco" / "GEN9_READER" / "train2017" / f"{m['id']}.png"
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        b = m["box"]
        band = img[int(b[1]):int(b[3]), int(b[0]):int(b[2])]
        if band.size < 500:
            continue
        c = np.percentile(band, 95) - np.percentile(band, 5)
        if c < 45:                      # c_deg 0.40·255 ≈ 102? → 낮게 잡아
            picked.append((m, img))
        if len(picked) >= 12:
            break
    print(f"합성 저대비 프레임: {len(picked)}건")
    syn = []
    for m, img in picked:
        b = m["box"]
        y1 = int(b[3])
        py0 = min(img.shape[0], y1 + 2)
        py1 = min(img.shape[0], y1 + 70)
        px0 = max(0, int(b[0]))
        px1 = min(img.shape[1], int(b[2]))
        if py1 - py0 < 40 or px1 - px0 < 80:
            continue
        syn.append(measure(img[py0:py1, px0:px1]))
    for k in ("h1", "h2", "h4", "v1", "v2", "v4"):
        v = [r[k] for r in syn]
        print(f"  합성 {k}: 중앙 {np.median(v):+.3f} "
              f"(범위 {np.min(v):+.3f}~{np.max(v):+.3f})")


if __name__ == "__main__":
    main()
