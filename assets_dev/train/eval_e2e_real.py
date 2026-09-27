# 실사진 끝단 파이프라인 측정 — 검출기 v2 + 리더 v2.1 통과(2026-09-26).
# 카드 「실사진 끝단 파이프라인 측정」. 합성 97%의 실사진 대응치를 잰다.
#
# 경로: 실사진 → LCD 프레이밍(framed_src_rect) → 검출기 v2(박스) →
#       리더 v2.1(값) → 정답 라벨과 채점.
# 정답: band_boxes.jsonl(사람 밴드 라벨) — 단, 파이프라인이 박스를 내면
#       그 박스로 크롭해 리더가 읽게 한다(배포 동등). 정답값은 매니페스트가
#       아니라 실사진의 사람 라벨과 대응되는 코퍼스 라벨(labels.jsonl)이다.
#
# 사용: python eval_e2e_real.py [--ckpt_det ...] [--ckpt_reader ...]
import argparse
import json
import sys

import cv2
import numpy as np
import torch

HERE = __import__("pathlib").Path(__file__).resolve().parent
sys.path.insert(0, "D:/tmp/YOLOX")

from build_cache_v2 import framed_src_rect          # noqa: E402
from gm_quads import quad_rows                     # noqa: E402
from band_exclusions import load_excluded          # noqa: E402
from reader_crnn import (CRNN, IN_W, IN_H, NUM_CLASSES,  # noqa: E402
                          decode_greedy, CHARSET, BLANK)
from yolox.exp import get_exp as get_yolox_exp    # noqa: E402
from yolox.utils import postprocess as yx_post    # noqa: E402
from yolox.data.data_augment import ValTransform  # noqa: E402

