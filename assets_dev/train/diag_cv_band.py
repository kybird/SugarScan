# 고전 CV 로 숫자줄을 찾을 수 있는가 — 학습 없이. 밴드 라벨 86장으로 채점한다.
#
# 왜: 검출을 모델로만 생각하고 있었는데, 7세그 숫자는 대비가 크고 획 굵기가
# 일정하며 같은 베이스라인에 정렬돼 있다. 고전적인 이진화+연결요소 파이프라인이
# 잘 듣는 조건이다. 되면 라벨도 학습도 모델 크기도 필요 없고, minAreaRect 로
# 회전각까지 공짜로 나온다.
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np

from eval_reader import load_gray  # EXIF 규약 한 곳에서만

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"


WORK_H = 400   # 작업 해상도. 원본 해상도에서 크기 비례 커널을 쓰면 65px 짜리
               # 커널이 나와 화면 전체를 한 덩어리로 뭉갠다(실측).


def find_band(gray, grow=0.0, thresh='otsu'):
    """숫자줄 후보 상자를 원본 crop 좌표로 돌려준다. 못 찾으면 None."""
    H, W = gray.shape
    sc = WORK_H / H
    g = cv2.resize(gray, (max(1, int(W * sc)), WORK_H), interpolation=cv2.INTER_AREA)
    g = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
    h, w = g.shape
    best = None
    # 밝은 획/어두운 획 둘 다 본다 — 백라이트 화면은 극성이 뒤집힌다.
    for inv in (cv2.THRESH_BINARY_INV, cv2.THRESH_BINARY):
        if thresh == 'otsu':
            # 전역 Otsu. 적응형은 창이 획 두께보다 작으면 굵은 획을 **속 빈
            # 테두리**로 만들어 채움률 필터에 탈락시킨다(1046 에서 확인:
            # 숫자가 통째로 빠지고 사과 아이콘이 최대 덩이가 됐다).
            # LCD 는 배경이 균일해 전역 임계가 잘 듣는다.
            _, bw = cv2.threshold(g, 0, 255, inv + cv2.THRESH_OTSU)
        else:
            bw = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       inv, 31, 8)
        # 세그먼트 사이 틈만 메운다. 숫자끼리 붙을 만큼 크면 안 된다.
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
        comps = []
        for i in range(1, n):
            x, y, cw, ch, area = stats[i]
            if ch < h * 0.08 or ch > h * 0.70:   # 작으면 날짜·아이콘, 크면 배경·베젤
                continue
            if cw < 3 or cw > w * 0.35:
                continue
            if not (0.15 < cw / ch < 1.6):       # 7세그 숫자의 가로세로 비
                continue
            if area < cw * ch * 0.15:
                continue
            comps.append((x, y, cw, ch, area))
        if not comps:
            continue
        # 가장 큰 글자를 기준으로 높이가 비슷하고 같은 줄에 있는 것만 모은다.
        comps.sort(key=lambda c: -c[3])
        ref = comps[0]
        cy = ref[1] + ref[3] / 2
        grp = [c for c in comps
               if abs(c[3] - ref[3]) < ref[3] * 0.45
               and abs((c[1] + c[3] / 2) - cy) < ref[3] * 0.45]
        x0 = min(c[0] for c in grp); y0 = min(c[1] for c in grp)
        x1 = max(c[0] + c[2] for c in grp); y1 = max(c[1] + c[3] for c in grp)
        score = sum(c[4] for c in grp) * len(grp)
        if best is None or score > best[0]:
            # 상자가 계통적으로 작다(실측: 68장 전부 밴드를 다 못 담았다).
            # 획 바깥 여백과 놓친 한 자리를 여백으로 메운다.
            gx = (x1 - x0) * grow
            gy = (y1 - y0) * grow
            best = (score, ((x0 - gx) / sc, (y0 - gy) / sc,
                            (x1 + gx) / sc, (y1 + gy) / sc))
    return None if best is None else best[1]


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / ua if ua > 0 else 0.0


def contains(pred, true, tol=0.02):
    """예측 상자가 정답 밴드를 (여유 tol 안에서) 다 담았는가."""
    wt = true[2] - true[0]; ht = true[3] - true[1]
    return (pred[0] <= true[0] + wt*tol and pred[1] <= true[1] + ht*tol and
            pred[2] >= true[2] - wt*tol and pred[3] >= true[3] - ht*tol)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thresh", default="otsu", choices=["otsu", "adaptive"])
    ap.add_argument("--grow", type=float, default=0.0,
                    help="찾은 상자를 사방으로 넓히는 비율")
    ap.add_argument("--pad", type=float, default=0.30,
                    help="GM 박스를 사방으로 넓혀 탐색한다(가로형은 박스가 밴드를 안 담는다)")
    a = ap.parse_args()

    band = {}
    for l in (HERE / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l); q = np.array(j["quad"], float)
            band[j["id"]] = (q[:,0].min(), q[:,1].min(), q[:,0].max(), q[:,1].max())
    gm = {}
    for l in (HERE / "gmscreen_quads.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l); q = np.array(j["quad"], float)
            gm[j["id"]] = (q[:,0].min(), q[:,1].min(), q[:,0].max(), q[:,1].max())
    rot = {json.loads(l)["id"]
           for l in (HERE / "band_rotation.jsonl").read_text(encoding="utf-8").splitlines()
           if l.strip()}
    wide = set(json.loads((HERE / "_diag" / "wide_all" / "wide_ids.json")
                          .read_text(encoding="utf-8")))

    res = {"세로형": [], "가로형": [], "회전": []}
    for cid, tb in sorted(band.items()):
        if cid not in gm:
            continue
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        if not p.exists():
            continue
        gray = load_gray(p)
        g = gm[cid]
        gw, gh = g[2]-g[0], g[3]-g[1]
        x0 = max(0, int(g[0] - gw*a.pad)); y0 = max(0, int(g[1] - gh*a.pad))
        x1 = min(gray.shape[1], int(g[2] + gw*a.pad))
        y1 = min(gray.shape[0], int(g[3] + gh*a.pad))
        sub = gray[y0:y1, x0:x1]
        if sub.size == 0:
            continue
        b = find_band(sub, grow=a.grow, thresh=a.thresh)
        key = "회전" if cid in rot else ("가로형" if cid in wide else "세로형")
        if b is None:
            res[key].append((cid, 0.0, False)); continue
        pred = (b[0]+x0, b[1]+y0, b[2]+x0, b[3]+y0)
        res[key].append((cid, iou(pred, tb), contains(pred, tb)))

    print(f"pad={a.pad} grow={a.grow} thresh={a.thresh}")
    for k, v in res.items():
        if not v:
            continue
        ious = np.array([x[1] for x in v]); cont = sum(1 for x in v if x[2])
        print(f"\n{k}  n={len(v)}")
        print(f"  IoU  중앙 {np.median(ious):.3f}  p25 {np.percentile(ious,25):.3f}"
              f"  p75 {np.percentile(ious,75):.3f}")
        print(f"  IoU>0.5 {int((ious>0.5).sum())}/{len(v)}"
              f"   밴드를 다 담음 {cont}/{len(v)}"
              f"   완전 실패(못 찾음) {int((ious==0).sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
