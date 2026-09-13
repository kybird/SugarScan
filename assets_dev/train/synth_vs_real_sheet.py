# 합성과 실사진을 사람이 눈으로 견주는 시트.
#
# 지표가 다 통과해도 합성이 실물과 달라 보일 수 있다. 그 판단은 사람이 한다.
# 이 스크립트는 판단에 필요한 그림만 만든다 — 결론을 내지 않는다.
#
# 세 가지 모드:
#   pair     실사진과 합성을 위아래로 나란히. 층(세로/가로)을 고정한다
#   blind    둘을 섞고 정답을 감춘다. 구분이 되면 그 단서가 곧 결함이다
#            (정답은 --answer 로 따로 출력)
#   contrast 대비 구간별 합성 표본 — 저대비 표본을 사람이 읽을 수 있는지
#
# 실사진은 GM 크롭(gmscreen_quads_oriented + band_boxes join), 합성은
# synth_panel.py gen 산출물. 둘 다 같은 물건이어야 한다는 것이 전제다.
# 자를 새로 만들지 않는다 — measure_panel_stats 의 로더·크롭을 쓴다.
#
# 사용:
#   python synth_vs_real_sheet.py pair --layer wide --images <dir>/images --manifest <dir>/manifest.jsonl
#   python synth_vs_real_sheet.py blind --n 16 --images … --manifest …
#   python synth_vs_real_sheet.py contrast --images … --manifest …
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np

import measure_panel_stats as M
import measure_polarity as MP

HERE = Path(__file__).resolve().parent
OUT = HERE / "_diag" / "synth_vs_real"
TILE_W = 240
SEED = 20260913


def _tile(gray, caption, quad=None, color=(0, 255, 0)):
    h = max(1, int(gray.shape[0] * TILE_W / gray.shape[1]))
    vis = cv2.cvtColor(cv2.resize(gray, (TILE_W, h)), cv2.COLOR_GRAY2BGR)
    if quad is not None:
        s = np.array([TILE_W / gray.shape[1], h / gray.shape[0]], np.float32)
        q = (np.asarray(quad, np.float32) * s).reshape(-1, 1, 2).astype(np.int32)
        cv2.polylines(vis, [q], True, color, 2)
    vis = cv2.copyMakeBorder(vis, 20, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    if caption:
        cv2.putText(vis, caption, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (255, 255, 255), 1)
    return vis


def _grid(tiles, cols, path):
    if not tiles:
        print("표본 없음")
        return
    h = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0,
                                cv2.BORDER_CONSTANT, value=(40, 40, 40))
             for t in tiles]
    while len(tiles) % cols:
        tiles.append(np.full_like(tiles[0], 40))
    rows = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.vstack(rows))
    print(f"→ {path}")


def real_crops(layer, limit):
    """실사진 GM 크롭 — (gray, band_quad_in_crop, id). 층으로 거른다."""
    quads = {r["id"]: r for r in M._load_jsonl(M.QUADS_ORIENTED)}
    root = M.UPSTREAM / "extracted" / "TILDE"
    out = []
    for b in M._load_jsonl(M.BAND_BOXES):
        g = quads.get(b["id"])
        if g is None:
            continue
        p = root / (b["id"] + ".jpg")
        if not p.exists():
            continue
        gx = M._rect_of(g["quad"])
        gw, gh = gx[2] - gx[0], gx[3] - gx[1]
        lay = "portrait" if gw / gh < 1.0 else "wide"
        if layer != "all" and lay != layer:
            continue
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        crop = M._crop_by_rect(img, gx)
        if crop is None:
            continue
        s = crop.shape[1] / gw
        q = (np.asarray(b["quad"], np.float32) - [gx[0], gx[1]]) * s
        out.append((crop, q, b["id"].split("/")[-1]))
        if len(out) >= limit:
            break
    return out


def synth_panels(images, manifest, layer, limit):
    imgs = Path(images)
    out = []
    for r in M._load_jsonl(manifest):
        lay = "portrait" if r["w"] / r["h"] < 1.0 else "wide"
        if layer != "all" and lay != layer:
            continue
        p = imgs / (r["id"] + ".png")
        if not p.exists():
            continue
        g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if g is None:
            continue
        out.append((g, np.asarray(r["quad"], np.float32), r["profile"]))
        if len(out) >= limit:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("pair", "blind", "contrast"))
    ap.add_argument("--layer", choices=("portrait", "wide", "all"), default="all")
    ap.add_argument("--images", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--n", type=int, default=8, help="각 쪽 장수")
    ap.add_argument("--no-quad", action="store_true", help="쿼드 오버레이 끄기")
    ap.add_argument("--answer", action="store_true", help="blind 정답 출력")
    a = ap.parse_args()
    rng = random.Random(SEED)
    qflag = None if a.no_quad else True

    if a.mode == "pair":
        R = real_crops(a.layer, a.n)
        S = synth_panels(a.images, a.manifest, a.layer, a.n)
        tiles = [_tile(g, f"real {i}", q if qflag else None, (0, 255, 0))
                 for g, q, i in R]
        tiles += [_tile(g, f"synth {i[:16]}", q if qflag else None, (0, 200, 255))
                  for g, q, i in S]
        print(f"실사진 {len(R)}장 / 합성 {len(S)}장 — 위가 실사진, 아래가 합성")
        _grid(tiles, a.n, OUT / f"pair_{a.layer}.png")

    elif a.mode == "blind":
        R = [(g, q, "R", i) for g, q, i in real_crops(a.layer, a.n)]
        S = [(g, q, "S", i) for g, q, i in synth_panels(a.images, a.manifest,
                                                        a.layer, a.n)]
        both = R + S
        rng.shuffle(both)
        tiles = [_tile(g, str(k + 1), q if qflag else None, (0, 255, 255))
                 for k, (g, q, _, _) in enumerate(both)]
        print(f"블라인드 {len(both)}장 — 어느 것이 합성인지 맞춰 보라. "
              f"구분이 되면 그 단서가 곧 결함이다")
        _grid(tiles, 4, OUT / f"blind_{a.layer}.png")
        if a.answer:
            print("정답:", " ".join(f"{k+1}:{t}" for k, (_, _, t, _) in
                                    enumerate(both)))
        else:
            print("정답을 보려면 --answer 를 붙여 다시 실행하라")

    else:  # contrast
        imgs = Path(a.images)
        rows = M._load_jsonl(a.manifest)
        buckets = {(0, 40): [], (40, 60): [], (60, 80): [], (80, 120): [],
                   (120, 999): []}
        for r in rows:
            p = imgs / (r["id"] + ".png")
            if not p.exists():
                continue
            g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if g is None:
                continue
            H, W = g.shape
            x0, y0, x1, y1 = M._rect_of(r["quad"])
            o = MP.polarity_of(g, (x0 / W, y0 / H, x1 / W, y1 / H))
            if o is None:
                continue
            for (lo, hi), v in buckets.items():
                if lo <= o[1] < hi and len(v) < 3:
                    v.append((g, np.asarray(r["quad"], np.float32),
                              f"대비 {o[1]:.0f}"))
        tiles = []
        for (lo, hi), v in buckets.items():
            for g, q, c in v:
                tiles.append(_tile(g, c, q if qflag else None, (0, 200, 255)))
        print("대비 구간별 합성 표본(구간당 3장, 낮은 대비부터). "
              "가장 흐린 줄을 사람이 읽을 수 있는지가 열화 상한의 질문이다")
        _grid(tiles, 3, OUT / "contrast_buckets.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
