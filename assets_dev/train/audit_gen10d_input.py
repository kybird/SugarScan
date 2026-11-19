# GEN10D 입력 감사 — 416/640 짝측정 (2026-11-19, G-GEN10D-INPUT-AUDIT-20261119)
#
# 질문: "896×516 합성이 640 레터박스에서 업스케일되어 밴드가 비정상적으로 크게
# 학습됐다"(dc238-judge GEN10D 절)는 설명이 실제 변환·데이터와 일치하는가.
#
# 측정만 한다. 학습·생성기·앱·ONNX·기존 결과 파일은 전혀 건드리지 않는다.
# 변환은 train_band.letterbox(학습·재판이 쓰는 그 함수)를 import 해서 잰다 —
# 재구현이 아니다. 검출기 추론은 eval_reject_stages.load_detector 를 쓴다.
#
# 사용:  python audit_gen10d_input.py            # A(기하) + B(crops) + C(검출기)
#        python audit_gen10d_input.py --skip-det # A + B 만 (GPU 없을 때)
#
# 출력: stdout(보고서 원시 수치) + audit_gen10d_input_out.json(전체 원시 결과)

import argparse
import json
import statistics as st
from pathlib import Path

import numpy as np

from train_band import letterbox  # 학습·재판 정본 변환

HERE = Path(__file__).resolve().parent
GEN10B = HERE / "synth_coco" / "GEN10B_TRAIN" / "annotations" / "instances_train2017.json"
LABELS = HERE / "dc238_labels.jsonl"
CKPT = {"ps10b(416)": HERE / "band_out" / "ps10b_det_neg25.pt",
        "ps10d(640)": HERE / "band_out" / "ps10d_det640.pt"}
CROPS = {"ps10b(416)": HERE / "band_out" / "ps10b_det_neg25_crops.jsonl",
         "ps10d(640)": HERE / "band_out" / "ps10d_det640_crops.jsonl"}
AUG_MIN, AUG_MAX = 0.55, 1.25   # 체크포인트 aug_scale_min / 상한(train_band 고정)


def q(v, ps=(10, 50, 90)):
    v = sorted(v)
    out = []
    for p in ps:
        i = min(len(v) - 1, max(0, int(round((len(v) - 1) * p / 100))))
        out.append(round(v[i], 1))
    return out  # (p10, med, p90)


def letterbox_r(w, h, size):
    """letterbox 의 배율 r 만 주석 수치로 계산(이미지 로드 없음)."""
    return min(size / h, size / w)


def part_a_synth():
    """A1 — GEN10B_TRAIN 양성 12,000장: 같은 주석을 416/640에 짝적용."""
    j = json.loads(GEN10B.read_text(encoding="utf-8"))
    by = {a["image_id"]: a["bbox"] for a in j["annotations"]}
    rows = []
    for im in j["images"]:
        b = by.get(im["id"])
        if b is None:
            continue
        # 같은 증강 배율 sc 를 두 크기에 공유(짝측정). sc 는 결정적 시드로 재현.
        rng = np.random.default_rng(im["id"])
        sc = rng.uniform(AUG_MIN, AUG_MAX)
        w, h = im["width"], im["height"]
        bw, bh = b[2] * sc, b[3] * sc          # 증강 후(원본 프레임 좌표)
        rows.append((w, h, bw, bh, sc))
    out = {"n": len(rows)}
    for size in (416, 640):
        r = [letterbox_r(w, h, size) for w, h, *_ in rows]
        bh = [bh_ * letterbox_r(w, h, size) for w, h, _, bh_, _ in rows]
        bw = [bw_ * letterbox_r(w, h, size) for w, h, bw_, _, _ in rows]
        tot = [sc * letterbox_r(w, h, size) for w, h, _, _, sc in rows]
        frac = [b / size for b in bh]
        out[f"size{size}"] = {
            "letterbox_r p10/med/p90": q(r),
            "band_h_px p10/med/p90": q(bh),
            "band_w_px p10/med/p90": q(bw),
            "band_h_fraction_of_canvas p10/med/p90": q(frac, (10, 50, 90)),
            "total_scale(sc*r) p10/med/p90": q(tot),
            "total_scale max": round(max(tot), 4),
            "n_upscale(total_scale>=1.0)": sum(1 for t in tot if t >= 1.0),
        }
    # 짝 비: 640/416 밴드 픽셀 비(전 행이 640/416=1.5385 여야 한다)
    ratio = [letterbox_r(w, h, 640) / letterbox_r(w, h, 416) for w, h, *_ in rows]
    out["band_px_ratio_640_over_416"] = {
        "p10/med/p90": q(ratio), "min": round(min(ratio), 5), "max": round(max(ratio), 5)}
    # 캔버스 점유 분수가 두 크기에서 같은가(대표값)
    f416 = [b[3] * b[4] * letterbox_r(b[0], b[1], 416) / 416 for b in rows]
    f640 = [b[3] * b[4] * letterbox_r(b[0], b[1], 640) / 640 for b in rows]
    out["fraction_identical_max_absdiff"] = round(max(abs(a - c) for a, c in zip(f416, f640)), 6)
    return out, rows


