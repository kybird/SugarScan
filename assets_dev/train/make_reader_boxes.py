# 리더 학습용 검출 예측 상자를 합성 세트 위에 낸다.
#
# 정합성 수리(2026-10-03, 사람 지적 "검출기가 바뀌었는데 이전 검출기로
# 학습한 걸 쓰는 게 맞아?"): 리더 v2.1 은 폐기 YOLOX(bandft_v2) 의 예측
# 상자로 학습됐다 — 설계 원칙('검출 예측 상자로 학습 = 배포 동등')이 깨진
# 상태. 이 자는 현 배포 검출기(BandNet) 의 상자를 B2/C2 패널 전체 위에
# 내서 reader_crnn.py train --boxes 규격으로 쓴다:
#   {"file_name": "panel_..._0.png", "pred": [x0, y0, x1, y1]}
# conf·스케일 게이트 미달 장은 적지 않는다(스킵=배포에서 검출 실패과
# 동등 — 리더가 그 장을 학습하지 않는다, 옛 체인과 같은 규칙).
#
# 사용:
#   python make_reader_boxes.py --set B2            # _diag/reader_boxes/B2_tg.jsonl
import argparse
import json
import time
from pathlib import Path

import cv2
import torch

from band_net import BandNet, decode
from train_band import letterbox

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="B2")
    ap.add_argument("--ckpt", default=str(HERE / "band_out" / "tone" / "atone_tg640w15"))
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--min-frac", type=float, default=0.02)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    c = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    model = BandNet(width=c["width"], stride=c.get("stride", 16)).to(dev).eval()
    model.load_state_dict(c["model"])
    size = c["size"]
    tag = Path(a.ckpt).stem.replace("atone_", "")

    set_dir = HERE / "synth_coco" / a.set
    files = sorted((set_dir / "train2017").glob("*.png"))
    out_p = Path(a.out) if a.out else HERE / "_diag" / "reader_boxes" / f"{a.set}_{tag}.jsonl"
    out_p.parent.mkdir(parents=True, exist_ok=True)

    n_ok = n_skip = 0
    t0 = time.time()
    with out_p.open("w", encoding="utf-8") as f, torch.no_grad():
        for k, p in enumerate(files):
            img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if img is None:
                n_skip += 1
                continue
            lb, r, dx, dy = letterbox(img, size)
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            obj, reg = model(x.to(dev))
            b, s = decode(obj.float(), reg.float(), model.stride)
            b = b[0].cpu().numpy()
            sc = float(s[0].cpu())
            box = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
            frac = ((box[2]-box[0]) * (box[3]-box[1])) / (img.shape[1] * img.shape[0])
            if sc < a.conf or frac < a.min_frac:
                n_skip += 1
                continue
            f.write(json.dumps({"file_name": p.name,
                                "pred": [round(v, 2) for v in box]}) + "\n")
            n_ok += 1
            if k % 200 == 0:
                print(f"  {k}/{len(files)} · {time.time()-t0:.0f}s", flush=True)
    print(f"{out_p.name}: {n_ok}개 상자 · 스킵 {n_skip}(검출 실패=배포 동등)")


if __name__ == "__main__":
    main()
