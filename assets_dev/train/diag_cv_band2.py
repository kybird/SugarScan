# 숫자줄을 고전 CV 로 찾는다 (2판). 밴드 라벨 86장으로 채점한다.
#
# 1판(diag_cv_band.py)과 다른 점 — 전부 실측에서 나왔다:
#  * 반사광을 먼저 누른다. CLAHE 는 국소 대비를 올려 하이라이트를 **키운다**.
#  * 채도를 쓴다. LCD 배경 채도(HSV S) 중앙 36, 60%의 장이 30 을 넘는다 —
#    회색~푸른 회색이다. 획은 중성이라 채도가 낮다. 그레이스케일로 먼저
#    바꾸면 이 정보가 버려진다.
#  * 양극성을 유지한다. 획이 어두운 장 72%, 밝은 장(백라이트) 28%.
#    가로형은 백라이트가 41% 라 한쪽만 보면 그 층이 통째로 날아간다.
#  * 개별 숫자를 묶지 않고 **부풀려 한 덩어리**로 만든 뒤 최대 덩이를 고른다.
#    1판은 숫자 하나를 놓치면 상자가 그만큼 줄어 68장 전부 "밴드를 다 담음"
#    이 0 이었다.
#  * 커널은 크롭 대비 비례. 작업 해상도를 고정해 작은 입력에서 커널이 1~2px
#    로 죽는 것을 막는다(비례가 틀린 게 아니라 1판은 계수가 컸다 — 65px).
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
WORK_H = 400


def load_rgb(p):
    with Image.open(p) as im:
        im.load()
        return np.asarray(ImageOps.exif_transpose(im).convert("RGB"))


def suppress_glare(g, pct=99.0):
    """반사광을 상한에서 눌러 붙인다. 하이라이트가 이진화를 지배하지 않게."""
    hi = float(np.percentile(g, pct))
    if hi <= 0:
        return g
    return np.clip(g.astype(np.float32) * (255.0 / hi), 0, 255).astype(np.uint8)


def find_band(rgb, use_sat=True, dilate=3, glare=99.0):
    H, W = rgb.shape[:2]
    sc = WORK_H / H
    img = cv2.resize(rgb, (max(1, int(W * sc)), WORK_H), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = suppress_glare(gray, glare)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

    # LCD 후보 — 채도가 있는 넓은 영역. 베젤·기기 몸체·배경을 줄인다.
    mask = None
    if use_sat:
        s = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)[..., 1]
        s = cv2.GaussianBlur(s, (0, 0), max(1.0, h * 0.02))
        _, m = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        k = max(3, int(h * 0.05)) | 1
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        if n > 1:
            i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            if st[i, cv2.CC_STAT_AREA] > h * w * 0.05:
                mask = (lab == i).astype(np.uint8) * 255

    small = max(3, int(h * 0.012)) | 1     # 이보다 얇은 획은 글자가 아니다
    grow = max(3, int(h * 0.010 * dilate)) | 1
    best = None
    for inv in (cv2.THRESH_BINARY_INV, cv2.THRESH_BINARY):
        bs = max(11, int(h * 0.08) | 1)
        bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   inv, bs, 8)
        if mask is not None:
            bw = cv2.bitwise_and(bw, mask)
        # 작은 획 제거 → 큰 획 살찌우기 → 한 덩어리
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (small, small)))
        bw = cv2.dilate(bw, cv2.getStructuringElement(cv2.MORPH_RECT, (grow, grow)))
        n, lab, st, _ = cv2.connectedComponentsWithStats(bw, 8)
        for i in range(1, n):
            x, y, cw, ch, area = st[i]
            if ch < h * 0.10 or ch > h * 0.92:
                continue
            if cw < w * 0.06 or cw > w * 0.98:
                continue
            if area < cw * ch * 0.25:
                continue
            score = area
            if best is None or score > best[0]:
                # 팽창분을 되돌린다.
                d = grow // 2
                best = (score, ((x + d) / sc, (y + d) / sc,
                                (x + cw - d) / sc, (y + ch - d) / sc))
    return None if best is None else best[1]


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / ua if ua > 0 else 0.0


