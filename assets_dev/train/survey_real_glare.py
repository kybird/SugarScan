# 실사진에서 반사가 뚜렷한 장을 골라 대지로 묶는다 — 사람이 유형을 눈으로 가른다.
#
# 합성 반사를 고치려면 "실물은 어떤 모양인가" 를 먼저 봐야 하는데, 2,500장을
# 눈으로 넘길 수는 없다. 그래서 **자로 고르고 눈으로 가른다** — 자는 순위만
# 매기고 유형 판정은 하지 않는다.
#
# 고르는 자: 화면 상자 안 밝은 영역의 **최대 내접 반지름**(거리변환 최댓값)을
# 화면 높이로 나눈 값.
#
#   1판은 "밝은 화소의 비율" 이었는데 실패했다(2026-09-16). 상위 30장이 거의
#   전부 **역광 LCD** 였다 — 숫자 획 자체가 포화에 가까우니 비율이 올라간다.
#   반사는 안 걸리고 밝은 화면만 걸렸다. 비율은 '밝다' 를 재지 '반사다' 를
#   재지 않는다.
#
#   획과 반사를 가르는 것은 밝기가 아니라 **두께**다. 7-세그 획은 가늘고
#   반사 얼룩은 뚱뚱하다. 거리변환 최댓값이 그 두께이고, 화면 높이로 나눠야
#   기기 크기에 휘둘리지 않는다.
#
# 이 값으로 반사 '유형'을 말하지 않는다 — 유형은 사람이 대지를 보고 정한다.
#
# 화면 상자는 gm_quads 의 규약을 따른다: 사람 라벨(screen_boxes.jsonl) 우선,
# 없으면 검출기 출력. 그 파일이 이미 단일 출처를 정해 뒀으므로 여기서 다시
# 고르지 않는다.
#
# 사용:
#   python survey_real_glare.py --top 30 --out _diag/real_glare
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
LABELS = DATUMO / "labels.jsonl"
HUMAN = HERE / "screen_boxes.jsonl"
DET = HERE / "gmscreen_quads.jsonl"

BRIGHT = 240        # 이 값 이상을 "포화에 가깝다" 로 본다


def rect(quad):
    q = np.asarray(quad, float)
    return [q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()]


def boxes():
    """사람 라벨 우선, 없으면 검출기 — gm_quads.py 와 같은 규약."""
    out = {}
    for l in Path(DET).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            out[j["id"]] = (rect(j["quad"]), "det")
    for l in Path(HUMAN).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if j.get("source") == "human" and j.get("quad"):
                out[j["id"]] = (rect(j["quad"]), "human")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--out", default=str(HERE / "_diag" / "real_glare"))
    ap.add_argument("--limit", type=int, default=0, help="앞 N 장만 훑는다")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    bx = boxes()
    rows = [json.loads(l) for l in
            LABELS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        rows = rows[:args.limit]

    scored = []
    for k, r in enumerate(rows):
        if r["id"] not in bx:
            continue
        p = DATUMO / r["image"]
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        b, src = bx[r["id"]]
        x0, y0 = max(0, int(b[0])), max(0, int(b[1]))
        x1, y1 = min(img.shape[1], int(b[2])), min(img.shape[0], int(b[3]))
        if x1 - x0 < 16 or y1 - y0 < 16:
            continue
        crop = img[y0:y1, x0:x1]
        mask = (crop >= BRIGHT).astype(np.uint8)
        if mask.any():
            # 거리변환 최댓값 = 밝은 영역에 들어가는 가장 큰 원의 반지름.
            # 가는 획은 작고 뚱뚱한 얼룩은 크다.
            thick = float(cv2.distanceTransform(mask, cv2.DIST_L2, 5).max())
        else:
            thick = 0.0
        scored.append({"id": r["id"], "src": src,
                       "blob": thick / max(crop.shape[0], 1),
                       "bright": float(mask.mean()),
                       "box": [x0, y0, x1, y1]})
        if (k + 1) % 400 == 0:
            print(f"... {k+1}/{len(rows)}", flush=True)

    scored.sort(key=lambda d: -d["blob"])
    v = np.array([d["blob"] for d in scored])
    print(f"훑은 장 {len(scored)} (모집단 {LABELS.name}, 상자 출처 "
          f"human {sum(1 for d in scored if d['src']=='human')} · "
          f"det {sum(1 for d in scored if d['src']=='det')})")
    print(f"밝은 영역 최대 내접 반지름 / 화면 높이: p50 {np.median(v):.4f} · "
          f"p90 {np.percentile(v,90):.4f} · p99 {np.percentile(v,99):.4f} · "
          f"max {v.max():.4f}")

    picks = scored[:args.top]
    (out / "candidates.json").write_text(
        json.dumps(picks, ensure_ascii=False, indent=2), encoding="utf-8")
    sheet(picks, rows, out / "sheet.png")
    print(f"상위 {len(picks)}장 -> {out/'sheet.png'} · {out/'candidates.json'}")
    return 0


def sheet(picks, rows, out_png, cols=6, cell=(420, 420)):
    img_of = {r["id"]: r["image"] for r in rows}
    tiles = []
    for d in picks:
        im = cv2.imread(str(DATUMO / img_of[d["id"]]))
        x0, y0, x1, y1 = d["box"]
        crop = im[y0:y1, x0:x1]
        s = min(cell[0] / crop.shape[1], cell[1] / crop.shape[0])
        crop = cv2.resize(crop, (int(crop.shape[1] * s), int(crop.shape[0] * s)))
        pad = np.zeros((cell[1], cell[0], 3), np.uint8)
        pad[:crop.shape[0], :crop.shape[1]] = crop
        cv2.putText(pad, f"{d['id'].split('/')[1]} blob {d['blob']:.3f}",
                    (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        tiles.append(pad)
    grid = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    w = max(g.shape[1] for g in grid)
    grid = [np.pad(g, ((0, 0), (0, w - g.shape[1]), (0, 0))) for g in grid]
    cv2.imwrite(str(out_png), np.vstack(grid))


if __name__ == "__main__":
    raise SystemExit(main())
