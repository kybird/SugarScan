# 사용자가 라벨한 밴드 쿼드 304장 → CNN 학습 데이터 자동 생성.
# GT 값에서 셀 라벨이 공짜로 나온다: '121'→[1,2,1], '53'→[11,5,3](빈칸=11).
# 산출: assets_dev/train/cell_data/*.png (384×128 밴드 캔버스) + labels.csv
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "cell_data"
W, H = 384, 128


def solve_homography(src_pts, dst_pts):
    A = []
    b = []
    for (x, y), (u, v) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b.append(v)
    h = np.linalg.solve(np.array(A, dtype=np.float64), np.array(b, dtype=np.float64))
    return h


def warp_band(img, quad):
    src = np.array(quad, dtype=np.float32)
    xs, ys = src[:, 0], src[:, 1]
    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()
    # 쿼드 순서 무관: 원본 좌표계의 축정렬 bbox 모서리를 목표 캔버스 모서리로
    src_ax = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float32)
    dst_ax = np.array([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src_ax, dst_ax)
    return cv2.warpPerspective(img, M, (W, H))


def main() -> int:
    labeled = [
        json.loads(l)
        for l in (HERE / "labeled.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    OUT.mkdir(exist_ok=True)
    rows = []
    n = 0
    for row in labeled:
        if row.get("source") != "human" or row.get("quad") is None:
            continue
        cid = row["id"]
        val = None
        # GT 교정 반영
        gt = None
        for l in (HERE / "gt_corrections.jsonl").read_text(encoding="utf-8").splitlines() if (HERE / "gt_corrections.jsonl").exists() else []:
            j = json.loads(l)
            if j["id"] == cid:
                gt = j["corrected"]
        if gt is None:
            for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
                j = json.loads(l)
                if j["id"] == cid:
                    val = j["reading"]
                    break
        else:
            val = gt
        if val is None:
            continue
        p = DATUMO / "extracted" / "TILDE" / f"{cid}.jpg"
        img = cv2.imread(str(p))
        if img is None:
            try:
                from PIL import Image
                img = cv2.cvtColor(
                    np.asarray(Image.open(p).convert("RGB")), cv2.COLOR_RGB2BGR)
            except Exception:
                continue
        band = warp_band(img, row["quad"])
        fn = f"band_{cid.replace('/', '__')}.png"
        cv2.imwrite(str(OUT / fn), band)
        s = str(val)
        cells = [11] * (3 - len(s)) + [int(ch) for ch in s]
        rows.append(f"{fn},{','.join(map(str, cells))}")
        n += 1
    (OUT / "labels.csv").write_text(
        "file,c1,c2,c3\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"bands: {n} → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
