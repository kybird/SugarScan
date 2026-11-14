# 합성 독립 검증 — 단계별 채점(2026-11-15, 설계 §6.1).
#
# 음성: 상자 통과 -> 숫자 후보 -> 확인 시트 도달을 유형별(no_device/off_lcd
# ·계열)로 센다. 양성: 정답 확정·오답 확정·미확정·글자 잘림을 센다.
# 검증 split(SGD_VAL)에서만 쓴다 — 임계 스윕 금지(동결 후 테스트 원칙).
#
# 앱 확정 규칙 재현(2026-11-14 Case 1 분석 반영):
#   검출 게이트 score>=0.25 & 면적>=2%  ->  리더 greedy 비었으면 탈락
#   -> 값 파싱(mg/dL 10..600 정수) -> 프레임 확신도(최약 자리 softmax 최대)
#   >=0.85. 사진 가져오기는 같은 프레임을 3회 제출하므로 결정적 모델의
#   연속 3회 합의는 1회 판정과 같다 — 안정화기 연속성 단위가 '유효 값
#   관측'임도 그 분석대로다(무검출은 창을 초기화하지 않는다).
#
# 사용:
#   python eval_reject_stages.py --set synth_coco/SGD_VAL \
#       --detector bundle | band_out/sgd_base.pt ... --reader bundle | ckpt.pt \
#       --name "제품 기준선" --out docs/reports/reject-stage-*.md
import argparse
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import torch

from band_net import BandNet, decode
from train_band import letterbox

CONF_GATE = 0.25
MIN_FRAC = 0.02
READ_CONF = 0.85
VLO, VHI = 10, 600      # mg/dL 값 검증 범위(정수)


def load_detector(spec):
    """'bundle' 이면 배포 ONNX, 경로면 train_band 체크포인트."""
    if spec == "bundle":
        import onnxruntime as ort
        from export_deploy_onnx import decode_np, letterbox as lb640
        m = Path(__file__).resolve().parents[2] / "assets" / "models"
        s = ort.InferenceSession(str(m / "band_detector.onnx"),
                                 providers=["CPUExecutionProvider"])

        def run(img):
            lb, r, dx, dy = lb640(img, 640)
            obj, reg = s.run(None, {"image": lb[None, None].astype(np.float32) / 255})
            box, score = decode_np(obj[0, 0], reg[0], 16)
            return np.asarray(box, np.float32), float(score), (r, dx, dy)
        return run, 640
    ck = torch.load(spec, map_location="cpu")
    from band_net import BandNet as BN
    model = BN(width=ck.get("width", 1.0), stride=ck.get("stride", 16))
    model.load_state_dict(ck["model"])
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(dev).eval()
    size = ck.get("size", 416)

    def run(img):
        lb, r, dx, dy = letterbox(img, size)
        x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            o, g = model(x.to(dev))
        b, sc = decode(o.float(), g.float(), model.stride)
        return b[0].cpu().numpy(), float(sc[0].cpu()), (r, dx, dy)
    return run, size


def load_reader(spec):
    """'bundle' 이면 배포 ONNX(reader_crnn.onnx), 경로면 reader 체크포인트.
    반환: crop(144x96 uint8) -> (text, conf)."""
    if spec == "bundle":
        import onnxruntime as ort
        from export_deploy_onnx import greedy_np, run_reader_onnx
        m = Path(__file__).resolve().parents[2] / "assets" / "models"
        sess = ort.InferenceSession(str(m / "reader_crnn.onnx"),
                                    providers=["CPUExecutionProvider"])

        def read(crop):
            logits = run_reader_onnx(sess, cv2.resize(crop, (144, 96)))
            return greedy_np(logits), conf_of(logits)
        return read
    from reader_crnn import CRNN, decode_greedy
    ck = torch.load(spec, map_location="cpu")
    model = CRNN()
    sd = ck.get("model", ck)
    model.load_state_dict(sd)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(dev).eval()

    def read(crop):
        x = (torch.from_numpy(cv2.resize(crop, (144, 96)).astype(np.float32))
             / 255.0 - 0.5).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            out = model(x.to(dev)).cpu()          # (1,T,C) — decode_greedy 규약
        return decode_greedy(out)[0], conf_of(out[0].numpy())
    return read


