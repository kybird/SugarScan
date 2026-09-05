# GM 재학습의 효과를 **라벨 없이** 잰다 — 평가 holdout 49장의 판독 정확도로.
#
# 왜 라벨이 필요 없는가: 개선의 정의가 "박스가 정답 박스에 가까운가"(IoU)가
# 아니라 "그 박스로 잘라서 값을 제대로 읽는가"이기 때문이다. GT 판독값은
# 이미 있으므로 홀드아웃에 사람 박스를 그릴 필요가 없다. 그래서 이 49장은
# 라벨링 큐에서 빠져 있고, 학습 데이터에도 들어가지 않는다.
#
# 사용:
#   python eval_lcd_fix.py --quads <검출결과.jsonl> [--label <표시이름>]
# 여러 번 부르면 서로 다른 검출 결과를 같은 잣대로 비교할 수 있다.
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
IN_H, IN_W = 160, 320
BLANK = 10


def load_jsonl(p):
    d = {}
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            d[j["id"]] = j
    return d


def greedy(row):
    seq = np.argmax(row, -1)
    s, prev = [], -1
    for v in seq:
        v = int(v)
        if v != prev and v != BLANK:
            s.append(str(v))
        prev = v
    return "".join(s)


def warp(g, quad):
    a = np.array(quad, np.float32)
    xs, ys = a[:, 0], a[:, 1]
    src = np.array([[xs.min(), ys.min()], [xs.max(), ys.min()],
                    [xs.max(), ys.max()], [xs.min(), ys.max()]], np.float32)
    dst = np.array([[0, 0], [IN_W - 1, 0], [IN_W - 1, IN_H - 1], [0, IN_H - 1]],
                   np.float32)
    return cv2.warpPerspective(g, cv2.getPerspectiveTransform(src, dst),
                               (IN_W, IN_H))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quads", required=True, help="검출 결과 jsonl")
    ap.add_argument("--label", default=None)
    args = ap.parse_args()
    tag = args.label or Path(args.quads).stem

    hold = json.loads((HERE / "lcd_fix_holdout.json").read_text(encoding="utf-8"))
    quads = load_jsonl(args.quads)
    readings = load_jsonl(DATUMO / "labels.jsonl")
    corr = load_jsonl(HERE / "gt_corrections.jsonl") if (
        HERE / "gt_corrections.jsonl").exists() else {}
    model = tf.keras.models.load_model(str(HERE / "reader_model"))

    rows, missing = [], 0
    for r in hold:
        cid = r["id"]
        gt = str(corr.get(cid, {}).get("corrected") or
                 readings.get(cid, {}).get("reading") or "")
        if not gt.isdigit():
            continue
        if cid not in quads:
            missing += 1
            rows.append((cid, r["stratum"], gt, None, None))
            continue
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            continue
        with Image.open(p) as pil:
            pil.load()
            pil = ImageOps.exif_transpose(pil)
            g = cv2.cvtColor(np.asarray(pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        crop = warp(g, quads[cid]["quad"])
        a = np.array(quads[cid]["quad"], float)
        ar = a[:, 0].ptp() / max(a[:, 1].ptp(), 1e-6)
        rows.append((cid, r["stratum"], gt, crop, ar))

    imgs = [r[3] for r in rows if r[3] is not None]
    preds = {}
    if imgs:
        L = model.predict(np.asarray(imgs, np.float32)[..., None],
                          batch_size=32, verbose=0)
        k = 0
        for r in rows:
            if r[3] is not None:
                preds[r[0]] = greedy(L[k]); k += 1

    n = len(rows)
    exact = sum(1 for r in rows if preds.get(r[0]) == r[2])
    print(f"\n=== {tag} — 평가 holdout {n}장 (학습에 쓰이지 않은 장) ===")
    print(f"  검출 실패(박스 없음) : {missing}")
    print(f"  판독 완전일치        : {exact}/{n} = {100*exact/n:.1f}%")
    from collections import Counter
    tot, ok = Counter(), Counter()
    for r in rows:
        tot[r[1]] += 1
        if preds.get(r[0]) == r[2]:
            ok[r[1]] += 1
    for s in ("gm_miss", "wide", "lowconf"):
        if tot[s]:
            print(f"    {s:8s} {ok[s]:2d}/{tot[s]:2d} = {100*ok[s]/tot[s]:5.1f}%")
    print("\n  틀린 장:")
    for cid, s, gt, crop, ar in rows:
        p = preds.get(cid)
        if p != gt:
            arx = f"w/h {ar:.2f}" if ar else "박스없음"
            print(f"    {cid:26s} {s:8s} GT {gt:>4} → {str(p):>6}  {arx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
