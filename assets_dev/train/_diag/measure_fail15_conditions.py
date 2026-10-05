# 검출 실패 15장(90도 회전 4장 제외)이 왜 실패하는지 이미지 조건으로 잰다
# (2026-10-04, 사람: "LCD 에 노이즈(그림자나 대비 얼룩) 때문인 것 같은데
# 인식 못하는 이유를 분석해볼 수 없냐").
#
# 비교 설계: 기종을 통제하고 조건만 비교한다 — 각 실패 장과 **같은 기종**의
# 검출 성공 사진(점수>=0.5)에서 밴드 크롭을 만들어 네 축을 재다:
#   대비(p95-p5, make_lowc_sheet.band_contrast 와 같은 자)
#   얼룩(8x3 블록 평균의 (max-min)/mean — 저주파 불균일 조명)
#   그림자(블록 평균의 x방향 선형 기울기 범위)
#   노이즈(비에지 화소의 라플라시안 MAD — 색 노이즈 근사)
#   휘도(크롭 평균)
#
# 실패 장의 밴드 상자는 gen1_v1 프로브(sc>=0.5)에서: 배포 모델 상자는 점이거나
# 점수 0 이라 신뢰할 수 없고, gen1 상자는 눈검·면적비(7~25%)로 숫자줄 위다.
# 성공 장의 상자는 배포 덤프(게이트 통과분). 규칙은 양쪽 다 "고신뢰 상자"로
# 같다.
#
# 사용: python _diag/measure_fail15_conditions.py
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

# make_lowc_sheet 을 import 하면 시트 생성 본문이 돌아버린다(스크립트다).
# band_contrast 는 p95-p5 다섯 줄 짜리라 _diag/measure_synth_contrast.py 와
# 같은 정의를 여기 둔다(자의 정의는 바꾸지 않는다).


def band_contrast(gray, box):
    x0, y0, x1, y1 = box
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(gray.shape[1], int(x1)), min(gray.shape[0], int(y1))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None, None
    band = gray[y0:y1, x0:x1].astype(np.float32)
    return abs(float(np.percentile(band, 95)) - float(np.percentile(band, 5))), \
        gray[y0:y1, x0:x1]


UP = HERE.parent / "upstream" / "datumo" / "extracted" / "TILDE"
FAILS = ["1705", "1706", "1710", "1762", "1781", "214", "2317", "2319",
         "2414", "498", "501", "525", "725", "728", "756"]
NSUC = 6           # 기종당 성공 대조 최대 수
SEED = 20261004


def pid(s):
    return "glucose_batch1/" + s


def photo(s):
    img = cv2.imread(str(UP / (pid(s) + ".jpg")), cv2.IMREAD_GRAYSCALE)
    if img is None:
        img = cv2.imread(str(UP / "glucose_batch1" / (s + ".jpg")),
                         cv2.IMREAD_GRAYSCALE)
    return img