def conf_of(logits):
    """앱 규약 확신도 — 글자가 나온(비blank·비반복) 스텝의 softmax 최대 확률
    중 최약값. 글자가 없으면 0(빈 출력은 어차피 탈락)."""
    ids = logits.argmax(axis=1)
    prev = np.r_[-1, ids[:-1]]
    peaks = logits[(ids != prev) & (ids != 10)]
    if not len(peaks):
        return 0.0
    e = np.exp(peaks - peaks.max(axis=1, keepdims=True))
    return float((e / e.sum(axis=1, keepdims=True)).max(axis=1).min())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--detector", required=True)
    ap.add_argument("--reader", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", default=None, help="md appendix 경로(선택)")
    args = ap.parse_args()
    det_run, size = load_detector(args.detector)
    read = load_reader(args.reader)
    root = Path(args.set)
    rows = [json.loads(l) for l in
            (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]

    neg = Counter()      # (reason, family) -> 각 단계
    neg_n = Counter()
    pos = Counter()
    pos_n = 0
    clips = 0
    for m in rows:
        img = cv2.imread(str(root / "train2017" / f"{m['id']}.png"),
                         cv2.IMREAD_GRAYSCALE)
        assert img is not None, m["id"]
        b, score, (r, dx, dy) = det_run(img)
        p = [(b[0] - dx) / r, (b[1] - dy) / r, (b[2] - dx) / r, (b[3] - dy) / r]
        frac = ((p[2] - p[0]) * (p[3] - p[1]) / (img.shape[0] * img.shape[1]))
        gate = score >= CONF_GATE and frac >= MIN_FRAC
        if m["has_band"]:
            pos_n += 1
            gt = str(m["label"])
            if not gate:
                pos["미확정(검출)"] += 1
                continue
            crop = img[max(0, int(p[1])):min(img.shape[0], int(p[3])),
                       max(0, int(p[0])):min(img.shape[1], int(p[2]))]
            text, conf = read(crop)
            val = int(text) if text.isdigit() and VLO <= int(text) <= VHI else None
            if val is None:
                pos["미확정(판독)"] += 1
            elif conf < READ_CONF:
                pos["미확정(확신도)"] += 1
            elif text == gt:
                pos["정답 확정"] += 1
            else:
                pos["오답 확정"] += 1
            db = m.get("digit_box")
            if db is not None and (p[0] > db[0] + 1 or p[1] > db[1] + 1
                                   or p[2] < db[2] - 1 or p[3] < db[3] - 1):
                clips += 1
        else:
            key = (m.get("neg_reason"), m.get("distractor_family") or "plain")
            neg_n[key] += 1
            if not gate:
                neg[(key, "상자단계 거절")] += 1
                continue
            crop = img[max(0, int(p[1])):min(img.shape[0], int(p[3])),
                       max(0, int(p[0])):min(img.shape[1], int(p[2]))]
            text, conf = read(crop)
            val = int(text) if text.isdigit() and VLO <= int(text) <= VHI else None
            if val is None:
                neg[(key, "판독단계 거절")] += 1
            elif conf < READ_CONF:
                neg[(key, "확신도단계 거절")] += 1
            else:
                neg[(key, "확인시트 도달")] += 1

    lines = [f"## {args.name} — SGD_VAL 단계별 채점",
             f"- 검출기 `{args.detector}` · 리더 `{args.reader}`",
             f"- 양성 n={pos_n}: " + ", ".join(f"{k} {v}" for k, v in pos.items())
             + f" / 글자 잘림 {clips}",
             "- 음성(장면 수 기준):"]
    fams = sorted({k for k in neg_n})
    for key in fams:
        n_ = neg_n[key]
        stages = {s: neg[(key, s)] for s in ("상자단계 거절", "판독단계 거절",
                                             "확신도단계 거절", "확인시트 도달")}
        reach = stages["확인시트 도달"]
        lines.append(f"  - {key[0]}/{key[1]}: n={n_} · 도달 {reach} "
                     f"({100*reach/max(1,n_):.1f}%) · " +
                     " · ".join(f"{s.replace('단계 거절','')} {v}" for s, v in stages.items()))
    txt = "\n".join(lines)
    print(txt)
    if args.out:
        with open(args.out, "a", encoding="utf-8") as f:
            f.write(txt + "\n\n")


if __name__ == "__main__":
    main()
