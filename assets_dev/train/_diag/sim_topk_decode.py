# BandNet 디코드 완화 시뮬레이션 — 정점 1칸 argmax 대신 상위 k칸 후보에서
# 면적 사전을 통과하는 최고 점수 칸을 고르는 규칙이 검출 실패를 얼마나
# 줄이는지 전량 코퍼스에서 잰다(2026-10-04, 사람: "왜 큰숫자를 나두고 작은
# 사각형을 검출하는지… 어떻게 개선해야할지도 모르겠어").
#
# 배경(실패 5장 실측): obj(존재)와 reg(크기)가 별개 머리인데 현행 decode 는
# 전역 정점 한 칸의 reg 만 믿는다. 1840·2074 는 숫자줄 obj 가 0.42/0.93 으로
# 뜨거운데 정점이 상자 바로 위 구석 칸(사진 좌표 (437,437)·(277,277))에
# 0.64/0.94 로 찍혀 그 칸의 무너진 reg(128×111·148×129px)가 최종 상자가
# 됐다. 규칙 자체를 바꾸면 학습 없이 회복 가능한지 본다.
#
# 규칙(사전 선언, 데이터 맞춤 없음): 후보 = obj 상위 32칸. 각 칸의 상자가
# 2%<=면적비<=60% 이고 화면 안 90% 이상이면 통과. 통과자 중 최고 obj 를
# 선택, 점수=그 칸의 obj. 통과자가 없으면 현행과 동일(전역 정점 그대로).
# 게이트는 배포와 동일(conf 0.25 · 면적 2%).
#
# 사용: python _diag/sim_topk_decode.py
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from band_net import BandNet, decode  # noqa: E402
from predict_band_quads import DATUMO, photo_index  # noqa: E402
from train_band import letterbox  # noqa: E402

CKPT = HERE / "band_out" / "tone" / "gen1_v1"
K = 32
FRAC_LO, FRAC_HI = 0.02, 0.60
INFRAME = 0.90
CONF = 0.25


def boxes_from_cells(o_sigmoid, reg, cells, r, dx, dy, stride):
    out = []
    for (gy, gx) in cells:
        cx, cy = (gx + 0.5) * stride, (gy + 0.5) * stride
        d = reg[0, :, gy, gx].cpu().numpy()
        out.append(([cx - d[0], cy - d[1], cx + d[2], cy + d[3]],
                    float(o_sigmoid[gy, gx])))
    return out


def pick(o_sigmoid, reg, r, dx, dy, stride, W, H):
    """(현행 상자·점수, topk 상자·점수) — 사진 좌표."""
    flat = o_sigmoid.reshape(-1)
    order = np.argsort(flat)[::-1]
    cells = [(int(i // o_sigmoid.shape[1]), int(i % o_sigmoid.shape[1]))
             for i in order[:K]]
    cands = boxes_from_cells(o_sigmoid, reg, cells, r, dx, dy, stride)
    base = cands[0]                       # argsort[0] = 전역 정점
    base_p = [(v - (dx if i % 2 == 0 else dy)) / r for i, v in enumerate(base[0])]
    best = None
    for box, sc in cands:
        p = [(box[0] - dx) / r, (box[1] - dy) / r,
             (box[2] - dx) / r, (box[3] - dy) / r]
        bw, bh = p[2] - p[0], p[3] - p[1]
        if bw <= 0 or bh <= 0:
            continue
        frac = bw * bh / max(1.0, W * H)
        ix = max(0.0, min(p[2], W) - max(p[0], 0.0))
        iy = max(0.0, min(p[3], H) - max(p[1], 0.0))
        inside = (ix * iy) / (bw * bh)
        if FRAC_LO <= frac <= FRAC_HI and inside >= INFRAME:
            if best is None or sc > best[1]:
                best = (p, sc)
    return base_p, base[1], (best[0] if best else base_p), (best[1] if best else base[1])


def main():
    c = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = BandNet(width=c["width"], stride=c.get("stride", 16)).cuda().eval()
    model.load_state_dict(c["model"])
    size = c["size"]
    lab = photo_index()
    gts = {}
    for line in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            gts[j["id"]] = j.get("image")

    rows = []
    n = fail_base = fail_topk = changed = 0
    for pid in sorted(gts):
        img = cv2.imread(str(DATUMO / gts[pid]), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        n += 1
        H, W = img.shape
        lb, r, dx, dy = letterbox(img, size)
        x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            obj, reg = model(x.cuda())
        o = torch.sigmoid(obj)[0, 0].cpu().numpy()
        bp, bs, tp, ts = pick(o, reg, r, dx, dy, model.stride, W, H)

        def ok(p, s):
            frac = (p[2] - p[0]) * (p[3] - p[1]) / max(1.0, W * H)
            return s >= CONF and frac >= FRAC_LO

        b_ok, t_ok = ok(bp, bs), ok(tp, ts)
        fail_base += not b_ok
        fail_topk += not t_ok
        iou_b_t = 0.0
        ix = max(0, min(bp[2], tp[2]) - max(bp[0], tp[0]))
        iy = max(0, min(bp[3], tp[3]) - max(bp[1], tp[1]))
        inter = ix * iy
        ua = ((bp[2] - bp[0]) * (bp[3] - bp[1])
              + (tp[2] - tp[0]) * (tp[3] - tp[1]) - inter)
        if ua > 0:
            iou_b_t = inter / ua
        changed += iou_b_t < 0.9
        rows.append(dict(id=pid, base=(round(bp[0]), round(bp[1]), round(bp[2]),
                                       round(bp[3]), round(bs, 3)),
                         topk=(round(tp[0]), round(tp[1]), round(tp[2]),
                               round(tp[3]), round(ts, 3)),
                         base_ok=bool(b_ok), topk_ok=bool(t_ok),
                         iou=float(round(iou_b_t, 3))))
        if n % 500 == 0:
            print(f"  {n}장 · base실패 {fail_base} · topk실패 {fail_topk}", flush=True)
    print(f"전량 {n}장")
    print(f"현행 디코드 검출실패 {fail_base}  ->  topk 디코드 검출실패 {fail_topk}")
    print(f"현행과 상자가 달라진(IoU<0.9) 장: {changed}")
    lost = [r0["id"] for r0 in rows if r0["base_ok"] and not r0["topk_ok"]]
    gained = [r0["id"] for r0 in rows if not r0["base_ok"] and r0["topk_ok"]]
    print("새로 실패(topk가 잃은 장):", [i.split("/")[-1] for i in lost])
    print("회복(topk가 얻은 장):", [i.split("/")[-1] for i in gained])
    dst = HERE / "_diag" / "sim_topk_decode_gen1.json"
    dst.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
