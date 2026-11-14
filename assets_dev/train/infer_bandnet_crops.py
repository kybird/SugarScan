# BandNet 검출기로 장면그룹 세트에서 크롭 제안을 뽑는다(2026-11-15, 설계 §4).
#
# 왜: 리더는 "검출기가 실제로 제안한 상자를 앱과 같은 방식으로" 잘라 144x96
# 으로 배운다(docs/reports/mosaic-rejection-training-design.md §4). GT 상자로
# 학습한 리더는 배포에서 검출 상자의 오차를 못 견딘다 — 옛 파이프라인의
# B=리더 학습(검출기가 처음 보는 장) 규칙과 같은 이유다.
#
# 출력 jsonl 행: {"file_name", "pred": [x0,y0,x1,y1] | null, "score",
#                "kind": "pos"|"neg", "label": 문자열 | ""}
#   - 양성: 게이트 통과 여부와 무관하게 최고 점수 상자를 낸다(라벨=정답).
#     게이트를 넘지 못한 양성은 pred=null — 리더 학습에서 건너뛴다.
#   - 음성: **앱 게이트(점수>=CONF, 면적>=MIN_FRAC)를 통과한 오검출만**
#     pred 를 낸다(라벨=""). 통과 못 한 음성은 pred=null — 리더가 볼 필요가
#     없다(검출기가 이미 거절했다).
#
# 사용:
#   python infer_bandnet_crops.py --set synth_coco/SGD_READER \
#       --ckpt band_out/sgd_base.pt --out band_out/sgd_base_reader_crops.jsonl
import argparse
import json
from pathlib import Path

import cv2
import torch

from band_net import BandNet, decode
from train_band import letterbox

CONF_GATE = 0.25     # 앱 검출 게이트(export_deploy_onnx 와 같은 값)
MIN_FRAC = 0.02


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()
    root = Path(args.set)
    dev = torch.device(args.device if torch.cuda.is_available() else "cpu")
    ck = torch.load(args.ckpt, map_location="cpu")
    model = BandNet(width=ck.get("width", 1.0), stride=ck.get("stride", 16))
    model.load_state_dict(ck["model"])
    model = model.to(dev).eval()
    size = ck.get("size", 416)
    man = [json.loads(l) for l in
           (root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
           if l.strip()]
    rows = []
    n_gate_pos = n_fp = 0
    with torch.no_grad():
        for m in man:
            img = cv2.imread(str(root / "train2017" / f"{m['id']}.png"),
                             cv2.IMREAD_GRAYSCALE)
            assert img is not None, m["id"]
            lb, r, dx, dy = letterbox(img, size)
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            o, g = model(x.to(dev))
            b, sc = decode(o.float(), g.float(), model.stride)
            b = b[0].cpu().numpy()
            score = float(sc[0].cpu())
            p = [(b[0] - dx) / r, (b[1] - dy) / r,
                 (b[2] - dx) / r, (b[3] - dy) / r]
            frac = ((p[2] - p[0]) * (p[3] - p[1])
                    / (img.shape[0] * img.shape[1]))
            gate = score >= CONF_GATE and frac >= MIN_FRAC
            if m["has_band"]:
                if gate:
                    rows.append(dict(file_name=f"{m['id']}.png",
                                     pred=[round(float(v), 1) for v in p],
                                     score=round(score, 4), kind="pos",
                                     label=m["label"]))
                    n_gate_pos += 1
                else:
                    rows.append(dict(file_name=f"{m['id']}.png", pred=None,
                                     score=round(score, 4), kind="pos",
                                     label=m["label"]))
            else:
                # 음성은 게이트를 넘은 오검출 크롭만 — 빈 라벨로.
                if gate:
                    rows.append(dict(file_name=f"{m['id']}.png",
                                     pred=[round(float(v), 1) for v in p],
                                     score=round(score, 4), kind="neg",
                                     label=""))
                    n_fp += 1
                else:
                    rows.append(dict(file_name=f"{m['id']}.png", pred=None,
                                     score=round(score, 4), kind="neg",
                                     label=""))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r_ in rows:
            f.write(json.dumps(r_, ensure_ascii=False) + "\n")
    n_pos = sum(1 for r_ in rows if r_["kind"] == "pos")
    print(f"크롭 제안: 양성 {n_pos} (게이트 통과 {n_gate_pos}) · "
          f"음성 오검출 크롭 {n_fp} · -> {out}")


if __name__ == "__main__":
    main()