def part_a_real():
    """A2 — DC238 값 207장: 사람 밴드 쿼드를 416/640 레터박스에 짝적용.
    프레임 크기는 ow/oh 가 56행에만 있어 실제 파일에서 EXIF 지향으로 읽는다
    (eval_real_judge.load_oriented 와 같은 관례)."""
    from PIL import Image, ImageOps
    from eval_real_judge import IMG
    rows = []
    n_no_quad = 0
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        j = json.loads(l)
        if j.get("value") is None:
            continue
        if not j.get("quad"):
            n_no_quad += 1
            continue
        stem = j["id"].split("/", 1)[1]
        with Image.open(IMG / f"{stem}.jpg") as im:
            w, h = ImageOps.exif_transpose(im).size
        xs = [p[0] for p in j["quad"]]
        ys = [p[1] for p in j["quad"]]
        bw, bh = max(xs) - min(xs), max(ys) - min(ys)
        rows.append((w, h, bw, bh))
    out = {"n": len(rows), "n_value_without_quad": n_no_quad}
    for size in (416, 640):
        r = [letterbox_r(w, h, size) for w, h, *_ in rows]
        bh = [b * letterbox_r(w, h, size) for w, h, _, b in rows]
        bw = [b * letterbox_r(w, h, size) for w, h, b, _ in rows]
        out[f"size{size}"] = {
            "letterbox_r p10/med/p90": q(r),
            "band_h_px p10/med/p90": q(bh),
            "band_w_px p10/med/p90": q(bw),
            "band_h_fraction_of_canvas p10/med/p90": q([b / size for b in bh]),
        }
    return out, rows


def part_a_x(synth_rows, real_rows):
    """A3 — 합성:실촉 밴드 픽셀 비가 416↔640 에서 뒤집히는가(중앙값 기준)."""
    x = {}
    for size in (416, 640):
        s = st.median([b[3] * letterbox_r(b[0], b[1], size) for b in synth_rows])
        r_ = st.median([b[3] * letterbox_r(b[0], b[1], size) for b in real_rows])
        x[f"size{size}"] = {"synth_med_px": round(s, 1), "real_med_px": round(r_, 1),
                            "synth_over_real": round(s / r_, 3)}
    return x


