# 배포 스택 ONNX 변환 + 파리티 — BandNet 검출기(ftk5_g0.06) × CRNN 리더(rftk5_foldall).
#
# 온디바이스 경로는 ONNX 로 확정됐다(docs/DONE.md G28 — tflite 는 BiLSTM 의
# TensorListReserve 로 불가). 이 스크립트가 배포 자산의 정본을 만든다:
#
#   1. torch → ONNX (opset 17, 고정 shape, 입출력 이름 명시)
#        검출기  image[1,1,640,640] → obj[1,1,40,40](logit) + reg[1,4,40,40](softplus)
#        리더    crop[1,1,96,144]  → logits[1,36,11]
#      디코드(argmax·sigmoid·ltrb·CTC greedy)는 앱(Dart)에서 한다 —
#      eval_e2e_bandnet.py 의 decode/decode_greedy 와 같은 수식을 Dart 로 옮기고
#      유닛테스트로 고정한다. 그래야 모델 파일과 앱 로직이 서로 소통 없이
#      일치하는지 시험할 수 있다.
#   2. 파리티 — 실촉 전량(--full) 또는 표본(기본)에 대해 PyTorch e2e 와
#      ONNX Runtime e2e 의 판정(verdict·pred)·검출 점수·상자 IoU 를 비교.
#   3. 골든 벡터 — Dart 전처리(letterbox·bilinear resize)의 cv2 규약을 고정하는
#      작은 합성 케이스. test/ocr/deploy_preprocess_golden_test.dart 이 소비한다.
#
# 사용:
#   python export_deploy_onnx.py                  # 변환+스모크(12장)+리더단위+골든
#   python export_deploy_onnx.py --full           # + 실촉 2,504장 전량 e2e 파리티
#   python export_deploy_onnx.py --skip-export    # 이미 변환된 onnx 로 파리티만
import argparse
import base64
import json
import time
from pathlib import Path

import cv2
import numpy as np
import torch

from band_net import BandNet
from reader_crnn import CRNN, IN_H, IN_W, NUM_CLASSES, decode_greedy
from train_band import letterbox

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "deploy_onnx"

DET_CKPT = HERE / "band_out" / "tone" / "ftk5_g0.06"
READER_CKPT = HERE / "reader_out" / "rftk5_foldall" / "best.pt"

CONF_GATE = 0.25
MIN_FRAC = 0.02

# eval_e2e_bandnet.py ROTATED_90 와 동일 — 사람 선언 제외(2026-10-04/05).
ROTATED_90 = {"1213", "1226", "1564", "1565", "940", "283", "2411"}


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def decode_np(obj, reg, stride):
    """Dart BandDetector.decode 가 따라야 할 numpy 판 — band_net.decode 와 같은 수식.

    obj (40,40) logit, reg (4,40,40). (box, score) 반환."""
    h, w = obj.shape
    idx = int(obj.argmax())
    gy, gx = divmod(idx, w)
    score = float(sigmoid(obj[gy, gx]))
    cx, cy = (gx + 0.5) * stride, (gy + 0.5) * stride
    r = reg.reshape(4, -1)[:, idx]
    return [cx - r[0], cy - r[1], cx + r[2], cy + r[3]], score


def greedy_np(logits):
    """reader_crnn.decode_greedy 의 numpy 판(단일 배치)."""
    ids = logits.argmax(-1)
    out, prev = [], -1
    for k in ids.tolist():
        if k != prev and k != NUM_CLASSES - 1:
            out.append(str(k))
        prev = k
    return "".join(out)


def load_corpus():
    gts, imgs = {}, {}
    for line in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            gts[j["id"]] = j["reading"]
            imgs[j["id"]] = j["image"]
    return gts, imgs


def load_torch_models(dev):
    cd = torch.load(DET_CKPT, map_location="cpu", weights_only=False)
    det = BandNet(width=cd["width"], stride=cd.get("stride", 16)).to(dev).eval()
    det.load_state_dict(cd["model"])
    cr = torch.load(READER_CKPT, map_location="cpu", weights_only=False)
    reader = CRNN(NUM_CLASSES).to(dev).eval()
    reader.load_state_dict(cr["model"])
    return det, reader, cd["size"]


def run_reader_onnx(sess, crop):
    t = crop.astype(np.float32) / 255.0 - 0.5
    logits = sess.run(None, {"crop": t[None, None]})[0][0]
    return logits


