# 끝단 측정 — BandNet 검출기 × CRNN 리더를 실촬 전사진으로 잰다.
#
# 사람 지시(2026-10-03): "끝단 측정해보자". 옛 eval_e2e_real.py 는 폐기된
# YOLOX 계열 + GM 화면 크롭(배포에 없는 오라클) 전제라 못 쓴다 — 이 자는
# **배포 경로 그대로** 잰다: 원본 사진 → BandNet(전체사진 입력) → 상자
# (conf·스케일 게이트) → 리더 크롭 규약(reader_crnn.BandCrops 와 동일:
# grayscale → resize 144×96 → /255−0.5) → CTC greedy → 값.
#
# 채점 정답은 labels.jsonl 의 reading(값)이다 — 밴드 박스 라벨이 필요
# 없어 2,512장 전량에서 잰다(사람 질문 "왜 223장만"의 답이 이 경로).
#
# 실패 분류: det(검출 실패: conf/게이트) / blank(리더 빈 출력) /
# wrong(오독) / right. 비숫자 GT(HI/LO 등)는 skip 으로 센다.
#
# 사용:
#   python eval_e2e_bandnet.py                       # tg 기본
#   python eval_e2e_bandnet.py --ckpt_det band_out/tone/atone_tf640w15 --tag tf
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import torch

from band_net import BandNet, decode
from reader_crnn import CRNN, IN_H, IN_W, NUM_CLASSES, decode_greedy, decode_beam
from train_band import letterbox

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"

