# 국소 대비 정규화(CLAHE)가 세그먼트와 배경을 더 잘 가르는가.
#
# 문제(2026-09-05, 사용자 관찰 488): 크롭 안에 **베젤이 숫자보다 더 어둡다**
# (베젤 최소 3 · LCD 배경 70 · 숫자는 그보다 조금 더 어두움). 그래서 전역
# 임계·극성 규칙이 성립하지 않고, 저대비 화면에서 희미한 반사선과 진짜
# 세그먼트의 농도 차가 사라진다.
#
# CLAHE 는 **타일 단위로** 히스토그램을 펴므로 베젤이 지배하지 못하고 패널
# 내부의 옅은 대비가 살아난다. 참고: SegoDec(Apache-2.0)이 같은 접근을 쓴다 —
# 코드는 안 봤고 아이디어만(LICENSES.md §참고만 하고 코드를 쓰지 않은 것).
#
# **주의**: 현재 모델은 CLAHE 없이 학습됐다. 추론에만 걸면 분포 밖이라
# 나빠지는 것이 정상이다. 이 스크립트는 '분리가 좋아지는가'를 보는 것이고,
# 채택 여부는 재학습해서 판단한다.
import json
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

HERE = Path(__file__).resolve().parent
OUT = HERE / "_diag" / "clahe"
BLANK = 10


def clahe(img, clip=2.5, tile=8):
    return cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile)).apply(img)


def dec(row):
    seq = np.argmax(row, -1)
    s, prev = [], -1
    for v in seq:
        v = int(v)
        if v != prev and v != BLANK:
            s.append(str(v))
        prev = v
    return "".join(s)


def separability(img):
    """숫자 영역에서 전경/배경이 얼마나 갈리는가 — 오츠 임계의 클래스간 분산."""
    h, w = img.shape
    c = img[int(h * 0.15):int(h * 0.75), int(w * 0.15):int(w * 0.9)]
    t, _ = cv2.threshold(c, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    a, b = c[c <= t].astype(np.float32), c[c > t].astype(np.float32)
    if len(a) < 10 or len(b) < 10:
        return 0.0
    wa, wb = len(a) / c.size, len(b) / c.size
    return float(wa * wb * (a.mean() - b.mean()) ** 2 / (c.astype(np.float32).var() + 1e-6))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cache = np.load(str(HERE / "data_cache_v2.npz"))
    X = cache["real_holdout_images"]
    ids = [str(v) for v in cache["real_holdout_ids"]]
    y = cache["real_holdout_label_ids"]
    gts = ["".join(str(int(v)) for v in r if int(v) != BLANK) for r in y]
    n = len(gts)

    s0 = np.array([separability(X[i]) for i in range(n)])
    Xc = np.stack([clahe(X[i]) for i in range(n)])
    s1 = np.array([separability(Xc[i]) for i in range(n)])
    print("전경/배경 분리도(오츠 클래스간 분산, 1에 가까울수록 잘 갈림)")
    print(f"  원본  중앙 {np.median(s0):.3f}  하위10% {np.percentile(s0,10):.3f}")
    print(f"  CLAHE 중앙 {np.median(s1):.3f}  하위10% {np.percentile(s1,10):.3f}")
    print(f"  개선된 장 {int((s1>s0).sum())}/{n} ({100*(s1>s0).mean():.0f}%)")

    m = tf.keras.models.load_model(str(HERE / "reader_model"))
    for tag, XX in (("원본(학습 규약)", X), ("CLAHE(추론만 — 분포 밖)", Xc)):
        L = m.predict(XX[..., None].astype(np.float32), batch_size=128, verbose=0)
        P = [dec(L[i]) for i in range(n)]
        ok = sum(P[i] == gts[i] for i in range(n))
        print(f"  {tag:26s} 완전일치 {ok}/{n} = {100*ok/n:.2f}%")

    for cid in ("glucose_batch1/488", "glucose_batch1/1717", "glucose_batch1/694"):
        if cid not in ids:
            continue
        i = ids.index(cid)
        pair = np.hstack([X[i], np.full((160, 6), 255, np.uint8), Xc[i]])
        cv2.imwrite(str(OUT / f"{cid.split('/')[-1]}.png"),
                    cv2.resize(pair, (pair.shape[1] * 3, 480),
                               interpolation=cv2.INTER_NEAREST))
        print(f"  saved {cid.split('/')[-1]}.png  분리도 {s0[i]:.3f} → {s1[i]:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