def crop_metrics(img, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    crop = img[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    c, _ = band_contrast(img, box)
    # 얼룩·그림자: 8x3 블록 평균
    h, w = crop.shape
    bm = []
    for iy in range(3):
        for ix in range(8):
            b = crop[iy * h // 3:(iy + 1) * h // 3,
                     ix * w // 8:(ix + 1) * w // 8]
            bm.append(b.mean())
    bm = np.array(bm, dtype=np.float64)
    blotch = (bm.max() - bm.min()) / max(1.0, bm.mean())      # 얼룩 강도
    g = bm.reshape(3, 8).mean(axis=0)                          # 열 평균(세로 밴드)
    shadow = float(g.max() - g.min())                          # x방향 밝기 드리프트
    # 노이즈: 에지 제외 화소의 라플라시안 절대편차 중앙값
    lap = np.abs(cv2.Laplacian(crop, cv2.CV_32F))
    thr = np.percentile(lap, 70)
    noise = float(np.median(lap[lap <= thr]))
    return dict(contrast=c, blotch=round(float(blotch), 3),
                shadow=round(shadow, 1), noise=round(noise, 2),
                lum=round(float(crop.mean()), 1))


def whole_metrics(img):
    s = cv2.resize(img, (480, 480), interpolation=cv2.INTER_AREA)
    return dict(wmean=round(float(s.mean()), 1), wstd=round(float(s.std()), 1))


def main():
    gen1 = {r["id"]: r for r in json.loads(
        (HERE / "_diag" / "fail19_raw_probe_gen1.json").read_text(encoding="utf-8"))}
    tgdump = {}
    for ln in (HERE / "band_quads_pred_tg640w15_20261004.jsonl").read_text(
            encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            q = r["quad"]
            xs = [p[0] for p in q]
            ys = [p[1] for p in q]
            tgdump[r["id"]] = (min(xs), min(ys), max(xs), max(ys), r["score"])
    dev = {}
    for ln in (HERE / "device_labels.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            dev[r["id"]] = (r.get("brand") or "?") + (
                " " + r["model"] if r.get("model") else "")
    e2e = {json.loads(l)["id"]: json.loads(l)
           for l in (HERE / "_diag" / "e2e_bandnet" / "tg_v11e.jsonl").read_text(
               encoding="utf-8").splitlines() if l.strip()}
    failset = {pid(s) for s in FAILS}

    # 기종별 성공 풀(점수>=0.5)
    pool = {}
    for i, (bid, t) in enumerate(tgdump.items()):
        if t[4] < 0.5 or bid in failset:
            continue
        if e2e.get(bid, {}).get("verdict") == "det":
            continue
        pool.setdefault(dev.get(bid, "?"), []).append(bid)
    rng = random.Random(SEED)

    rows = []
    for s in FAILS:
        p = pid(s)
        img = photo(s)
        d = dev.get(p, "?")
        m = dict(id=s, device=d, **whole_metrics(img))
        g = gen1.get(p, {})
        if g.get("score", 0) >= 0.5 and g.get("frac", 0) >= 0.02:
            m["band"] = crop_metrics(img, g["box"])
        rows.append(m)
        # 같은 기종 성공 대조
        succ = rng.sample(pool.get(d, []), min(NSUC, len(pool.get(d, []))))
        for bid in succ:
            si = cv2.imread(str(UP / (bid.replace("/", "\\") + ".jpg")),
                            cv2.IMREAD_GRAYSCALE)
            if si is None:
                continue
            rows.append(dict(id=bid.split("/")[-1] + "(성공)", device=d,
                             **whole_metrics(si),
                             band=crop_metrics(si, tgdump[bid][:4])))

    # 출력: 기종 블록별로 실패 vs 성공 평균
    from collections import defaultdict
    bydev = defaultdict(lambda: {"fail": [], "suc": []})
    for r in rows:
        bydev[r["device"]]["fail" if "(성공)" not in r["id"] else "suc"].append(r)
    print(f"{'기종':<28} {'군':>4} {'n':>2} {'대비':>6} {'얼룩':>6} {'그림자':>6} "
          f"{'노이즈':>6} {'휘도':>6} {'전체평균':>7}")
    agg = defaultdict(lambda: defaultdict(list))
    for d in sorted(bydev):
        for grp in ("fail", "suc"):
            rs = bydev[d][grp]
            if not rs:
                continue
            bs = [r["band"] for r in rs if r.get("band")]
            n = len(bs)
            if n:
                agg["band"][grp].append(len(bs))
                print(f"{d:<28} {grp:>4} {n:>2} "
                      f"{np.mean([b['contrast'] for b in bs]):6.1f} "
                      f"{np.mean([b['blotch'] for b in bs]):6.3f} "
                      f"{np.mean([b['shadow'] for b in bs]):6.1f} "
                      f"{np.mean([b['noise'] for b in bs]):6.2f} "
                      f"{np.mean([b['lum'] for b in bs]):6.1f} "
                      f"{np.mean([r['wmean'] for r in rs]):7.1f}")
            else:
                print(f"{d:<28} {grp:>4}  0  (밴드 상자 없음 — 전체평균 "
                      f"{np.mean([r['wmean'] for r in rs]):.1f})")
    # 전체 집계
    print("\n== 전체 집계(밴드 지표가 있는 장만) ==")
    for grp in ("fail", "suc"):
        vals = defaultdict(list)
        for r in rows:
            if ("(성공)" in r["id"]) == (grp == "suc") and r.get("band"):
                for k, v in r["band"].items():
                    vals[k].append(v)
        print(grp, " ".join(f"{k}={np.mean(v):.2f}" for k, v in sorted(vals.items())))
    dst = HERE / "_diag" / "fail15_conditions.json"
    dst.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
