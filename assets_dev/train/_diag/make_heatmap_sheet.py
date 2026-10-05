# BandNet 중간 산출 시각화 — GEN1 검출기가 실패 장에서 어디를 "밴드"로
# 믿는지(objectness 히트맵)와 숫자줄 칸들이 내놓는 상자(칸별 회귀)를 그린다
# (2026-10-04, 사람: "왜 이런 결과가 나오는지 중간과정을 분석해볼 수 없냐").
#
# 구조(band_net.py): /16 격자 칸마다 objectness 1 + (l,t,r,b) 거리 4.
# 후처리는 전역 argmax 하나 — 정점 칸의 회귀값으로 상자를 만들고 NMS 는
# 없다. 그래서 (1) 정점이 어디 찍히는지 (2) 숫자줄 칸의 objectness 는 얼마인지
# (3) 그 칸들의 회귀 상자는 어떤지를 보면 실패 단계가 드러난다.
#
# 한 행 = [실패 사진+히트맵+정점+상자 | 히트맵 단독 | 같은 기종 성공 사진+히트맵].
# 빨간 십자 = 정점 칸. 주황 = 최종 상자. 노란 얇은 선 = 숫자줄 참조 상자 안
# 칸들의 회귀 상자(참조 = 배포 TG 덤프 상자, 이 사진들은 TG 가 잡았다).
#
# 사용: python _diag/make_heatmap_sheet.py
import json
import random
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
CASES = ["1639", "1709", "818", "1840", "2074"]   # GEN1 신규 실패(사람 지적 장)
TH = 28.0          # 히트맵 표시 상한(objectness 낮은 장도 볼 수 있게 log 스케일 아님)
CH2 = 360          # 셀 세로


def heat_overlay(img, obj, r, dx, dy, size, stride, boxes_extra=None):
    """obj(1,Hc,Wc) logits → 사진 좌표 히트맵 오버레이 RGB."""
    heat = torch.sigmoid(obj)[0, 0].cpu().numpy()
    h, w = img.shape
    nh, nw = int(round(h * r)), int(round(w * r))
    big = cv2.resize(heat, (size, size), interpolation=cv2.INTER_NEAREST)
    cell = big[dy:dy + nh, dx:dx + nw]
    cell = cv2.resize(cell, (w, h), interpolation=cv2.INTER_LINEAR)
    cell = np.clip(cell / TH, 0, 1)
    hm = cv2.applyColorMap((cell * 255).astype(np.uint8), cv2.COLORMAP_JET)
    rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    mask = cell > 0.02
    out = rgb.copy()
    out[mask] = cv2.addWeighted(hm, 0.55, rgb, 0.45, 0)[mask]
    out[~mask] = (rgb * 0.55)[~mask].astype(np.uint8)
    return out


def to_photo(p, r, dx, dy):
    return [(p[0] - dx) / r, (p[1] - dy) / r, (p[2] - dx) / r, (p[3] - dy) / r]


def run(model, size, img):
    lb, r, dx, dy = letterbox(img, size)
    x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        obj, reg = model(x.cuda())
        b, s = decode(obj.float(), reg.float(), model.stride)
    return obj, reg, b[0].cpu().numpy(), float(s[0]), r, dx, dy, x.shape[-1]


def cell_boxes(reg, ref_box, r, dx, dy, stride, img_shape):
    """참조 상자(사진 좌표) 안 중심의 칸 회귀 상자들을 사진 좌표로."""
    H, W = img_shape
    out = []
    _, C, Hc, Wc = reg.shape
    for gy in range(Hc):
        for gx in range(Wc):
            cx, cy = (gx + 0.5) * stride, (gy + 0.5) * stride
            px, py = (cx - dx) / r, (cy - dy) / r
            if not (ref_box[0] <= px <= ref_box[2] and ref_box[1] <= py <= ref_box[3]):
                continue
            d = reg[0, :, gy, gx].cpu().numpy()
            out.append([px - d[0] / r, py - d[1] / r,
                        px + d[2] / r, py + d[3] / r])
    return out


