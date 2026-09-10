# G34 3단계 — 검증 스트립(2x2 고해상도) 생성.
#
# 시트 판독은 외형군(body color/shape)은 일관되게 주지만 브랜드 문구는
# 모델이 조건마다 다르게 읽는다(실측: 같은 검정-타원형이 OneTouch Ultra /
# GlucoNeX plus / CUEDIO PAW / GLUCOCARD 로 각각 읽힘). 그래서 브랜드는
# 원본 해상도 스트립으로 교차 검증한다 — 2x2 셀에 긴 변 ~1100px 씩.
#
# 두 용도:
#   A. 거대 성분(c001 565장 · c003 723장) 전이 연쇄 점검(AC #3) —
#      id 정렬 위치를 사분위로 뽑은 표본 4장씩.
#   B. 외형군별 대표 — 시트 판독에서 같은 군으로 모인 성분의 원본.
#
# 산출: _diag/device_tags/verify_NN.png (각 셀에 이미지 id 캡션)
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "_diag" / "device_tags"

CELL = 1120  # 긴 변 상한 — 브랜드 각인이 읽히는 크기


def cell_img(cid, w, h):
    with Image.open(DATUMO / "extracted" / "TILDE" / f"{cid}.jpg") as pil:
        pil.load()
        pil = ImageOps.exif_transpose(pil)
        pil.thumbnail((w - 8, h - 40))
        return cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2BGR)


def strip(items, name):
    """items: [(label, image_id)] 4개 → 2x2 스트립."""
    canvas = np.full((CELL * 2 + 20, CELL * 2 + 20, 3), 25, np.uint8)
    for k, (label, cid) in enumerate(items):
        r, c = divmod(k, 2)
        y0, x0 = r * (CELL + 10), c * (CELL + 10)
        canvas[y0:y0 + 34, x0:x0 + CELL] = (45, 45, 45)
        cv2.putText(canvas, label, (x0 + 8, y0 + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 220, 255), 2, cv2.LINE_AA)
        im = cell_img(cid, CELL, CELL)
        yy, xx = y0 + 38, x0 + 4
        canvas[yy:yy + im.shape[0], xx:xx + im.shape[1]] = im
    cv2.imwrite(str(OUT / name), canvas)
    print(f"  {name}: {[i[1] for i in items]}", flush=True)


def main() -> int:
    comps = json.loads((HERE / "_diag" / "scene_components.json").read_text(
        encoding="utf-8"))

    # A. 거대 성분 사분위 표본 — 연쇄가 다른 기기를 묶었는지 눈으로 본다(AC #3).
    for cid_key in ("c001", "c003"):
        members = comps[cid_key]
        n = len(members)
        picks = [members[0], members[n // 4], members[2 * n // 4], members[-1]]
        strip([(f"{cid_key} q{i} ({n} total)", p) for i, p in enumerate(picks)],
              f"verify_giant_{cid_key}.png")

    # B. 외형군 대표 — 시트 판독에서 군을 대표하는 원본(성분 id, 대표 id).
    groups = [
        ("white", ["c001", "c003", "c002", "c010"]),
        ("white2", ["c013", "c033", "c050", "c084"]),
        ("blackoval", ["c009", "c122", "c161", "c201"]),
        ("blackoval2", ["c241", "c281", "c321", "c361"]),
        ("green", ["c004", "c033", "c238", "c277"]),
        ("blue", ["c013", "c076", "c079", "c324"]),
        ("purple", ["c059", "c283", "c323", "c327"]),
        ("silver", ["c058", "c307", "c309", "c316"]),
    ]
    for gi, (gname, cids) in enumerate(groups, start=1):
        items = []
        for cc in cids:
            members = comps.get(cc)
            if not members:
                print(f"  !! {cc} 없음 — 스킵", flush=True)
                continue
            items.append((f"{cc} ({len(members)})", members[0]))
        if items:
            strip(items, f"verify_grp_{gname}.png")
    print("완료", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
