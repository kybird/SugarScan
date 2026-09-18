# 합성으로만 학습한 밴드 검출기를 **실촬**에서 잰다 — 도메인 격차의 크기.
#
# 왜 필요한가: 합성 세트 B·C 성적(1300/1300, IoU 중앙 0.956)은 **같은 생성기의
# 다른 시드**일 뿐이다. 마일스톤 문구가 이미 못박았다 — "검증도 같은 생성기라
# 일반화는 증명하지 못한다". 실촬 숫자가 없으면 아키텍처 결정을 할 수 없다.
#
# **프레이밍을 맞추는 것이 이 자의 핵심이다.** 합성 패널은 실촬 "전체 사진"이
# 아니라 기기 크롭에 가깝다(2026-09-17 실측: 밴드/프레임 넓이비가 합성 0.315 대
# 실촬 전체사진 0.108 로 2.9배 차이, 실촬 LCD 박스 기준으로는 0.391 로 근접).
# 전체 사진을 그냥 먹이면 분포 밖에서 재는 것이라 격차가 부풀려진다.
# 그래서 GM 쿼드에 **학습 캐시와 같은 여백**을 붙여 자른다 —
# build_cache_v2.framed_src_rect 를 그대로 부른다(BOX_MARGIN 이 정본).
#
# 정답은 사람 밴드 라벨(band_boxes.jsonl, 읽기 전용)이다.
# 기본 모집단은 기기 단절 분할의 **홀드아웃**이다 — train 쪽은 다른 작업이
# 학습에 쓸 수 있으므로 평가에 섞지 않는다.
#
# 한계(출력에 함께 찍는다): 이 홀드아웃에 가로형이 0장이다. 구조적이라
# 시드로 안 풀린다 — 가로형 밴드 라벨이 기기 두 종뿐이고 둘 다 train 으로 갔다.
#
# 사용:
#   python eval_synthband_real.py --ckpt yolox_out/synthband_v2_a2/best_ckpt.pth
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

sys.path.insert(0, "D:/tmp/YOLOX")
from yolox.data.data_augment import ValTransform  # noqa: E402
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402

from build_cache_v2 import framed_src_rect  # 프레이밍 정본  # noqa: E402
from gm_quads import quad_rows  # GM 쿼드 단일 출처  # noqa: E402

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
BANDS = HERE / "band_boxes.jsonl"
SPLIT = HERE / "_diag" / "band_device_split" / "band_device_split.json"
EXP = str(HERE / "yolox_synthband_exp.py")
WIDE = HERE / "_diag" / "wide_all" / "wide_ids.json"


def rect(quad):
    q = np.asarray(quad, float)
    return [q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()]


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / u if u > 0 else 0.0