def part_a_e2e(n=20):
    """A4 — 실 파일로 구현 검증: 주석 산수 == letterbox 실동작 (샘플)."""
    import cv2
    j = json.loads(GEN10B.read_text(encoding="utf-8"))
    by = {a["image_id"]: a["bbox"] for a in j["annotations"]}
    pos = [im for im in j["images"] if im["id"] in by][:n]
    root = HERE / "synth_coco" / "GEN10B_TRAIN" / "train2017"
    worst = {"bh": 0.0, "frac": 0.0}
    for im in pos:
        img = cv2.imread(str(root / im["file_name"]), cv2.IMREAD_GRAYSCALE)
        h, w = img.shape
        # 구현 크기가 주석과 같은지도 검증
        assert (w, h) == (im["width"], im["height"]), (im["file_name"], w, h, im["width"], im["height"])
        b = by[im["id"]]
        for size in (416, 640):
            lb, r, dx, dy = letterbox(img, size)
            bh_impl = b[3] * r
            bh_math = b[3] * letterbox_r(im["width"], im["height"], size)
            worst["bh"] = max(worst["bh"], abs(bh_impl - bh_math))
            worst["frac"] = max(worst["frac"], abs(lb.shape[0] - size))
    worst["canvas_shape_maxdiff"] = worst.pop("frac")
    return {"n": len(pos), "impl_vs_math_max_absdiff_band_h_px": round(worst["bh"], 6),
            "canvas_shape_maxdiff": worst["canvas_shape_maxdiff"]}


def part_b_crops():
    """B — ps10b vs ps10d 검출기가 뽑은 학습 크롭 분포(리더 입력 분포)."""
    out = {}
    for name, p in CROPS.items():
        pos_w, pos_h, scores, npos, nneg = [], [], [], 0, 0
        for l in p.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            j = json.loads(l)
            if j["kind"] == "pos" and j.get("pred"):
                pos_w.append(j["pred"][2] - j["pred"][0])
                pos_h.append(j["pred"][3] - j["pred"][1])
                npos += 1
            else:
                nneg += 1
            scores.append(j["score"])
        out[name] = {"n_pos": npos, "n_neg": nneg,
                     "pos_crop_w_px p10/med/p90": q(pos_w),
                     "pos_crop_h_px p10/med/p90": q(pos_h),
                     "neg_score p10/med/p90": q(scores)}
    return out


def part_d_cross():
    """D — 2×2 교차: 검출기{ps10b@640, ps10d@640(+ps10b@416 닻)} ×
    리더{ps10b, ps10d}. 체인·버킷은 eval_real_judge 본체와 동일 규칙
    (CONF_GATE→MIN_FRAC→판독→값검증→READ_CONF)로 잰다. 기존 재판 결과와
    같은 버킷명이라 직접 비교된다."""
    import torch
    from collections import Counter
    from eval_reject_stages import (CONF_GATE, MIN_FRAC, READ_CONF, VLO, VHI,
                                    load_detector, load_reader)
    from eval_real_judge import load_oriented

    rows = {}
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            rows[j["id"].split("/", 1)[1]] = j

    det_specs = [("ps10b@416", CKPT["ps10b(416)"], 416),
                 ("ps10b@640", CKPT["ps10b(416)"], 640),
                 ("ps10d@640", CKPT["ps10d(640)"], 640)]
    rdr_specs = [("rdr10b", "reader_out/ps10b_rdr/best.pt"),
                 ("rdr10d", "reader_out/ps10d_rdr/best.pt")]
    out = {}
    for dname, dpath, dsize in det_specs:
        ck = torch.load(dpath, map_location="cpu", weights_only=False)
        ck["size"] = dsize
        tmp = HERE / f"_audit_tmp_det_{dname}.pt"
        torch.save(ck, tmp)
        try:
            det_run, _ = load_detector(str(tmp))
            for rname, rpath in rdr_specs:
                read = load_reader(rpath)
                pos, pos_n = Counter(), 0
                for stem, gt in sorted(rows.items()):
                    if not (gt["source"] == "human" and gt["value"] is not None):
                        continue
                    pos_n += 1
                    img = load_oriented(stem)
                    b, score, (r, dx, dy) = det_run(img)
                    p = [(b[0] - dx) / r, (b[1] - dy) / r,
                         (b[2] - dx) / r, (b[3] - dy) / r]
                    frac = ((p[2] - p[0]) * (p[3] - p[1])
                            / (img.shape[0] * img.shape[1]))
                    stage, val, conf = "검출게이트", None, 0.0
                    if score >= CONF_GATE and frac >= MIN_FRAC:
                        stage = "판독"
                        crop = img[max(0, int(p[1])):min(img.shape[0], int(p[3])),
                                   max(0, int(p[0])):min(img.shape[1], int(p[2]))]
                        text, conf = read(crop)
                        if text:
                            stage = "값검증"
                            if text.isdigit() and VLO <= int(text) <= VHI:
                                val = int(text)
                                stage = "확신도"
                                if conf >= READ_CONF:
                                    stage = "확정"
                    if val is None:
                        pos[f"미확정({stage})"] += 1
                    elif stage != "확정":
                        pos[f"확신도차단(판독{'정답' if val == gt['value'] else '오답'})"] += 1
                    elif val == gt["value"]:
                        pos["정닥 확정"] += 1
                    else:
                        pos["오답 확정"] += 1
                out[f"{dname}+{rname}"] = {"n": pos_n, **dict(pos)}
        finally:
            tmp.unlink(missing_ok=True)
    return out


