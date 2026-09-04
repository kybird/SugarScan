# 자동 밴드(숫자 줄) 추출 시제품 — **학습에 쓰기 전에 눈으로 보라고** 만든 것.
#
# 핵심 설계: 밴드를 GM 크롭 '안에서' 찾으면 GM 이 이미 잘라낸 자리는 복구할 수
# 없다. 그래서 **원본 이미지에서 GM 박스를 넓힌 영역**을 뒤진다.
#
# 산출: _diag/autoband/*.png — 왼쪽 GM 크롭(현재 학습 입력) · 오른쪽 자동 밴드
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "_diag" / "autoband"
IN_H, IN_W = 160, 320
MARGIN = 0.12          # GM 박스를 사방으로 12% 넓혀서 뒤진다(잘린 자리 회수용)
PROC_H = 480           # 밴드 탐색용 작업 높이


def load(p, key="quad"):
    d = {}
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            d[j["id"]] = j.get(key)
    return d


def gray_of(cid):
    p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
    with Image.open(p) as pil:
        pil.load()
        pil = ImageOps.exif_transpose(pil)
        return cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)


def bbox(quad):
    a = np.array(quad, dtype=np.float32)
    return [a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()]


def expand(b, W, H, m=MARGIN):
    x0, y0, x1, y1 = b
    dw, dh = (x1 - x0) * m, (y1 - y0) * m
    return [max(0, x0 - dw), max(0, y0 - dh),
            min(W - 1, x1 + dw), min(H - 1, y1 + dh)]


def crop(g, b):
    x0, y0, x1, y1 = [int(round(v)) for v in b]
    return g[y0:y1 + 1, x0:x1 + 1]


def ink_mask(patch):
    """극성 무관 전경 마스크. 국소 대비 기준."""
    blur = cv2.GaussianBlur(patch, (0, 0), max(1, patch.shape[0] / 120))
    med = cv2.medianBlur(blur, 2 * int(patch.shape[0] / 12) + 1)
    diff = blur.astype(np.int16) - med.astype(np.int16)
    return (np.abs(diff) > 22).astype(np.uint8)


def find_band(patch):
    """숫자 줄의 (y0,y1,x0,x1). 못 찾으면 None."""
    h, w = patch.shape
    m = ink_mask(patch)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_RECT,
                                                   (max(3, w // 40), 3)))
    rows = m.sum(axis=1).astype(np.float32)
    if rows.max() <= 0:
        return None
    thr = max(rows.max() * 0.25, w * 0.03)
    on = rows > thr
    runs, s = [], None
    for i, v in enumerate(on):
        if v and s is None:
            s = i
        elif not v and s is not None:
            runs.append((s, i - 1))
            s = None
    if s is not None:
        runs.append((s, len(on) - 1))
    if not runs:
        return None
    # 숫자 줄은 화면에서 가장 '두꺼운' 줄이다(시간·단위 줄보다 크다)
    y0, y1 = max(runs, key=lambda r: r[1] - r[0])
    if y1 - y0 < h * 0.08:
        return None
    cols = m[y0:y1 + 1].sum(axis=0).astype(np.float32)
    cthr = max(cols.max() * 0.12, 1.0)
    idx = np.where(cols > cthr)[0]
    if idx.size == 0:
        return None
    x0, x1 = int(idx.min()), int(idx.max())
    py, px = (y1 - y0) * 0.14, (x1 - x0) * 0.04
    return (max(0, int(y0 - py)), min(h - 1, int(y1 + py)),
            max(0, int(x0 - px)), min(w - 1, int(x1 + px)))


def warp_box(g, b):
    x0, y0, x1, y1 = [float(v) for v in b]
    src = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32)
    dst = np.array([[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1], [0, IN_H - 1]],
                   np.float32)
    return cv2.warpPerspective(g, cv2.getPerspectiveTransform(src, dst),
                               (IN_W, IN_H))


def autoband_box(g, gmquad):
    H, W = g.shape
    eb = expand(bbox(gmquad), W, H)
    patch = crop(g, eb)
    sc = PROC_H / patch.shape[0]
    small = cv2.resize(patch, (max(8, int(patch.shape[1] * sc)), PROC_H),
                       interpolation=cv2.INTER_AREA)
    r = find_band(small)
    if r is None:
        return None
    y0, y1, x0, x1 = [v / sc for v in r]
    return [eb[0] + x0, eb[1] + y0, eb[0] + x1, eb[1] + y1]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    gm = load(HERE / "gmscreen_quads.jsonl")
    scr = load(HERE / "screen_boxes.jsonl")
    readings = load(DATUMO / "labels.jsonl", "reading")

    # 알려진 실패 장을 반드시 포함시킨다 — 잘린 마지막 자리가 회수되는지가 관건
    must = ["glucose_batch1/1614", "glucose_batch1/1091", "glucose_batch1/1622",
            "glucose_batch1/1624", "glucose_batch1/444", "glucose_batch1/236"]
    wide = [c for c in scr if scr[c] and c in gm
            and (np.array(scr[c])[:, 0].ptp() / max(np.array(scr[c])[:, 1].ptp(), 1)) > 1.2]
    picks, seen = [], set()
    for c in must + wide + sorted(gm):
        if c in gm and c not in seen and (DATUMO / "extracted" / "TILDE" / f"{c}.jpg").exists():
            picks.append(c)
            seen.add(c)
        if len(picks) >= 12:
            break

    tiles, ok = [], 0
    for cid in picks:
        g = gray_of(cid)
        gmc = warp_box(g, bbox(gm[cid]))
        ab = autoband_box(g, gm[cid])
        abc = warp_box(g, ab) if ab else np.zeros((IN_H, IN_W), np.uint8)
        ok += ab is not None
        pair = np.hstack([cv2.cvtColor(gmc, cv2.COLOR_GRAY2BGR),
                          np.full((IN_H, 4, 3), (0, 200, 0), np.uint8),
                          cv2.cvtColor(abc, cv2.COLOR_GRAY2BGR)])
        bar = np.full((24, pair.shape[1], 3), 30, np.uint8)
        cv2.putText(bar, f"{cid.split('/')[-1]}  GT {readings.get(cid)}   "
                    f"[left] GM screen   [right] auto band"
                    + ("" if ab else "  (BAND NOT FOUND)"),
                    (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 220, 255), 1,
                    cv2.LINE_AA)
        tiles.append(np.vstack([bar, pair]))

    sheet = np.vstack(tiles)
    p = OUT / "compare.png"
    cv2.imwrite(str(p), sheet)
    print(f"밴드 검출 성공 {ok}/{len(picks)}")
    print("saved", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