def main():
    c = torch.load(CKPT, map_location="cpu", weights_only=False)
    model = BandNet(width=c["width"], stride=c.get("stride", 16)).cuda().eval()
    model.load_state_dict(c["model"])
    size = c["size"]
    lab = photo_index()

    tg = {}
    for ln in (HERE / "band_quads_pred_tg640w15_20261004.jsonl").read_text(
            encoding="utf-8").splitlines():
        if ln.strip():
            rr = json.loads(ln)
            q = rr["quad"]
            xs = [p[0] for p in q]
            ys = [p[1] for p in q]
            tg[rr["id"]] = (min(xs), min(ys), max(xs), max(ys), rr["score"])
    dev = {}
    for ln in (HERE / "device_labels.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            rr = json.loads(ln)
            dev[rr["id"]] = (rr.get("brand") or "?") + (
                " " + rr["model"] if rr.get("model") else "")
    gen1 = {json.loads(l)["id"]: json.loads(l)
            for l in (HERE / "_diag" / "e2e_bandnet" / "gen1.jsonl").read_text(
                encoding="utf-8").splitlines() if l.strip()}
    fails = {x["id"] for x in json.loads(
        (HERE / "_diag" / "fail19_raw_probe_gen1new.json").read_text(encoding="utf-8"))}

    rng = random.Random(20261004)
    canvas_rows = []
    for s in CASES:
        pid = "glucose_batch1/" + s
        img = cv2.imread(str(DATUMO / lab[pid]), cv2.IMREAD_GRAYSCALE)
        obj, reg, box, sc, r, dx, dy, _ = run(model, size, img)
        ov = heat_overlay(img, obj, r, dx, dy, size, model.stride)
        pb = to_photo(box, r, dx, dy)
        cv2.rectangle(ov, (int(pb[0]), int(pb[1])), (int(pb[2]), int(pb[3])),
                      (0, 140, 255), 3)
        # 정점 칸 십자
        heat = torch.sigmoid(obj)[0, 0]
        gy, gx = divmod(int(obj.view(-1).argmax()), obj.shape[-1])
        px, py = ((gx + .5) * model.stride - dx) / r, ((gy + .5) * model.stride - dy) / r
        cv2.drawMarker(ov, (int(px), int(py)), (255, 0, 0), cv2.MARKER_CROSS, 34, 3)
        # 숫자줄 칸 회귀(TG 참조 상자)
        ref = tg.get(pid)
        if ref:
            for cb in cell_boxes(reg, ref[:4], r, dx, dy, model.stride, img.shape):
                cv2.rectangle(ov, (int(cb[0]), int(cb[1])), (int(cb[2]), int(cb[3])),
                              (0, 255, 255), 1)
        sc_l = 330 / max(img.shape)
        ov = cv2.resize(ov, (int(img.shape[1] * sc_l), int(img.shape[0] * sc_l)),
                        interpolation=cv2.INTER_AREA)
        cap = f"FAIL {s} sc{sc:.2f} {dev.get(pid,'?')[:18]}"
        ov = cv2.copyMakeBorder(ov, 0, 24, 0, 0, cv2.BORDER_CONSTANT, value=(16, 16, 16))
        cv2.putText(ov, cap, (4, ov.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 140, 255), 1)
        # 히트맵 단독(오버레이와 동일 스케일) — 오버레이 재사용으로 대체 없이
        # 두 번째 칸은 같은 ov 를 십자만 강조해 재사용
        ov2 = ov.copy()
        cv2.putText(ov2, "peak cross", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1)
        # 같은 기종 성공
        pool = [i for i, v in gen1.items()
                if v["verdict"] == "right" and dev.get(i) == dev.get(pid)
                and i not in fails]
        suc = rng.choice(pool) if pool else None
        if suc:
            si = cv2.imread(str(DATUMO / lab[suc]), cv2.IMREAD_GRAYSCALE)
            o2, r2, b2, s2, rr_, dx2, dy2, _ = run(model, size, si)
            sov = heat_overlay(si, o2, rr_, dx2, dy2, size, model.stride)
            pb2 = to_photo(b2, rr_, dx2, dy2)
            cv2.rectangle(sov, (int(pb2[0]), int(pb2[1])), (int(pb2[2]), int(pb2[3])),
                          (0, 220, 0), 3)
            sc_l = 330 / max(si.shape)
            sov = cv2.resize(sov, (int(si.shape[1] * sc_l), int(si.shape[0] * sc_l)),
                             interpolation=cv2.INTER_AREA)
            sov = cv2.copyMakeBorder(sov, 0, 24, 0, 0, cv2.BORDER_CONSTANT,
                                     value=(16, 16, 16))
            cv2.putText(sov, f"OK {suc.split('/')[-1]} sc{s2:.2f}", (4, sov.shape[0] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 1)
        else:
            sov = np.full((CH2, 330, 3), 16, np.uint8)
        canvas_rows.append((ov, ov2, sov))

    PAD, CWMAX = 8, 560
    widths = [max(r0.shape[1] for r0, _, _ in canvas_rows) + PAD,
              max(r1.shape[1] for _, r1, _ in canvas_rows) + PAD,
              max(r2.shape[1] for _, _, r2 in canvas_rows) + PAD]
    Hh = PAD + len(canvas_rows) * (CH2 + 40 + PAD) + 30
    canvas = np.full((Hh, sum(widths) + PAD, 3), 24, np.uint8)
    cv2.putText(canvas, "orange=final box, red cross=peak cell, yellow thin=per-cell"
                " reg at digit row, heatmap=obj", (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)
    for ri, (a, b, cc) in enumerate(canvas_rows):
        y0 = 30 + PAD + ri * (CH2 + 40 + PAD)
        for ci, cell in enumerate((a, b, cc)):
            x0 = PAD + sum(widths[:ci])
            cell_r = cv2.resize(cell, (widths[ci] - PAD, CH2 + 24),
                                interpolation=cv2.INTER_AREA)
            canvas[y0:y0 + CH2 + 24, x0:x0 + widths[ci] - PAD] = cell_r
    out = HERE / "_diag" / "gen1_heatmap_sheet.png"
    cv2.imwrite(str(out), canvas)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