def e2e_one(img, det_torch, reader_torch, size, det_ort, reader_ort, stride):
    """한 장을 torch 경로와 ORT 경로 각각으로 읽는다. (torch행, ort행, 비교값)"""
    lb, r, dx, dy = letterbox(img, size)
    x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
    dev = next(det_torch.parameters()).device
    with torch.no_grad():
        obj, reg = det_torch(x.to(dev))
        from band_net import decode as det_decode
        b, s = det_decode(obj.float(), reg.float(), stride)
    b = b[0].cpu().numpy()
    sc = float(s[0].cpu())
    p_t = [(b[0] - dx) / r, (b[1] - dy) / r, (b[2] - dx) / r, (b[3] - dy) / r]

    o_obj, o_reg = det_ort.run(None, {"image": x.numpy().astype(np.float32)})
    box_lb, sc_o = decode_np(o_obj[0, 0], o_reg[0], stride)
    # decode_np 는 레터박스 좌표를 내므로 torch 경로와 같이 원본으로 되돌린다.
    p_o = [(box_lb[0] - dx) / r, (box_lb[1] - dy) / r,
           (box_lb[2] - dx) / r, (box_lb[3] - dy) / r]

    def gate(p, sc):
        frac = ((p[2] - p[0]) * (p[3] - p[1])) / max(1.0, img.shape[1] * img.shape[0])
        return sc < CONF_GATE or frac < MIN_FRAC, frac

    g_t, _ = gate(p_t, sc)
    g_o, _ = gate(p_o, sc_o)
    iou = box_iou(p_t, p_o)

    def crop_pred(p, reader_fn):
        x0, y0 = max(0, int(p[0])), max(0, int(p[1]))
        x1 = min(img.shape[1], int(round(p[2])))
        y1 = min(img.shape[0], int(round(p[3])))
        if x1 - x0 < 4 or y1 - y0 < 4:
            return None, "tiny"
        crop = cv2.resize(img[y0:y1, x0:x1], (IN_W, IN_H))
        return reader_fn(crop), None

    if g_t or g_o:
        v_t = v_o = "det"
        pred_t = pred_o = ""
    else:
        rdev = next(reader_torch.parameters()).device
        pred_t, why_t = crop_pred(p_t, lambda c: decode_greedy(
            reader_torch(_reader_input(c).to(rdev)).cpu())[0])
        v_t = "blank" if (pred_t == "" and why_t is None) else (
            "det" if why_t else "read")
        pred_o, why_o = crop_pred(p_o, lambda c: greedy_np(
            run_reader_onnx(reader_ort, c)))
        v_o = "blank" if (pred_o == "" and why_o is None) else (
            "det" if why_o else "read")
    return (v_t, pred_t, sc), (v_o, pred_o, sc_o), {
        "iou": iou, "score_diff": abs(sc - sc_o),
        "agree": v_t == v_o and pred_t == pred_o,
    }


def _reader_input(crop):
    t = torch.from_numpy(crop).float().div_(255.).sub_(0.5)
    return t.unsqueeze(0).unsqueeze(0)


def box_iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def make_goldens():
    """Dart 전처리 고정용 합성 케이스. np.random.RandomState(42) 로 재현 가능."""
    rs = np.random.RandomState(42)
    cases = {"letterbox": [], "crop_resize": []}
    for h, w in [(60, 100), (100, 60), (77, 77)]:
        img = rs.randint(0, 256, (h, w), dtype=np.uint8)
        out, r, dx, dy = letterbox(img, 64)
        cases["letterbox"].append({
            "in_w": w, "in_h": h, "size": 64, "r": r, "dx": dx, "dy": dy,
            "in": _b64(img), "out": _b64(out)})
    for h, w in [(70, 120), (150, 200), (96, 144)]:
        img = rs.randint(0, 256, (h, w), dtype=np.uint8)
        cases["crop_resize"].append({
            "in_w": w, "in_h": h, "out_w": IN_W, "out_h": IN_H,
            "in": _b64(img), "out": _b64(cv2.resize(img, (IN_W, IN_H)))})
    (OUT / "golden_vectors.json").write_text(
        json.dumps(cases), encoding="utf-8")
    return sum(len(v) for v in cases.values())


