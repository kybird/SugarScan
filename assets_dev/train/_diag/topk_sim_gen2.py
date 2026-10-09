# topk 디코드 시뮬레이션 — gen2_v1_step8000 + e2e 판독률까지 (2026-10-09).
# 규칙은 2026-10-04 사전 선언 그대로(데이터 맞춤 없음):
#   후보 = obj 상위 32칸 · 사전 = 2%<=면적비<=60% · 화면 안 90% 이상
#   통과자 중 최고 obj · 통과자 없으면 현행(전역 정점)과 동일 · 게이트 0.25/2%
# 확장: 검출실패 수만이 아니라 (a) 상자 달라진 장 수(IoU<0.9) (b) 리더 25k
# 를 얹은 e2e 판독률 변화 — 채택 판정은 이 셋이 함께 결정한다
# ([[decode-change-needs-full-corpus-simulation]]).
# 배포 검출기가 gen2_v1_step8000 이므로 이 결과가 채택 근거가 된다.
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from band_net import BandNet  # noqa: E402
from predict_band_quads import DATUMO, photo_index  # noqa: E402
from reader_crnn import CRNN, IN_H, IN_W, NUM_CLASSES, decode_greedy  # noqa: E402
from train_band import letterbox  # noqa: E402

DET = HERE / "band_out" / "tone" / "gen2_v1_step8000"
RDR = HERE / "reader_out" / "gen2lad25000_s8k" / "best.pt"
K = 32
FRAC_LO, FRAC_HI = 0.02, 0.60
INFRAME = 0.90
CONF = 0.25
ROTATED_90 = {"1213", "1226", "1564", "1565", "940", "283", "2411"}


def pick(o_sig, reg, r, dx, dy, stride, W, H):
    flat = o_sig.reshape(-1)
    order = np.argsort(flat)[::-1]
    cells = [(int(i // o_sig.shape[1]), int(i % o_sig.shape[1]))
             for i in order[:K]]
    cands = []
    for (gy, gx) in cells:
        cx, cy = (gx + 0.5) * stride, (gy + 0.5) * stride
        d = reg[0, :, gy, gx].cpu().numpy()
        cands.append(([cx - d[0], cy - d[1], cx + d[2], cy + d[3]],
                      float(o_sig[gy, gx])))
    base = cands[0]
    base_p = [(base[0][0] - dx) / r, (base[0][1] - dy) / r,
              (base[0][2] - dx) / r, (base[0][3] - dy) / r]
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
        if FRAC_LO <= frac <= FRAC_HI and (ix * iy) / (bw * bh) >= INFRAME:
            if best is None or sc > best[1]:
                best = (p, sc)
    return base_p, base[1], (best[0] if best else base_p), (best[1] if best else base[1])


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    c = torch.load(DET, map_location="cpu", weights_only=False)
    det = BandNet(width=c["width"], stride=c.get("stride", 16)).to(dev).eval()
    det.load_state_dict(c["model"])
    size = c["size"]
    cr = torch.load(RDR, map_location="cpu", weights_only=False)
    reader = CRNN(NUM_CLASSES).to(dev).eval()
    reader.load_state_dict(cr["model"])

    gts = {}
    for line in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            gts[j["id"]] = (j.get("image"), str(j.get("reading", "")))

    def e2e(img, p, sc):
        frac = (p[2] - p[0]) * (p[3] - p[1]) / max(1.0, img.shape[1] * img.shape[0])
        if sc < CONF or frac < FRAC_LO:
            return "det", None
        x0, y0 = max(0, int(p[0])), max(0, int(p[1]))
        x1 = min(img.shape[1], int(round(p[2])))
        y1 = min(img.shape[0], int(round(p[3])))
        if x1 - x0 < 4 or y1 - y0 < 4:
            return "det", None
        crop = cv2.resize(img[y0:y1, x0:x1], (IN_W, IN_H))
        t = torch.from_numpy(crop).float().div_(255.).sub_(0.5).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            logits = reader(t.to(dev))
        pred = decode_greedy(logits[0].cpu().unsqueeze(0))[0]
        if not pred:
            return "blank", None
        return ("right" if pred == gt_val else "wrong"), pred

    rows = []
    agg = {"base": {"right": 0, "wrong": 0, "blank": 0, "det": 0},
           "topk": {"right": 0, "wrong": 0, "blank": 0, "det": 0}}
    changed = 0
    n = 0
    for pid in sorted(gts):
        if pid.split("/", 1)[-1] in ROTATED_90:
            continue
        img_path, reading = gts[pid]
        if not reading.lstrip("-").isdigit():
            continue
        gt_val = str(int(reading))
        img = cv2.imread(str(DATUMO / img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        n += 1
        H, W = img.shape
        lb, r, dx, dy = letterbox(img, size)
        x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            obj, reg = det(x.to(dev))
        o_sig = torch.sigmoid(obj)[0, 0].cpu().numpy()
        bp, bs, tp, ts = pick(o_sig, reg, r, dx, dy, det.stride, W, H)
        bv, bpred = e2e(img, bp, bs)
        tv, tpred = e2e(img, tp, ts)
        agg["base"][bv] += 1
        agg["topk"][tv] += 1
        ix = max(0, min(bp[2], tp[2]) - max(bp[0], tp[0]))
        iy = max(0, min(bp[3], tp[3]) - max(bp[1], tp[1]))
        inter = ix * iy
        ua = ((bp[2] - bp[0]) * (bp[3] - bp[1])
              + (tp[2] - tp[0]) * (tp[3] - tp[1]) - inter)
        iou_bt = inter / ua if ua > 0 else 0.0
        changed += iou_bt < 0.9
        if bv != tv or iou_bt < 0.9:
            rows.append(dict(id=pid, base=[round(float(v), 1) for v in bp] + [round(float(bs), 3)],
                             base_v=bv, topk=[round(float(v), 1) for v in tp] + [round(float(ts), 3)],
                             topk_v=tv, gt=gt_val, iou=round(iou_bt, 3)))
        if n % 500 == 0:
            print(f"  {n}장 · base {agg['base']} · topk {agg['topk']}", flush=True)
    for k in agg:
        s = agg[k]
        m = s["right"] + s["wrong"] + s["blank"]
        print(f"[{k}] 채점 {m} · 정답 {s['right']} ({100*s['right']/max(1,m):.2f}%)"
              f" · 오독 {s['wrong']} · 빈 {s['blank']} · det {s['det']}")
    print(f"상자 달라짐(IoU<0.9): {changed}장 · 판정/상자 변경 {len(rows)}장")
    for r0 in rows:
        print(f"  {r0['id'].split('/')[-1]}: {r0['base_v']}->{r0['topk_v']}"
              f" (GT {r0['gt']})")
    out = HERE / "_diag" / "topk_sim_gen2.json"
    out.write_text(json.dumps(dict(n=int(n), agg=agg, changed=int(changed), rows=rows), default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o),
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
