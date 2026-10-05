# 검출 실패 19장의 게이트 적용 전 최상위 후보를 뽑는다(2026-10-04).
#
# 왜 필요한가 — predict_band_quads.py 는 conf·스케일 게이트를 **쓰기 전에**
# 걸러서, 게이트에 걸린 장은 원시 덤프에 행이 아예 없다. e2e(tg_v11e) 행에는
# 점수·면적비만 있고 좌표가 없어 "버려진 상자가 어디에 있었는지"를 그릴 수
# 없다. 몽타주 주황 상자의 출처로 쓴다.
#
# 2026-10-04 사람 요청("인식 못하는 이유를 분석")으로 --ckpt/--ids 를 받게
# 일반화 — 같은 실패 목록을 다른 검출기(예: 저대비 축을 학습한 gen1_v1)에
# 통과시켜 점수 회복 여부를 보는 것이 목적이다.
#
# 사용:
#   python _diag/probe_fail19_raw.py                       # atone_tg640w15·19장
#   python _diag/probe_fail19_raw.py --ckpt band_out/gen1_v1 --tag gen1
import argparse
import json
import sys
from pathlib import Path

import cv2
import torch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from predict_band_quads import DATUMO, photo_index  # noqa: E402
from band_net import BandNet, decode  # noqa: E402
from train_band import letterbox  # noqa: E402

DEFAULT_CKPT = str(HERE / "band_out" / "tone" / "atone_tg640w15")

# e2e tg_v11e 검출 실패 19장(2026-10-04 실측 — 집합 원본은 e2e jsonl).
FAILS = [
    "glucose_batch1/1213", "glucose_batch1/1226", "glucose_batch1/1565",
    "glucose_batch1/1705", "glucose_batch1/1706", "glucose_batch1/1710",
    "glucose_batch1/1762", "glucose_batch1/1781", "glucose_batch1/214",
    "glucose_batch1/2317", "glucose_batch1/2319", "glucose_batch1/2414",
    "glucose_batch1/498", "glucose_batch1/501", "glucose_batch1/525",
    "glucose_batch1/725", "glucose_batch1/728", "glucose_batch1/756",
    "glucose_batch1/940",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default=DEFAULT_CKPT)
    ap.add_argument("--ids", help="쉼표 구분 id(접두 glucose_batch1/ 생략). "
                                  "없으면 FAILS 19장 전부")
    ap.add_argument("--tag", default=None, help="출력 json 접미사(없으면 체크포인트명)")
    args = ap.parse_args()
    ids = ([("glucose_batch1/" + s.strip()) for s in args.ids.split(",")]
           if args.ids else list(FAILS))
    tag = args.tag or Path(args.ckpt).name

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    c = torch.load(args.ckpt, map_location="cpu", weights_only=False)
    model = BandNet(width=c["width"], stride=c.get("stride", 16)).to(dev).eval()
    model.load_state_dict(c["model"])
    size = c["size"]
    lab = photo_index()
    out = []
    for pid in ids:
        img = cv2.imread(str(DATUMO / lab[pid]), cv2.IMREAD_GRAYSCALE)
        if img is None:
            out.append(dict(id=pid, error="decode_fail"))
            continue
        lb, r, dx, dy = letterbox(img, size)
        x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            obj, reg = model(x.to(dev))
            b, s = decode(obj.float(), reg.float(), model.stride)
        b = b[0].cpu().numpy()
        sc = float(s[0].cpu())
        p = [(b[0] - dx) / r, (b[1] - dy) / r, (b[2] - dx) / r, (b[3] - dy) / r]
        frac = ((p[2] - p[0]) * (p[3] - p[1])) / max(1.0, img.shape[1] * img.shape[0])
        out.append(dict(id=pid, score=round(sc, 4), frac=round(frac, 4),
                        box=[round(v, 1) for v in p]))
    dst = HERE / "_diag" / f"fail19_raw_probe_{tag}.json"
    dst.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for o in out:
        if "error" in o:
            print(f"{o['id']:>24}  {o['error']}")
        else:
            print(f"{o['id']:>24}  sc{o['score']:.2f} frac{o['frac']*100:.2f}% "
                  f"box={o['box']}")
    print(dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
