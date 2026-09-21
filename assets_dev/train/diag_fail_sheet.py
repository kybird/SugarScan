# 실패한 장을 **눈으로 본다**. 가설을 세우기 전에.
#
# 왜(2026-09-20): 4번·5번에서 세 팔을 연달아 기각했다. 셋 다 내가 사진을
# 한 장도 안 보고 세운 가설이었다(장면 맥락 · 입력 해상도 · 배율 덮기).
# CLAUDE.md "증상 보고를 받으면 코드보다 현장을 먼저 본다"를 데이터에 대해
# 안 지킨 것이다.
#
# 접촉 인화지를 한 장 만든다. 각 칸에 밴드 주변을 넉넉히 잘라 놓고
#   초록 = 사람 라벨(해당 코퍼스 규약)   빨강 = 숫자 칸(규약에서 역산)
#   노랑 = 배포 상자(예측 + BOX_MARGIN)
# 를 그린다. 판정과 **같은 좌표계**로 그려야 보는 것이 재는 것과 같아진다.
#
# 이미지는 저장소 밖(assets_dev/upstream 정션)에서 읽고 결과는 _diag 에만
# 쓴다. **커밋하지 않는다** — docs/LICENSES.md §1.4.
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from lcd_layout import BAND_MARGIN
from build_cache_v2 import BOX_MARGIN
from report_fail_mix import rows, classify, digit_cell, pad

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="atone")
    ap.add_argument("--dir", default="_diag/tone")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cls", default="일부만", choices=["일부만", "딴 데", "미검출"])
    ap.add_argument("--corpus", default="roboflow", choices=["roboflow", "datumo"])
    ap.add_argument("--split", default="dev")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--cell", type=int, default=320)
    ap.add_argument("--full", action="store_true",
                    help="사진 전체를 보여 준다 — **상자가 사진의 어디인지**를"
                         " 보려면 이쪽. 상자 주변만 자르면 어떤 상자든 칸"
                         " 한가운데에 놓여 전부 중앙으로 보인다.")
    ap.add_argument("--out", default="_diag/fail_sheet.png")
    a = ap.parse_args()

    if a.corpus == "roboflow":
        from eval_band_roboflow import population
        pop = {k: v[0] for k, v in population().items()}
        pfx = "roboflow_"
    else:
        from eval_band_real import population as dpop       # (id -> 경로)
        pop = dpop()
        pfx = ""

    keep = None
    sp = HERE / "rf_split.json"
    if a.corpus == "roboflow" and a.split != "all" and sp.exists():
        keep = set(json.loads(sp.read_text(encoding="utf-8"))[a.split])

    rs = rows(HERE / a.dir / (pfx + f"{a.arm}_s{a.seed}.jsonl"))
    bad = [r for r in rs
           if (keep is None or r["id"] in keep) and classify(r) == a.cls]
    print(f"{a.cls} {len(bad)}장 중 앞 {min(a.n, len(bad))}장을 인화한다")
    bad = bad[:a.n]
    if not bad:
        raise SystemExit("표본 없음")

    C = a.cell
    cols = 4
    rowsn = (len(bad) + cols - 1) // cols
    sheet = np.full((rowsn * C, cols * C, 3), 30, np.uint8)

    for i, r in enumerate(bad):
        p = pop.get(r["id"])
        if p is None:
            continue
        img = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if img is None:
            continue
        g = r["gt"]
        d = digit_cell(g)
        e = pad(r["pred"]) if r.get("det") else None
        # 밴드를 중심으로 넉넉히 잘라 낸다 — 주변에 무엇이 있는지 봐야 한다.
        if a.full:
            x0, y0, x1, y1 = 0, 0, img.shape[1], img.shape[0]
        else:
            cx, cy = (g[0] + g[2]) / 2, (g[1] + g[3]) / 2
            half = max(g[2] - g[0], g[3] - g[1]) * 1.6
            if e is not None:                   # 예측이 밖이면 같이 담는다
                half = max(half, abs(e[0]-cx), abs(e[2]-cx),
                           abs(e[1]-cy), abs(e[3]-cy)) * 1.15
            x0, y0 = int(cx - half), int(cy - half)
            x1, y1 = int(cx + half), int(cy + half)
        px0, py0 = max(0, -x0), max(0, -y0)
        sx0, sy0 = max(0, x0), max(0, y0)
        sx1, sy1 = min(img.shape[1], x1), min(img.shape[0], y1)
        crop = np.full((y1-y0, x1-x0, 3), 30, np.uint8)
        crop[py0:py0+(sy1-sy0), px0:px0+(sx1-sx0)] = img[sy0:sy1, sx0:sx1]
        s = C / max(1, crop.shape[0])
        crop = cv2.resize(crop, (C, C))
        if a.full:
            # 사진 한가운데를 십자로 — "중앙인가"를 눈대중이 아니라
            # 기준선으로 보게 한다.
            cv2.line(crop, (C//2, 0), (C//2, C), (90, 90, 90), 1)
            cv2.line(crop, (0, C//2), (C, C//2), (90, 90, 90), 1)
        def box(b, col, th=2):
            cv2.rectangle(crop, (int((b[0]-x0)*s), int((b[1]-y0)*s)),
                          (int((b[2]-x0)*s), int((b[3]-y0)*s)), col, th)
        box(g, (0, 220, 0))
        box(d, (0, 0, 235))
        if e is not None:
            box(e, (0, 235, 235))
        cv2.putText(crop, r["id"].split("/")[-1][:18], (4, C-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        rr, cc = divmod(i, cols)
        sheet[rr*C:(rr+1)*C, cc*C:(cc+1)*C] = crop

    out = HERE / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), sheet)
    print(f"-> {out}  초록=사람 라벨 · 빨강=숫자 칸 · 노랑=배포 상자")


if __name__ == "__main__":
    main()