# 90° 회전 사진 — 사람 선언(2026-10-04 "애당초 모델에 90도돌아간건
# 보여주지도않았잖아")으로 평가에서 제외한다. 2026-10-05 시각 재확인
# (_diag/rot5_check.png, 5장 전부 90°) + 같은 날 사람 지적으로 283 추가
# (B판 감안 — 어두운 노출이라 1차 시각 검증이 정방향으로 오판했다.
# ±90° 회전본 병치 시험 _diag/rot_ab_283_1709.png 로 확정: 정방향은
# 시계 90° 회전본). 리뷰 몽타주에서만 빼고 e2e 에는 남아 있던 것을
# 이날 정식화했다. 2431(두 자리만 촬영, 라벨 오염)은 코퍼스 자체에서
# 이미 제외된 별건이다.
ROTATED_90 = {"1213", "1226", "1564", "1565", "940", "283"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt_det", default=str(HERE / "band_out" / "tone" / "atone_tg640w15"))
    ap.add_argument("--ckpt_reader", default=str(HERE / "reader_crnn_v2_1" / "best.pt"))
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--min-frac", type=float, default=0.02,
                    help="스케일 게이트 — 예측 면적/화면 하한(eval·predict 와 동일)")
    ap.add_argument("--tag", default=None, help="결과 파일 접두(기본: 검출 ckpt 이름)")
    ap.add_argument("--beam", type=int, default=0,
                    help="0=greedy(구동작), N>=1 은 CTC prefix 빔(2026-10-03 재작성)")
    ap.add_argument("--boxes-file", default=None,
                    help="검출기를 돌리지 않고 이 상자 jsonl(band_quads_pred 규약)을"
                         " 쓴다 — 상자 후처리(예: 오른쪽 패드) 실험용")
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    cd = torch.load(a.ckpt_det, map_location="cpu", weights_only=False)
    det = BandNet(width=cd["width"], stride=cd.get("stride", 16)).to(dev).eval()
    det.load_state_dict(cd["model"])
    cr = torch.load(a.ckpt_reader, map_location="cpu", weights_only=False)
    reader = CRNN(NUM_CLASSES).to(dev).eval()
    reader.load_state_dict(cr.get("model", cr))

    gts = {}
    imgs = {}
    for line in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            gts[j["id"]] = j["reading"]
            imgs[j["id"]] = j["image"]

    tag = a.tag or Path(a.ckpt_det).stem
    ext_boxes = None
    if a.boxes_file:
        ext_boxes = {}
        for line in Path(a.boxes_file).read_text(encoding="utf-8").splitlines():
            if line.strip():
                j = json.loads(line)
                if j.get("quad"):
                    xs = [p[0] for p in j["quad"]]
                    ys = [p[1] for p in j["quad"]]
                    ext_boxes[j["id"]] = [min(xs), min(ys), max(xs), max(ys)]
        if a.tag:
            tag = a.tag
    if a.beam:
        tag += f"_beam{a.beam}"
    out_p = HERE / "_diag" / "e2e_bandnet" / f"{tag}.jsonl"
    out_p.parent.mkdir(parents=True, exist_ok=True)

    stats = {"right": 0, "wrong": 0, "blank": 0, "det": 0, "skip": 0}
    wrong_rows = []
    t0 = time.time()
    with out_p.open("w", encoding="utf-8") as f, torch.no_grad():
        for k, (cid, gt) in enumerate(sorted(gts.items())):
            if cid.split("/", 1)[-1] in ROTATED_90:
                stats["skip"] += 1
                f.write(json.dumps({"id": cid, "verdict": "skip",
                                    "why": "rotated_90"},
                                   ensure_ascii=False) + "\n")
                continue
            if not str(gt).lstrip("-").isdigit():
                stats["skip"] += 1
                continue
            img = cv2.imread(str(DATUMO / imgs[cid]), cv2.IMREAD_GRAYSCALE)
            if img is None:
                stats["skip"] += 1
                continue
            if ext_boxes is not None:
                eb = ext_boxes.get(cid)
                if eb is None:
                    stats["det"] += 1
                    f.write(json.dumps({"id": cid, "verdict": "det",
                                        "gt": gt}, ensure_ascii=False) + chr(10))
                    continue
                p = list(eb)
                sc = 1.0
            else:
                lb, r, dx, dy = letterbox(img, cd["size"])
                x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
                obj, reg = det(x.to(dev))
                b, s = decode(obj.float(), reg.float(), det.stride)
                b = b[0].cpu().numpy()
                sc = float(s[0].cpu())
                p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
            frac = ((p[2]-p[0]) * (p[3]-p[1])) / max(1.0, img.shape[1] * img.shape[0])
            row = {"id": cid, "gt": gt, "score": round(sc, 3)}
            if sc < a.conf or frac < a.min_frac:
                stats["det"] += 1
                row.update(verdict="det", score=round(sc, 2),
                           frac=round(frac, 4))
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                continue
            x0, y0 = max(0, int(p[0])), max(0, int(p[1]))
            x1 = min(img.shape[1], int(round(p[2])))
            y1 = min(img.shape[0], int(round(p[3])))
            if x1 - x0 < 4 or y1 - y0 < 4:
                stats["det"] += 1
                f.write(json.dumps({**row, "verdict": "det",
                                    "why": "tiny_box"}, ensure_ascii=False) + "\n")
                continue
            crop = cv2.resize(img[y0:y1, x0:x1], (IN_W, IN_H))
            t = torch.from_numpy(crop).float().div_(255.).sub_(0.5).unsqueeze(0).unsqueeze(0)
            logits = reader(t.to(dev))
            if a.beam:
                pred = decode_beam(logits[0].cpu().unsqueeze(0),
                                   beam_width=a.beam)[0]
            else:
                pred = decode_greedy(logits[0].cpu().unsqueeze(0))[0]
            row["pred"] = pred
            if not pred:
                stats["blank"] += 1
                row["verdict"] = "blank"
            elif pred == str(int(gt)):
                stats["right"] += 1
                row["verdict"] = "right"
            else:
                stats["wrong"] += 1
                row["verdict"] = "wrong"
                if len(wrong_rows) < 30:
                    wrong_rows.append((cid, gt, pred))
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            if k % 250 == 0:
                print(f"  {k}/{len(gts)} · {time.time()-t0:.0f}s", flush=True)

    n = stats["right"] + stats["wrong"] + stats["blank"]
    print(f"[{tag}] 전량 {len(gts)} · skip {stats['skip']} · 검출실패 {stats['det']}")
    print(f"  채점 {n}장: 정답 {stats['right']} ({100*stats['right']/max(1,n):.1f}%)"
          f" · 오독 {stats['wrong']} · 빈출력 {stats['blank']}")
    print(f"  전량 기준 판독률 {100*stats['right']/len(gts):.1f}%  -> {out_p}")
    for cid, gt, pr in wrong_rows[:10]:
        print(f"    오독 {cid.split('/')[-1]:<7} GT {gt:>3} pred {pr or '(빈)'}")


if __name__ == "__main__":
    main()
