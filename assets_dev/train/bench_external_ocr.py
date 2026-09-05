# 외부 범용 OCR 을 우리 holdout 으로 잰다 — 우리 파이프라인과 같은 잣대로.
#
# 왜 재는가: `IMPLEMENTATION_PLAN.md` D-2 는 "7-세그먼트는 상태 공간이 유한해
# 학습 모델이 과잉"이라며 EasyOCR 을 규칙 판독기로 대체했다. 그 전제가 틀렸다 —
# **숫자의** 상태 공간은 유한하지만 **사진의** 상태 공간은 무한하다(조명·각도·
# 반사·기종). 오늘 실패한 35건이 전부 후자다. 그러니 다시 재는 것이 맞다.
#
# 두 조건으로 잰다:
#   crop  우리 GM 박스+여유로 자른 320x160 — **판독력만** 비교
#   full  원본 전체 — 검출까지 포함. 오늘 오류의 66% 가 검출 문제이므로
#         범용 텍스트 검출이 그걸 건너뛰는지가 진짜 질문이다
#
# 라이선스: EasyOCR 코드 Apache-2.0, **가중치 조건 미확인**(LICENSES.md §4).
# 여기서는 **벤치마크로만** 쓴다. 앱 반입은 별도 확인이 필요하다.
import argparse
import json
import re
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
IN_H, IN_W, BLANK = 160, 320, 10
from build_cache_v2 import BOX_MARGIN  # noqa: E402


def load(p):
    d = {}
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            d[j["id"]] = j
    return d


def crop_of(g, quad):
    a = np.array(quad, np.float32)
    x0, y0, x1, y1 = a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()
    mw, mh = (x1 - x0) * BOX_MARGIN, (y1 - y0) * BOX_MARGIN
    x0, y0 = max(0, x0 - mw), max(0, y0 - mh)
    x1 = min(g.shape[1] - 1, x1 + mw); y1 = min(g.shape[0] - 1, y1 + mh)
    src = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32)
    dst = np.array([[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1], [0, IN_H - 1]],
                   np.float32)
    return cv2.warpPerspective(g, cv2.getPerspectiveTransform(src, dst), (IN_W, IN_H))


def pick_number(texts, gt_len):
    """읽힌 조각들에서 혈당값 후보를 고른다.

    범용 OCR 은 시간·단위·기종명까지 읽으므로 그대로 비교하면 부당하게 나쁘다.
    **가장 관대한 기준**으로 준다 — 숫자만 남긴 조각 중 GT 와 자릿수가 같은
    것이 있으면 그걸, 없으면 가장 긴 숫자열을 쓴다.
    """
    nums = []
    for t in texts:
        for m in re.findall(r"\d+", t.replace("O", "0").replace("o", "0")
                            .replace("I", "1").replace("l", "1")):
            nums.append(m)
    if not nums:
        return ""
    same = [x for x in nums if len(x) == gt_len]
    return same[0] if same else max(nums, key=len)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--mode", choices=("crop", "full", "both"), default="both")
    args = ap.parse_args()

    import easyocr
    reader = easyocr.Reader(["en"], gpu=True, verbose=False)

    gm = load(HERE / "gmscreen_quads.jsonl")
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    ids = [str(v) for v in cache["real_holdout_ids"]]
    y = cache["real_holdout_label_ids"]
    gts = {ids[i]: "".join(str(int(v)) for v in y[i] if int(v) != BLANK)
           for i in range(len(ids))}
    ours = load(HERE / "reader_preds.json") if False else json.loads(
        (HERE / "reader_preds.json").read_text(encoding="utf-8"))

    step = max(1, len(ids) // args.limit)     # 간격 표본 — 앞부분만 집지 않는다
    use = [c for c in ids[::step] if c in gm][:args.limit]
    print(f"표본 {len(use)}장 (holdout {len(ids)}장에서 간격 추출)\n")

    res = {m: {"ok": 0, "n": 0, "t": 0.0} for m in ("crop", "full")}
    ours_ok = 0
    misses = []
    for k, cid in enumerate(use):
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            continue
        with Image.open(p) as pil:
            pil.load(); pil = ImageOps.exif_transpose(pil)
            g = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        gt = gts[cid]
        if ours.get(cid, [""])[0] == gt:
            ours_ok += 1
        for mode in (("crop", "full") if args.mode == "both" else (args.mode,)):
            img = crop_of(g, gm[cid]["quad"]) if mode == "crop" else g
            t0 = time.time()
            try:
                out = reader.readtext(img, detail=0, allowlist="0123456789")
            except Exception:
                out = []
            res[mode]["t"] += time.time() - t0
            got = pick_number(out, len(gt))
            res[mode]["n"] += 1
            if got == gt:
                res[mode]["ok"] += 1
            elif mode == "crop" and len(misses) < 12:
                misses.append((cid, gt, got, out[:4]))
        if (k + 1) % 25 == 0:
            print(f"  ... {k+1}/{len(use)}", flush=True)

    print(f"\n{'엔진/조건':<28} | {'완전일치':>14} | {'장당 시간':>10}")
    print("-" * 60)
    n = res["crop"]["n"] or 1
    print(f"{'우리 파이프라인 (TTA)':<28} | {ours_ok:4d} ({100*ours_ok/n:5.1f}%) | "
          f"{'—':>10}")
    for mode, lab in (("crop", "EasyOCR · 우리 크롭"), ("full", "EasyOCR · 원본 전체")):
        r = res[mode]
        if r["n"]:
            print(f"{lab:<28} | {r['ok']:4d} ({100*r['ok']/r['n']:5.1f}%) | "
                  f"{r['t']/r['n']:9.2f}s")
    print("\nEasyOCR(크롭) 오답 예시 — GT / 고른 값 / 원시 출력:")
    for cid, gt, got, raw in misses:
        print(f"  {cid.split('/')[-1]:>6}  {gt:>4} / {got or '(없음)':>6} / {raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