def contains(pred, true, tol=0.02):
    wt = true[2]-true[0]; ht = true[3]-true[1]
    return (pred[0] <= true[0]+wt*tol and pred[1] <= true[1]+ht*tol and
            pred[2] >= true[2]-wt*tol and pred[3] >= true[3]-ht*tol)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pad", type=float, default=0.30)
    ap.add_argument("--no-sat", action="store_true")
    ap.add_argument("--dilate", type=float, default=3)
    ap.add_argument("--glare", type=float, default=99.0)
    ap.add_argument("--dump", default=None, help="오버레이 png 를 저장할 폴더")
    a = ap.parse_args()

    def rd(f):
        d = {}
        for l in (HERE / f).read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l); q = np.array(j["quad"], float)
                d[j["id"]] = (q[:,0].min(), q[:,1].min(), q[:,0].max(), q[:,1].max())
        return d
    band, gm = rd("band_boxes.jsonl"), rd("gmscreen_quads.jsonl")
    rot = {json.loads(l)["id"]
           for l in (HERE / "band_rotation.jsonl").read_text(encoding="utf-8").splitlines()
           if l.strip()}
    wide = set(json.loads((HERE/"_diag"/"wide_all"/"wide_ids.json").read_text(encoding="utf-8")))
    dump = Path(a.dump) if a.dump else None
    if dump:
        dump.mkdir(parents=True, exist_ok=True)

    res = {"세로형": [], "가로형": [], "회전": []}
    for cid, tb in sorted(band.items()):
        if cid not in gm:
            continue
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            continue
        rgb = load_rgb(p)
        g = gm[cid]; gw, gh = g[2]-g[0], g[3]-g[1]
        x0 = max(0, int(g[0]-gw*a.pad)); y0 = max(0, int(g[1]-gh*a.pad))
        x1 = min(rgb.shape[1], int(g[2]+gw*a.pad)); y1 = min(rgb.shape[0], int(g[3]+gh*a.pad))
        sub = rgb[y0:y1, x0:x1]
        if sub.size == 0:
            continue
        b = find_band(sub, use_sat=not a.no_sat, dilate=a.dilate, glare=a.glare)
        key = "회전" if cid in rot else ("가로형" if cid in wide else "세로형")
        if b is None:
            res[key].append((cid, 0.0, False)); continue
        pred = (b[0]+x0, b[1]+y0, b[2]+x0, b[3]+y0)
        res[key].append((cid, iou(pred, tb), contains(pred, tb)))
        if dump:
            v = cv2.cvtColor(sub, cv2.COLOR_RGB2BGR).copy()
            cv2.rectangle(v, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0,0,255), 6)
            cv2.rectangle(v, (int(tb[0]-x0), int(tb[1]-y0)),
                          (int(tb[2]-x0), int(tb[3]-y0)), (0,255,255), 6)
            s = 900 / max(v.shape[:2])
            cv2.imwrite(str(dump / f"{cid.replace('/','__')}.png"),
                        cv2.resize(v, None, fx=s, fy=s))

    print(f"pad={a.pad} sat={'off' if a.no_sat else 'on'} dilate={a.dilate} glare={a.glare}")
    tot_i, tot_c, tot_n = [], 0, 0
    for k, v in res.items():
        if not v:
            continue
        i = np.array([x[1] for x in v]); c = sum(1 for x in v if x[2])
        tot_i += list(i); tot_c += c; tot_n += len(v)
        print(f"  {k:<4} n={len(v):<3} IoU중앙 {np.median(i):.3f}  "
              f"IoU>0.5 {int((i>0.5).sum()):>2}/{len(v):<3} "
              f"다담음 {c:>2}/{len(v):<3} 완전실패 {int((i==0).sum())}")
    ti = np.array(tot_i)
    print(f"  {'전체':<4} n={tot_n:<3} IoU중앙 {np.median(ti):.3f}  "
          f"IoU>0.5 {int((ti>0.5).sum()):>2}/{tot_n:<3} 다담음 {tot_c:>2}/{tot_n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