def compare(specs):
    """같은 모집단·같은 정답이어야 부른다. 층 중앙값만 보면 이상치 한 장이
    평균을 끌고 가는 것을 축의 효과로 읽는다([[same-seed-is-not-paired]] 의
    짝비교 절)."""
    data = {}
    for spec in specs:
        name, _, path = spec.partition("=")
        data[name] = {r["id"]: r for r in
                      (json.loads(l) for l in
                       Path(path).read_text(encoding="utf-8").splitlines()
                       if l.strip())}
    names = list(data)
    common = set.intersection(*(set(d) for d in data.values()))
    print(f"짝지은 장 {len(common)} (각 팔 " +
          " · ".join(f"{n} {len(data[n])}" for n in names) + ")")
    base = names[0]
    for n in names[1:]:
        d = np.array([data[n][i]["iou"] - data[base][i]["iou"]
                      for i in sorted(common)])
        win = int((d > 0.01).sum())
        lose = int((d < -0.01).sum())
        print(f"  {n} vs {base}: 승 {win} · 패 {lose} · 무 {len(d)-win-lose}"
              f"  | 짝차이 중앙 {np.median(d):+.4f} 평균 {d.mean():+.4f}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--exp", default=EXP)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--side", default="holdout",
                    choices=("holdout", "train", "all"))
    ap.add_argument("--out", default=str(HERE / "_diag" / "synthband_real"))
    ap.add_argument("--compare", nargs="+", metavar="이름=jsonl",
                    help="같은 모집단의 결과들을 짝지어 승·패·무로 센다")
    args = ap.parse_args()

    if args.compare:
        return compare(args.compare)

    bands = {}
    for l in BANDS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if j.get("quad"):
                bands[j["id"]] = rect(j["quad"])
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    ids = (split["holdout_ids"] if args.side == "holdout"
           else split["train_ids"] if args.side == "train"
           else split["train_ids"] + split["holdout_ids"])
    gm = {r["id"]: r for r in quad_rows()}
    labels = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labels[j["id"]] = j["image"]

    exp = get_exp(args.exp, None)
    model = exp.get_model().cuda().eval()
    model.load_state_dict(torch.load(args.ckpt, map_location="cpu")["model"])
    pre = ValTransform(legacy=False)

    rows, skipped = [], []
    for cid in ids:
        if cid not in bands or cid not in gm or cid not in labels:
            skipped.append(cid)
            continue
        img = cv2.imread(str(DATUMO / labels[cid]))
        if img is None:
            skipped.append(cid)
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fr = framed_src_rect(gray, gm[cid]["quad"])     # 학습 캐시와 같은 여백
        x0, y0 = int(fr[0][0]), int(fr[0][1])
        x1, y1 = int(fr[2][0]), int(fr[2][1])
        crop = img[y0:y1, x0:x1]
        if crop.size == 0 or min(crop.shape[:2]) < 16:
            skipped.append(cid)
            continue
        r = min(exp.test_size[0] / crop.shape[0], exp.test_size[1] / crop.shape[1])
        t, _ = pre(crop, None, exp.test_size)
        with torch.no_grad():
            det = postprocess(model(torch.from_numpy(t).unsqueeze(0).float().cuda()),
                              exp.num_classes, args.conf, 0.45, class_agnostic=True)[0]
        rec = {"id": cid, "gt": bands[cid], "crop": [x0, y0, x1, y1]}
        if det is None or len(det) == 0:
            rec.update(pred=None, score=None, iou=0.0)
        else:
            o = det.cpu().numpy()
            k = int(np.argmax(o[:, 4] * o[:, 5]))
            # 크롭 좌표 -> 원본 사진 좌표
            b = [float(o[k][0]) / r + x0, float(o[k][1]) / r + y0,
                 float(o[k][2]) / r + x0, float(o[k][3]) / r + y0]
            rec.update(pred=[round(v, 1) for v in b],
                       score=round(float(o[k][4] * o[k][5]), 4),
                       iou=round(iou(b, bands[cid]), 4))
        rows.append(rec)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{args.side}.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    v = np.array([r["iou"] for r in rows])
    miss = sum(1 for r in rows if r["pred"] is None)
    wide = set(json.loads(WIDE.read_text(encoding="utf-8")))
    n_wide = sum(1 for r in rows if r["id"] in wide)
    print(f"체크포인트 {Path(args.ckpt).parent.name} · 모집단 {args.side} "
          f"n={len(rows)} (건너뜀 {len(skipped)})")
    print(f"  프레이밍: GM 쿼드 + build_cache_v2.BOX_MARGIN (합성과 같은 규약)")
    print(f"  검출 실패 {miss}장")
    print(f"  IoU 중앙 {np.median(v):.4f} · 평균 {v.mean():.4f} · "
          f"p10 {np.percentile(v, 10):.4f} · 최소 {v.min():.4f}")
    print(f"  >=0.5 {int((v >= .5).sum())}장 · >=0.75 {int((v >= .75).sum())}장")
    print(f"  가로형 {n_wide}장 — 0이면 이 수치는 **세로형 성적일 뿐이다**")
    print(f"-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
