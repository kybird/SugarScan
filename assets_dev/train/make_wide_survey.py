# 가로 화면 비율을 사람이 직접 세기 위한 표본 대지(contact sheet).
#
# 왜 표본인가: 2,512장을 다 볼 필요가 없다. 무작위 200장이면 비율을
# ±5pp 안쪽으로 추정할 수 있고, 세는 시간은 10분대다.
#
# 왜 사람이 세는가: GM 박스로는 못 센다 — 가로 화면을 세로로 접어 잡기
# 때문이다(2382: GM 0.66 vs 사람 2.20). 자동 집계가 곧 과소평가다.
#
# 산출: _diag/wide_survey/sheet_N.png + index.json
# 사용자는 가로로 보이는 번호만 적으면 되고, 비율·신뢰구간은
# tally_wide_survey.py 가 계산한다.
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "_diag" / "wide_survey"

N_SAMPLE = 200
COLS, ROWS = 5, 8          # 한 장에 40개
CELL_W, CELL_H = 380, 300  # LCD 모양을 알아볼 수 있는 최소 크기
SEED = 20260904


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="표본이 아니라 전량으로 대지를 만든다")
    ap.add_argument("--out", default=None, help="산출 폴더 이름(기본 wide_survey)")
    args = ap.parse_args()
    out = HERE / "_diag" / (args.out or ("wide_all" if args.all else "wide_survey"))

    out.mkdir(parents=True, exist_ok=True)
    globals()["OUT"] = out
    ids = []
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if (DATUMO / "extracted" / "TILDE" / f"{j['id']}.jpg").exists():
                ids.append(j["id"])
    ids.sort()
    if args.all:
        pick = ids                      # id 사전순 — 번호가 안정적이라 되짚기 쉽다
    else:
        rng = np.random.RandomState(SEED)
        pick = [ids[i] for i in rng.choice(len(ids), N_SAMPLE, replace=False)]
    OUT = out

    index, sheet, n = [], 0, 0
    per = COLS * ROWS
    for start in range(0, len(pick), per):
        chunk = pick[start:start + per]
        canvas = np.full((ROWS * CELL_H, COLS * CELL_W, 3), 25, np.uint8)
        for k, cid in enumerate(chunk):
            no = start + k + 1
            with Image.open(DATUMO / "extracted" / "TILDE" / f"{cid}.jpg") as pil:
                pil.load()
                pil = ImageOps.exif_transpose(pil)
                pil.thumbnail((CELL_W - 8, CELL_H - 30))
                im = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2BGR)
            r, c = divmod(k, COLS)
            y0, x0 = r * CELL_H, c * CELL_W
            canvas[y0:y0 + 22, x0:x0 + CELL_W] = (45, 45, 45)
            cv2.putText(canvas, f"{no}", (x0 + 6, y0 + 17),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 220, 255), 2,
                        cv2.LINE_AA)
            yy, xx = y0 + 26, x0 + 4
            canvas[yy:yy + im.shape[0], xx:xx + im.shape[1]] = im
            index.append({"no": no, "id": cid})
            n += 1
        sheet += 1
        cv2.imwrite(str(OUT / f"sheet_{sheet}.png"), canvas)
        print(f"  sheet_{sheet}.png  ({len(chunk)}개)")

    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    print(f"\n표본 {n}장 / 전체 {len(ids)}장 · 대지 {sheet}장 → {OUT}")
    print("가로로 보이는 번호를 적어 주면 tally_wide_survey.py 가 비율을 낸다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