def _b64(a):
    return base64.b64encode(a.tobytes()).decode("ascii")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="실촉 전량 e2e 파리티")
    ap.add_argument("--skip-export", action="store_true")
    ap.add_argument("--smoke", type=int, default=12)
    a = ap.parse_args()
    import onnxruntime as ort

    OUT.mkdir(exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    det, reader, size = load_torch_models(dev)

    if not a.skip_export:
        det_path = OUT / "band_detector.onnx"
        torch.onnx.export(
            det, torch.zeros(1, 1, size, size, device=dev), det_path,
            input_names=["image"], output_names=["obj", "reg"],
            opset_version=17, do_constant_folding=True)
        reader_path = OUT / "reader_crnn.onnx"
        torch.onnx.export(
            reader, torch.zeros(1, 1, IN_H, IN_W, device=dev), reader_path,
            input_names=["crop"], output_names=["logits"],
            opset_version=17, do_constant_folding=True)
        print(f"변환: {det_path.name} {det_path.stat().st_size/1e6:.2f}MB · "
              f"{reader_path.name} {reader_path.stat().st_size/1e6:.2f}MB")
    det_ort = ort.InferenceSession(str(OUT / "band_detector.onnx"),
                                   providers=["CPUExecutionProvider"])
    reader_ort = ort.InferenceSession(str(OUT / "reader_crnn.onnx"),
                                      providers=["CPUExecutionProvider"])

    # 리더 단위 파리티 — 정답 상자 크롭에서 logits 최대절대차.
    gts, imgs = load_corpus()
    ids = sorted(gts)
    rs = np.random.RandomState(7)
    sample = [i for i in ids if i.split("/", 1)[-1] not in ROTATED_90
              and str(gts[i]).lstrip("-").isdigit()]
    reader_max = 0.0
    reader_n = 0
    reader_decode_mismatch = []
    for cid in rs.choice(sample, 200, replace=False):
        img = cv2.imread(str(DATUMO / imgs[cid]), cv2.IMREAD_GRAYSCALE)
        h, w = img.shape
        x0, y0 = w // 4, h // 4
        crop = cv2.resize(img[y0:y0 + h // 2, x0:x0 + w // 2], (IN_W, IN_H))
        with torch.no_grad():
            tl = reader(_reader_input(crop).to(dev)).cpu().numpy()[0]
        ol = run_reader_onnx(reader_ort, crop)
        reader_max = max(reader_max, float(np.abs(tl - ol).max()))
        if decode_greedy(torch.from_numpy(tl).unsqueeze(0))[0] != greedy_np(ol):
            reader_decode_mismatch.append(cid)
        reader_n += 1
    print(f"리더 logits 파리티: n={reader_n} 최대절대차 {reader_max:.2e} "
          f"(torch {dev} vs ORT CPU) · 디코드 불일치 {len(reader_decode_mismatch)}")

    ng = make_goldens()
    print(f"골든 벡터: {ng} 케이스 -> {OUT/'golden_vectors.json'}")

    # e2e 파리티
    targets = sample if a.full else list(rs.choice(sample, a.smoke,
                                                   replace=False))
    stats = {"n": 0, "agree": 0, "verdict_disagree": [],
             "max_score_diff": 0.0, "min_iou": 1.0}
    t0 = time.time()
    rows = []
    for k, cid in enumerate(sorted(targets)):
        img = cv2.imread(str(DATUMO / imgs[cid]), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        t_row, o_row, cmp = e2e_one(img, det, reader, size, det_ort,
                                    reader_ort, det.stride)
        stats["n"] += 1
        stats["agree"] += int(cmp["agree"])
        stats["max_score_diff"] = max(stats["max_score_diff"],
                                      cmp["score_diff"])
        stats["min_iou"] = min(stats["min_iou"], cmp["iou"])
        if not cmp["agree"]:
            stats["verdict_disagree"].append(
                {"id": cid, "torch": t_row, "ort": o_row, **cmp})
        rows.append({"id": cid, "torch": t_row, "ort": o_row, **cmp})
        if a.full and k % 250 == 0:
            print(f"  {k}/{len(targets)} · {time.time()-t0:.0f}s", flush=True)

    tag = "full" if a.full else "smoke"
    out_jsonl = OUT / f"parity_{tag}.jsonl"
    out_jsonl.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                 for r in rows), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"e2e 파리티({tag}): 일치 {stats['agree']}/{stats['n']} · "
          f"min IoU {stats['min_iou']:.4f} · "
          f"max 점수차 {stats['max_score_diff']:.2e} -> {out_jsonl}")
    return 0 if stats["agree"] == stats["n"] and stats["verdict_disagree"] == [] else 1


if __name__ == "__main__":
    raise SystemExit(main())
