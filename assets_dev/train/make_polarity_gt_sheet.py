# 극성 정답(사람 라벨) 시트 만들기 — 2026-09-13.
#
# 왜: measure_polarity.polarity_of 의 배경 기준(bg)이 'GM 크롭 전체 중앙값'
# 이라 어두운 베젤이 섞인 기기에서 정상 패널을 반전으로 뒤집는 것으로 보인다
# (diag_polarity_bg.py). 세 후보 정의 중 어느 것이 맞는지 자끼리는 못 가린다 —
# 사람이 찍은 정답이 있어야 정의를 '고르는' 게 아니라 '검증'할 수 있다.
#
# 표본 설계: 30장. 자끼리 판정이 갈린 장 15 + 일치한 장 15.
#   갈린 장만 보면 정의의 분해능은 보이지만 전체 정확도를 못 잰다.
#   일치한 장을 섞어야 '둘 다 틀리는' 구간이 드러난다.
#   한 기기가 표본을 독식하지 않게 기기당 최대 2장으로 제한한다.
#
# 사람에게 보이는 것은 회색조 화면 크롭과 번호뿐이다 — 자의 판정도, 기기
# 이름도 보이지 않는다(블라인드). 회색조인 이유는 자가 보는 것과 같은 입력을
# 사람도 보게 하기 위해서다.
#
#   conda run -n sugartrain python make_polarity_gt_sheet.py
#
# 산출:
#   _diag/polarity_gt/tiles/NN.png     낱장 크롭(확대해서 볼 때)
#   _diag/polarity_gt/sheet_N.png      번호가 찍힌 10장짜리 시트 3장
#   _diag/polarity_gt/_key.jsonl       번호 -> id·기기·자 판정 (사람에게 보이지 않음)
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import measure_polarity as mp  # noqa: E402
from diag_polarity_bg import rows_for  # noqa: E402
from eval_reader import load_gray  # noqa: E402

OUT = HERE / "_diag" / "polarity_gt"
SEED = 7013
PER_DEVICE_MAX = 2
N_FLIP, N_AGREE = 15, 15
TILE_H = 620


def pick(rows):
    rng = random.Random(SEED)
    flip = [r for r in rows if r[6] != r[7]]
    agree = [r for r in rows if r[6] == r[7]]
    rng.shuffle(flip)
    rng.shuffle(agree)

    def take(pool, k):
        seen = defaultdict(int)
        out = []
        for r in pool:
            if seen[r[1]] >= PER_DEVICE_MAX:
                continue
            seen[r[1]] += 1
            out.append(r)
            if len(out) == k:
                break
        return out

    sel = take(flip, N_FLIP) + take(agree, N_AGREE)
    rng.shuffle(sel)          # 갈린 장이 앞에 몰리지 않게 섞는다
    return sel


def crop_of(img_id, pad=0.06):
    quads = crop_of.quads
    g = quads.get(img_id)
    p = mp.UPSTREAM / "extracted" / "TILDE" / (img_id + ".jpg")
    if g is None or not p.exists():
        return None
    img = load_gray(p)
    if img is None:
        return None
    x0, y0, x1, y1 = mp._rect_of(g["quad"])
    w, h = x1 - x0, y1 - y0
    x0 = int(max(0, x0 - w * pad)); y0 = int(max(0, y0 - h * pad))
    x1 = int(min(img.shape[1], x1 + w * pad))
    y1 = int(min(img.shape[0], y1 + h * pad))
    return img[y0:y1, x0:x1]


def main():
    rows = rows_for(set())
    sel = pick(rows)
    crop_of.quads = {r["id"]: r for r in mp._load_jsonl(mp.QUADS_ORIENTED)}
    (OUT / "tiles").mkdir(parents=True, exist_ok=True)
    key, tiles = [], []
    for n, r in enumerate(sel, 1):
        img_id, name = r[0], r[1]
        c = crop_of(img_id)
        if c is None:
            continue
        cv2.imwrite(str(OUT / "tiles" / f"{n:02d}.png"), c)
        key.append(dict(n=n, id=img_id, device=name, ruler_crop_bg=r[6],
                        ruler_band_bg=r[7], p5=r[4], p95=r[5],
                        bg_crop=r[2], bg_band=r[9]))
        tiles.append((n, c))
    with open(OUT / "_key.jsonl", "w", encoding="utf-8") as f:
        for k in key:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")

    for s in range((len(tiles) + 9) // 10):
        group = tiles[s * 10:(s + 1) * 10]
        # 칸은 고정 크기다 — 가로형 한 장이 섞이면 칸 폭이 그 장에 맞춰져
        # 나머지가 우표만 해진다(1차 sheet_3 에서 실제로 그랬다).
        cw = 560
        cells = []
        for n, c in group:
            sc = min(cw / c.shape[1], TILE_H / c.shape[0])
            r = cv2.resize(c, (max(1, int(c.shape[1] * sc)),
                               max(1, int(c.shape[0] * sc))))
            t = np.full((TILE_H, cw), 20, np.uint8)
            oy, ox = (TILE_H - r.shape[0]) // 2, (cw - r.shape[1]) // 2
            t[oy:oy + r.shape[0], ox:ox + r.shape[1]] = r
            t = cv2.cvtColor(t, cv2.COLOR_GRAY2BGR)
            cv2.rectangle(t, (0, 0), (96, 52), (0, 0, 0), -1)
            cv2.putText(t, f"{n:02d}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                        1.4, (0, 240, 255), 3, cv2.LINE_AA)
            cells.append(t)
        canvas = np.full((2 * (TILE_H + 12) + 12, 5 * (cw + 12) + 12, 3),
                         20, np.uint8)
        for i, t in enumerate(cells):
            y = 12 + (i // 5) * (TILE_H + 12)
            x = 12 + (i % 5) * (cw + 12)
            canvas[y:y + TILE_H, x:x + t.shape[1]] = t
        cv2.imwrite(str(OUT / f"sheet_{s + 1}.png"), canvas)
        print(f"sheet_{s + 1}.png  {len(group)}장")
    print(f"낱장 {len(tiles)} -> {OUT / 'tiles'}")
    print(f"정답표(사람에게 보이지 않음) -> {OUT / '_key.jsonl'}")


if __name__ == "__main__":
    main()