DATUMO = HERE.parent / "upstream" / "datumo"
SPLIT = HERE / "_diag" / "band_device_split" / "band_device_split.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt_det", default=str(
        HERE / "yolox_out" / "bandft_v2" / "best_ckpt.pth"))
    ap.add_argument("--ckpt_reader", default=str(
        HERE / "reader_crnn_v2_1" / "best.pt"))
    ap.add_argument("--exp", default=str(HERE / "yolox_synthband_exp.py"))
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--out", default=str(HERE / "_diag" / "e2e_real"))
    args = ap.parse_args()
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 정답값: Datumo 코퍼스 labels.jsonl 의 reading 필드(사람 지적으로 재확인
    # 2026-09-26 — 실사진 혈당값이 처음부터 여기 있었다).
    gt_values = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if j.get("reading") is not None:
                gt_values[j["id"]] = str(j["reading"])

    # 홀드아웃 id
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    holdout = set(split["holdout_ids"])
    excluded = set(load_excluded())

    # 라벨 좌표(체점용 GT 박스)
    bands = {}
    for l in (HERE / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if j.get("quad"):
                q = np.asarray(j["quad"], float)
                bands[j["id"]] = [q[:, 0].min(), q[:, 1].min(),
                                  q[:, 0].max(), q[:, 1].max()]

    gm = {r["id"]: r for r in quad_rows()}
    labels = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labels[j["id"]] = j["image"]
            if j["id"] not in gt_values and j.get("reading") is not None:
                gt_values[j["id"]] = str(j["reading"])

    # 대상: 값 라벨 있음 ∩ 홀드아웃 ∩ 제외 아님
    ids = [i for i in sorted(gt_values)
           if i in holdout and i not in excluded
           and i in gm and i in labels]
    print(f"측정 대상: {len(ids)}장 (값 라벨 {len(gt_values)} 중 홀드아웃+유효)")

    # 검출기
    yx_exp = get_yolox_exp(args.exp, None)
    det_model = yx_exp.get_model().to(dev).eval()
    det_model.load_state_dict(
        torch.load(args.ckpt_det, map_location="cpu")["model"])
    pre = ValTransform(legacy=False)

    # 리더
    reader = CRNN(NUM_CLASSES).to(dev).eval()
    ckpt = torch.load(args.ckpt_reader, map_location="cpu")
    reader.load_state_dict(ckpt.get("model", ckpt))

    from pathlib import Path as P
    out = P(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for cid in ids:
        img = cv2.imread(str(DATUMO / labels[cid]))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fr = framed_src_rect(gray, gm[cid]["quad"])
        x0, y0 = int(fr[0][0]), int(fr[0][1])
        x1, y1 = int(fr[2][0]), int(fr[2][1])
        crop = img[y0:y1, x0:x1]
        if crop.size == 0 or min(crop.shape[:2]) < 16:
            rows.append({"id": cid, "gt": gt_values[cid], "det": "crop_fail"})
            continue
        # letterbox 파라미터 계산(ValTransform 과 동일한 스케일)
        ch, cw = crop.shape[:2]
        ts = yx_exp.test_size
        r = min(ts[0] / ch, ts[1] / cw)
        nw, nh = int(round(cw * r)), int(round(ch * r))
        pad_x = (ts[1] - nw) // 2
        pad_y = (ts[0] - nh) // 2
        t, _ = pre(crop, None, ts)
        with torch.no_grad():
            det = yx_post(
                det_model(torch.from_numpy(t).unsqueeze(0).float().to(dev)),
                yx_exp.num_classes, args.conf, 0.45, class_agnostic=True)[0]
        if det is None or len(det) == 0:
            rows.append({"id": cid, "gt": gt_values[cid], "det": "miss"})
            continue
        o = det.cpu().numpy()
        sc = o[:, 4] * o[:, 5]
        k = int(np.argmax(sc))
        # letterbox 640 공간 → crop 공간 → 원본 공간
        bx = o[k][:4].astype(float)
        cx0 = (bx[0] - pad_x) / r
        cy0 = (bx[1] - pad_y) / r
        cx1 = (bx[2] - pad_x) / r
        cy1 = (bx[3] - pad_y) / r
        box = [max(0, cx0)+x0, max(0, cy0)+y0,
               min(cw, cx1)+x0, min(ch, cy1)+y0]

        # 리더: 크롭 → IN_W×IN_H → CRNN
        ry0, ry1 = int(max(0, box[1])), int(min(img.shape[0], box[3]))
        rx0, rx1 = int(max(0, box[0])), int(min(img.shape[1], box[2]))
        rc = cv2.resize(img[ry0:ry1, rx0:rx1], (IN_W, IN_H))
        x = torch.from_numpy(
            cv2.cvtColor(rc, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        ).unsqueeze(0).unsqueeze(0).to(dev)
        with torch.no_grad():
            logits = reader(x)
        pred = decode_greedy(logits.cpu())[0]

        gt = gt_values[cid]
        gt_box = bands.get(cid)
        iou = 0.0
        if gt_box:
            ix0, iy0 = max(gt_box[0], box[0]), max(gt_box[1], box[1])
            ix1, iy1 = min(gt_box[2], box[2]), min(gt_box[3], box[3])
            inter = max(0, ix1-ix0) * max(0, iy1-iy0)
            ua = ((gt_box[2]-gt_box[0])*(gt_box[3]-gt_box[1])
                  + (box[2]-box[0])*(box[3]-box[1]) - inter)
            iou = inter/ua if ua > 0 else 0
        rows.append({"id": cid, "gt": gt, "pred": pred,
                     "ok": pred == gt, "det_iou": round(iou, 3)})

    (out / "rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")
    scored = [r for r in rows if "pred" in r]
    ok = sum(1 for r in scored if r["ok"])
    print(f"\n실사진 끝단 결과:")
    print(f"  측정 {len(rows)}장 · 리더 도달 {len(scored)}장 "
          f"(검출 실패 {sum(1 for r in rows if r.get('det') in ('miss','crop_fail'))})")
    print(f"  완전일치 {ok}/{len(scored)} = {100*ok/max(1,len(scored)):.1f}%")
    print(f"  합성 대비 갭: 97.0% → {100*ok/max(1,len(scored)):.1f}%")
    if scored:
        wrong = [r for r in scored if not r["ok"]]
        if wrong:
            print(f"  오독 {len(wrong)}건:")
            for r in wrong[:15]:
                print(f"    {r['id']}: GT {r['gt']} → {r['pred']}"
                      f"  (IoU {r['det_iou']})")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
