# G34 2단계 — 성분 대표 710장의 컨택트 시트.
#
# 「촬영 장면 성분에 기종을 태깅한다」 카드의 AC #2. 성분마다 대표 1장
# (사전순 첫 장 — 무작위 금지, 재실행마다 같은 시트가 나와야 사람이 검토를
# 이어갈 수 있다)을 뽑아 대지에 담는다. 셀에는 component_id · 대표 id ·
# 성분 크기를 캡션으로 단다. LCD 크롭이 아니라 **원본 전체** 를 넣는다 —
# 기종은 화면이 아니라 몸통과 브랜드 각인에서 읽힌다.
#
# 산출: _diag/device_tags/sheet_NN.png (5열×8행=40셀, 18장) + index.json
# 관례는 make_wide_survey.py 를 따른다(EXIF 적용·cv2 캡션·결정적 순서).
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "_diag" / "device_tags"

COLS, ROWS = 5, 8           # 한 장에 40성분
CELL_W, CELL_H = 400, 340   # 기기 몸통이 드러나는 최소 크기 (와이드 서베이 관례 + 여유)
CAP_H = 44                  # 캡션 2줄 (성분·대표 / 크기)


def main() -> int:
    comps = json.loads((HERE / "_diag" / "scene_components.json").read_text(
        encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    reps = []  # (component_id, rep_id, size)
    for cid in sorted(comps):
        members = comps[cid]
        reps.append((cid, members[0], len(members)))

    index, sheet = [], 0
    for start in range(0, len(reps), COLS * ROWS):
        chunk = reps[start:start + COLS * ROWS]
        canvas = np.full((ROWS * CELL_H, COLS * CELL_W, 3), 25, np.uint8)
        for k, (cid, rep, size) in enumerate(chunk):
            with Image.open(DATUMO / "extracted" / "TILDE" / f"{rep}.jpg") as pil:
                pil.load()
                pil = ImageOps.exif_transpose(pil)
                pil.thumbnail((CELL_W - 8, CELL_H - CAP_H - 10))
                im = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2BGR)
            r, c = divmod(k, COLS)
            y0, x0 = r * CELL_H, c * CELL_W
            canvas[y0:y0 + CAP_H, x0:x0 + CELL_W] = (45, 45, 45)
            # 줄1: 성분 id + 크기 / 줄2: 대표 이미지 id (사람이 되짚는 열쇠)
            cv2.putText(canvas, f"{cid}  {size}", (x0 + 6, y0 + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 220, 255), 2,
                        cv2.LINE_AA)
            cv2.putText(canvas, rep.replace("glucose_batch1/", "b1/"),
                        (x0 + 6, y0 + 38), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (200, 200, 200), 1, cv2.LINE_AA)
            yy, xx = y0 + CAP_H + 4, x0 + 4
            canvas[yy:yy + im.shape[0], xx:xx + im.shape[1]] = im
            index.append({"component": cid, "rep": rep, "size": size,
                          "sheet": sheet + 1, "cell": k})
        sheet += 1
        cv2.imwrite(str(OUT / f"sheet_{sheet:02d}.png"), canvas)
        print(f"  sheet_{sheet:02d}.png ({len(chunk)}성분)", flush=True)

    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n대표 {len(reps)}장 / 성분 {len(comps)}개 · 대지 {sheet}장 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