def part_c_detector():
    """C — 검출기 단독 짝비교: 같은 DC238 값 207장을 세 배치로 돌린다.
    ps10b@416(제품 재현), ps10b@640(승자 조건), ps10d@640(GEN10D 조건).
    리더 없이 게이트 통과율·점수·GT IoU 만 잰다 — 검출기 책임만 분리."""
    import torch
    from eval_reject_stages import CONF_GATE, load_detector
    from eval_real_judge import load_oriented

    rows = []
    for l in LABELS.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        j = json.loads(l)
        if j.get("value") is None or not j.get("quad"):
            continue
        xs = [p[0] for p in j["quad"]]
        ys = [p[1] for p in j["quad"]]
        rows.append((j["id"].split("/", 1)[1], min(xs), min(ys), max(xs), max(ys)))

    def iou(a, b):
        x1, y1 = max(a[0], b[0]), max(a[1], b[1])
        x2, y2 = min(a[2], b[2]), min(a[3], b[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
        return inter / ua if ua > 0 else 0.0

    out = {}
    for name, p in CKPT.items():
        if name.startswith("ps10b"):
            cfgs = [("ps10b@416", 416), ("ps10b@640", 640)]
        else:
            cfgs = [("ps10d@640", 640)]
        for cname, size in cfgs:
            ck = torch.load(p, map_location="cpu", weights_only=False)
            ck["size"] = size          # 배급 크기만 바꾼다 — 가중치 불변
            tmp = HERE / f"_audit_tmp_{cname}.pt"
            torch.save(ck, tmp)
            try:
                run, _ = load_detector(str(tmp))
                scores, ious, npass, nimg = [], [], 0, 0
                for stem, gx1, gy1, gx2, gy2 in rows:
                    img = load_oriented(stem)
                    box, score, (r, dx, dy) = run(img)
                    nimg += 1
                    if box is not None and len(box) and score >= CONF_GATE:
                        npass += 1
                        pb = [box[0] / r - dx / r, box[1] / r - dy / r,
                              box[2] / r - dx / r, box[3] / r - dy / r]
                        ious.append(iou(pb, [gx1, gy1, gx2, gy2]))
                    scores.append(score)
                out[cname] = {
                    "n": nimg, "gate_pass": npass,
                    "pass_rate": round(npass / max(1, nimg), 3),
                    "score p10/med/p90": q(scores),
                    "iou_of_pass p10/med/p90": q(ious) if ious else None,
                }
            finally:
                tmp.unlink(missing_ok=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-det", action="store_true")
    a = ap.parse_args()

    report = {}
    sa, srows = part_a_synth()
    ra, rrows = part_a_real()
    report["A1_synth"] = sa
    report["A2_real"] = ra
    report["A3_synth_vs_real"] = part_a_x(srows, rrows)
    report["A4_impl_check"] = part_a_e2e()
    report["B_crops"] = part_b_crops()
    if not a.skip_det:
        report["C_detector"] = part_c_detector()
        report["D_cross"] = part_d_cross()

    print(json.dumps(report, indent=2, ensure_ascii=False))
    (HERE / "audit_gen10d_input_out.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
