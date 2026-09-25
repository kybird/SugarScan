# 「밴드 밖 엣지 밀도가 어디서 오는가」 — 실사진과 합성의 밀도 격차를 분해한다.
#
# 배경(2026-09-12): 카드「합성 밀도 미달」의 AC 는 합성 패널의 밴드 밖 엣지
# 밀도를 실사진 2.52% 에 맞추라고 요구했다. 그런데 그 두 수치는 다른 물건을
# 잰 값이다 — 실사진은 GM 크롭(기기 몸체 포함)이고 합성은 패널만 그린다.
# 이 스크립트가 그것을 가른다. 자(Canny 50/150, 긴 변 896, 밴드 rect 제외)는
# measure_panel_stats 와 동일하다 — 새로 만들지 않는다.
#
#   tiles    32px 타일로 나눠 '퍼짐(엣지 있는 타일 비율)'과 '뭉침(그 타일 내부
#            밀도)'을 가른다. 질감이면 퍼짐이 높고, 요소면 뭉침이 높다.
#   denoise  medianBlur 5 로 미세 잡음을 죽여 '촬영 질감' 기여분을 뺀다.
#   ring     바깥 테두리 링(기본 15%)과 안쪽을 따로 잰다. 실사진 GM 크롭이
#            기기 몸체를 포함하면 링 쪽이 크게 높다.
#
# 사용:
#   python diag_density_where.py <tiles|denoise|ring> [--images <dir> --manifest <f>]
#   합성 인자를 생략하면 실사진만 잰다.
import argparse
import pathlib

import cv2
import numpy as np

import measure_panel_stats as M

TILE = 32


def _edges(gray, denoise=False):
    g = cv2.medianBlur(gray, 5) if denoise else gray
    return cv2.Canny(cv2.GaussianBlur(g, (3, 3), 0), 50, 150) > 0


def _outside_mask(shape, band_frac):
    H, W = shape
    m = np.ones((H, W), bool)
    x0, y0, x1, y1 = band_frac
    m[int(y0 * H):int(np.ceil(y1 * H)), int(x0 * W):int(np.ceil(x1 * W))] = False
    return m


def stat_tiles(gray, band_frac):
    H, W = gray.shape
    e, m = _edges(gray), _outside_mask(gray.shape, band_frac)
    cov, loc = [], []
    for yy in range(0, H - TILE, TILE):
        for xx in range(0, W - TILE, TILE):
            mm = m[yy:yy + TILE, xx:xx + TILE]
            if mm.sum() < TILE * TILE * 0.9:
                continue
            d = e[yy:yy + TILE, xx:xx + TILE][mm].mean()
            cov.append(d > 0.002)
            if d > 0.002:
                loc.append(d)
    if not cov:
        return None
    return float(np.mean(cov)), float(np.median(loc)) if loc else 0.0


def stat_denoise(gray, band_frac):
    m = _outside_mask(gray.shape, band_frac)
    if m.sum() < 100:
        return None
    return float(_edges(gray)[m].mean()), float(_edges(gray, True)[m].mean())


def stat_ring(gray, band_frac, r=0.15):
    H, W = gray.shape
    e, out = _edges(gray), _outside_mask(gray.shape, band_frac)
    ring = np.zeros((H, W), bool)
    mx, my = int(r * W), int(r * H)
    ring[:my, :] = ring[H - my:, :] = True
    ring[:, :mx] = ring[:, W - mx:] = True
    a, b = out & ring, out & ~ring
    if a.sum() < 100 or b.sum() < 100:
        return None
    return float(e[a].mean()), float(e[b].mean())


def iter_real(with_ids=False):
    """with_ids 면 (id, crop, band_frac) 를 낸다 — 기기 균등 통계용
    (사람 결정 (가) 2026-09-24). 기본 형태는 기존 소비처 불변."""
    quads = {r["id"]: r for r in M._load_jsonl(M.QUADS_ORIENTED)}
    root = M.UPSTREAM / "extracted" / "TILDE"
    for b in M._load_jsonl(M.BAND_BOXES):
        g = quads.get(b["id"])
        if g is None:
            continue
        p = root / (b["id"] + ".jpg")
        if not p.exists():
            continue
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        gx, bx = M._rect_of(g["quad"]), M._rect_of(b["quad"])
        crop = M._crop_by_rect(img, gx)
        if crop is None:
            continue
        gw, gh = gx[2] - gx[0], gx[3] - gx[1]
        item = (crop, ((bx[0] - gx[0]) / gw, (bx[1] - gx[1]) / gh,
                       (bx[2] - gx[0]) / gw, (bx[3] - gx[1]) / gh))
        yield (b["id"], *item) if with_ids else item


def iter_synth(images_dir, manifest):
    imgs = pathlib.Path(images_dir)
    for r in M._load_jsonl(manifest):
        p = imgs / (r["id"] + ".png")
        if not p.exists():
            continue
        g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if g is None:
            continue
        H, W = g.shape
        x0, y0, x1, y1 = M._rect_of(r["quad"])
        yield g, (x0 / W, y0 / H, x1 / W, y1 / H)


FMT = {
    "tiles": ("엣지 있는 타일 비율 median={0:.3f}  그 타일 내부 밀도 median={1:.4f}"),
    "denoise": ("원본 median={0:.4f}  잡음제거 후 median={1:.4f}"),
    "ring": ("바깥 링 median={0:.4f}  안쪽 median={1:.4f}"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("tiles", "denoise", "ring"))
    ap.add_argument("--images")
    ap.add_argument("--manifest")
    ap.add_argument("--ring", type=float, default=0.15)
    a = ap.parse_args()
    fn = {"tiles": stat_tiles, "denoise": stat_denoise,
          "ring": lambda g, b: stat_ring(g, b, a.ring)}[a.cmd]

    sources = [("실사진", iter_real())]
    if a.images and a.manifest:
        sources.append(("합성", iter_synth(a.images, a.manifest)))
    for tag, it in sources:
        vals = [r for r in (fn(g, b) for g, b in it) if r is not None]
        arr = np.asarray(vals)
        print(f"{tag:6s} n={len(arr):3d}  " +
              FMT[a.cmd].format(np.median(arr[:, 0]), np.median(arr[:, 1])))
        if a.cmd == "denoise":
            # 원본 밀도가 0인 장(엣지가 아예 없는 크롭)은 비율이 정의되지
            # 않는다 — 나누면 표본 전체가 nan 이 된다(2026-09-12 실측).
            ok = arr[:, 0] > 0
            if ok.any():
                d = (arr[ok, 0] - arr[ok, 1]) / arr[ok, 0]
                print(f"        질감 기여 median={100 * np.median(d):.1f}% "
                      f"(밀도 0인 {int((~ok).sum())}장 제외)")
            else:
                print("        질감 기여: 잴 수 있는 표본 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
