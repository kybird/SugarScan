# 밴드 검출망 예측을 웹툴 오버레이 규약으로 내보낸다.
#
# 배경(2026-09-14): 웹툴의 `/api/quads?kind=band` 는 `datumo_quads_v2.jsonl` 을
# 읽는데 그 파일이 저장소에 없다 — 옛 v2 밴드 모델 시절 산물이고 재구축 때
# 사라졌다. 그래서 밴드 예측 오버레이가 빈 채로 돌고 있었다.
#
# **2026-09-18 검출기를 바꿔 끼웠다** (사람 지시: "기존 webtool 의 검출기를
# 바꿔끼우자"). 구판은 폐기된 계열(`band_det_*.pt`, 4점 쿼드 회귀 CNN)을 쓰고
# **GM 크롭**을 입력으로 받았다. 새 검출망(BandNet, docs/SPEC.md §5.3)은
# **전체 혈당기 사진**을 받는다(§1.1) — 그래서 크롭 단계가 통째로 사라진다.
# GM 쿼드도 더 이상 필요 없다. 이것이 중요한 이유: GM 쿼드로 잘라 주는 것은
# 배포에 없는 오라클이고(§7-2), 화면에 그렇게 그리면 실제보다 좋아 보인다.
#
# 좌표계: **원본 사진 픽셀**(band_boxes.jsonl 과 같은 표시 좌표). 레터박스로
# 넣었다가 되돌린다. 이 변환을 빼먹으면 쿼드가 화면 좌상단으로 쏠려 그려진다 —
# [[unnamed-coordinate-frame]].
#
# 출력은 **축정렬 사각형**이지만 오버레이 규약이 쿼드 4점이라 네 귀로 적는다
# (SPEC §9.5 — 정답도 예측도 축정렬 사각형 하나다).
#
# 예측 파일임을 이름과 스키마로 밝힌다: 파일명에 `_pred`, 행마다 `source` 와
# `ckpt`. 라벨 파일과 같은 디렉터리에 같은 스키마로 두면 언젠가 실측으로
# 둔갑한다 — 그 사고가 2026-09-13 에 있었다
# ([[prediction-used-as-ground-truth]]).
#
# 사용:
#   python predict_band_quads.py --ckpt band_out/curve_07998.pt
#   python predict_band_quads.py --ckpt band_out/curve_02000.pt --limit 200
import argparse
import json
import time
from pathlib import Path

import cv2
import torch

from band_net import BandNet, decode
from train_band import letterbox

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"


def photo_index():
    """id -> 이미지 경로. labels.jsonl 이 코퍼스의 사진 목록 정본이다."""
    out = {}
    for line in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            out[j["id"]] = j["image"]
    return out


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="band_out/curve_07998.pt")
    ap.add_argument("--out", default="band_quads_pred.jsonl")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=0, help="0 이면 전량")
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = HERE / args.ckpt if not Path(args.ckpt).is_absolute() else Path(args.ckpt)
    c = torch.load(ck, map_location="cpu", weights_only=False)
    model = BandNet(width=c["width"]).to(dev).eval()
    model.load_state_dict(c["model"])
    size = c["size"]

    lab = photo_index()
    ids = sorted(lab)
    if args.limit:
        ids = ids[:args.limit]
    print(f"{ck.name}  width {c['width']} · {c['param']/1e6:.3f}M · "
          f"학습장수 {c['n_images']} · 입력 {size}")
    print(f"대상 {len(ids)}장 — **전체 혈당기 사진**을 그대로 넣는다(크롭 없음)")

    out = HERE / args.out
    n = miss = low = 0
    t0 = time.time()
    with open(out, "w", encoding="utf-8") as f:
        for i, pid in enumerate(ids):
            img = cv2.imread(str(DATUMO / lab[pid]), cv2.IMREAD_GRAYSCALE)
            if img is None:
                miss += 1
                continue
            lb, r, dx, dy = letterbox(img, size)
            x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
            obj, reg = model(x.to(dev))
            b, s = decode(obj.float(), reg.float(), model.stride)
            b = b[0].cpu().numpy()
            sc = float(s[0].cpu())
            if sc < args.conf:
                low += 1
                continue
            p = [(b[0]-dx)/r, (b[1]-dy)/r, (b[2]-dx)/r, (b[3]-dy)/r]
            f.write(json.dumps(dict(
                id=pid,
                quad=[[round(p[0], 2), round(p[1], 2)],
                      [round(p[2], 2), round(p[1], 2)],
                      [round(p[2], 2), round(p[3], 2)],
                      [round(p[0], 2), round(p[3], 2)]],
                source="detector", ckpt=ck.name, arch="bandnet",
                score=round(sc, 4)), ensure_ascii=False) + "\n")
            n += 1
            if (i + 1) % 250 == 0:
                print(f"  {i + 1}/{len(ids)}  {time.time() - t0:.0f}s", flush=True)
    print(f"{out}  {n}장 기록 · 이미지 없음 {miss} · "
          f"conf<{args.conf} 로 버림 {low} · {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
