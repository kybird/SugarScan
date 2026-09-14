# 밴드 쿼드 검출기 v0 게이트 평가 — 「합성만으로 밴드 쿼드 검출기 v0」 (2026-09-12).
#
# 사람이 그린 밴드 라벨(band_boxes.jsonl 97장, 읽기 전용 — 학습에 절대 안 쓴다)
# 에서 IoU 를 잰다. 이것이 카드 AC#7 게이트다: 중앙 0.7 이상 진행, 0.4~0.7 진행
# 하되 약점 명시, 0.4 미만 handoff.
#
# 비교 축(AC#4) — 같은 사진에서 세 제안자를 나란히:
#   det    본 검출기(합성만 학습). GM 크롭 -> 레터박스 256 -> 쿼드 회귀
#   gm     GM 박스 AABB 를 제안으로 쓴 것(폴백 하한)
#   cv     고전 CV 파인더(diag_cv_band.find_band, 운영점 pad .30/pad_x 1.00 +
#          grow .30/.10 — cv-band-viability 보고서의 운영점)
#
# 사용:
#   conda run -n sugartrain python eval_band_detector.py gate            # 84장 게이트
#   conda run -n sugartrain python eval_band_detector.py gate --all-proposals
#       # 게이트에 이어 전량 2,494장 제안(시간 몇 분) — AC#1
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch

from eval_reader import load_gray
from diag_cv_band import find_band, grow_box, DEFAULTS
from train_band_detector import BandQuadNet, letterbox, quad_to_target, IMG_SIZE

HERE = Path(__file__).resolve().parent

# GM 쿼드는 사람 라벨 우선이다(gm_quads.load_gm_quads, 2026-09-13).
# 구판은 검출기 출력(gmscreen_quads_oriented)만 봤고 그걸 실측이라
# 불렀다 — 사람이 그린 화면 상자 411행이 따로 있었는데 측정 경로
# 어디도 쓰지 않았다.
from gm_quads import quad_rows  # noqa: E402
UPSTREAM = HERE.parent / "upstream" / "datumo"
QUADS_ORIENTED = HERE / "gmscreen_quads_oriented.jsonl"   # 읽기 전용
BAND_BOXES = HERE / "band_boxes.jsonl"                    # 읽기 전용(게이트)
DEVICE_LABELS = HERE / "device_labels.jsonl"
CKPT = HERE / "band_det_v0.pt"


def _load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def _rect_of(quad):
    q = np.asarray(quad, np.float64)
    return q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()


def poly_iou(q1, q2):
    """볼록 다각형 IoU(축정렬 박스도 그대로 통과). q: 4x2 float32."""
    a = np.asarray(q1, np.float32).reshape(-1, 1, 2)
    b = np.asarray(q2, np.float32).reshape(-1, 1, 2)
    ret, inter = cv2.intersectConvexConvex(a, b)
    if not ret or inter.size == 0:
        return 0.0
    ia = cv2.contourArea(inter)
    ua = cv2.contourArea(np.asarray(q1, np.float32)) + \
        cv2.contourArea(np.asarray(q2, np.float32)) - ia
    return float(ia / ua) if ua > 0 else 0.0


def det_predict(model, gray, dev):
    x, sc, px, py = letterbox(gray)
    xt = torch.from_numpy(x)[None, None].to(dev)
    with torch.no_grad():
        y = model(xt)[0].cpu().numpy().reshape(4, 2)
    q = y * IMG_SIZE - np.array([px, py])
    q = q / sc                                   # 크롭 픽셀 좌표로 역변환
    return q.astype(np.float32)


def slope_deg(q):
    """쿼드 상단 변의 기울기(도). 축 정렬이면 0."""
    top = q[1] - q[0]
    return float(np.degrees(np.arctan2(top[1], top[0])))


def crop_photo(img, g):
    x0, y0, x1, y1 = g
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(img.shape[1], int(x1)), min(img.shape[0], int(y1))
    if x1 - x0 < 16 or y1 - y0 < 16:
        return None
    return img[y0:y1, x0:x1], x0, y0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gate"])
    ap.add_argument("--ckpt", default=str(CKPT))
    ap.add_argument("--all-proposals", action="store_true",
                    help="게이트 통과 후 전량 제안(AC#1) — 결과는 _diag 로")
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = BandQuadNet().to(dev)
    model.load_state_dict(torch.load(args.ckpt, map_location=dev))
    model.eval()

    quads = {r["id"]: r for r in quad_rows()}
    bands = _load_jsonl(BAND_BOXES)
    devices = {r["id"]: r for r in _load_jsonl(DEVICE_LABELS)}

    per_id = {}
    for b in bands:
        pid = b["id"]
        g = quads.get(pid)
        if g is None:
            continue
        rel = UPSTREAM / "extracted" / "TILDE" / (pid + ".jpg")
        if not rel.exists():
            continue
        img = load_gray(rel)
        if img is None:
            continue
        gq = np.asarray(g["quad"], np.float32)
        gx0, gy0, gx1, gy1 = _rect_of(gq)
        cr = crop_photo(img, (gx0, gy0, gx1, gy1))
        if cr is None:
            continue
        crop, cx0, cy0 = cr

        # 1) 검출기 제안
        q_crop = det_predict(model, crop, dev)
        q_photo = q_crop + np.array([cx0, cy0], np.float32)

        # 2) GM AABB 제안
        gm_rect = np.array([[gx0, gy0], [gx1, gy0], [gx1, gy1], [gx0, gy1]],
                           np.float32)

        # 3) 고전 CV 제안 — 운영점 그대로
        cv_rect = crop_photo(img, (
            gx0 - (gx1 - gx0) * 1.00, gy0 - (gy1 - gy0) * 0.30,
            gx1 + (gx1 - gx0) * 1.00, gy1 + (gy1 - gy0) * 0.30))
        cv_q_photo = None
        if cv_rect is not None:
            cc, ccx, ccy = cv_rect
            fb = find_band(cc, None)
            if fb is not None:
                bx = grow_box(fb[0], DEFAULTS)
                cv_q_photo = np.float32([
                    [ccx + bx[0], ccy + bx[1]], [ccx + bx[2], ccy + bx[1]],
                    [ccx + bx[2], ccy + bx[3]], [ccx + bx[0], ccy + bx[3]]])

        hq = np.asarray(b["quad"], np.float32)
        per_id[pid] = dict(
            iou_det=poly_iou(q_photo, hq),
            iou_gm=poly_iou(gm_rect, hq),
            iou_cv=poly_iou(cv_q_photo, hq) if cv_q_photo is not None else None,
            slope=slope_deg(q_photo),
            device=(lambda d: (d["brand"] + " " + d["model"]).strip()
                    if d and d.get("status") == "identified" else "(미식별)")(
                devices.get(pid)),
        )

    ious = np.asarray([v["iou_det"] for v in per_id.values()])
    gms = np.asarray([v["iou_gm"] for v in per_id.values()])
    cvs = np.asarray([v["iou_cv"] for v in per_id.values()
                      if v["iou_cv"] is not None])
    print(f"== 게이트: 사람 밴드 라벨 join {len(ious)}장 ==")
    print(f"det  IoU median={np.median(ious):.3f} p10={np.percentile(ious, 10):.3f} "
          f"p25={np.percentile(ious, 25):.3f} p75={np.percentile(ious, 75):.3f} "
          f"p90={np.percentile(ious, 90):.3f}")
    print(f"gm   IoU median={np.median(gms):.3f}   (GM 박스 그대로 — 폴백 하한)")
    print(f"cv   IoU median={np.median(cvs):.3f} n={len(cvs)}  "
          f"(고전 CV 파인더 운영점)")
    slopes = np.abs([v["slope"] for v in per_id.values()])
    print(f"제안 쿼드 기울기 |deg| >=1: {(slopes >= 1).mean() * 100:.1f}%  "
          f">=0.5: {(slopes >= 0.5).mean() * 100:.1f}%  (축정렬 퇴화 검사, AC#2)")

    by_dev = defaultdict(list)
    for v in per_id.values():
        by_dev[v["device"]].append(v["iou_det"])
    print("-- 기기별 det IoU (n>=3, 오름차순 — AC#3) --")
    for name, vals in sorted(by_dev.items(), key=lambda kv: np.median(kv[1])):
        if len(vals) >= 3:
            print(f"  {name:30s} n={len(vals):3d}  median={np.median(vals):.3f} "
                  f"min={min(vals):.3f}")

    out = HERE / "_diag" / "band_det_v0"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "gate_results.jsonl", "w", encoding="utf-8") as f:
        for pid, v in per_id.items():
            f.write(json.dumps(dict(id=pid, **v), ensure_ascii=False) + "\n")

    # 눈검증 시트 — 최저 6장 + 중앙 근처 3장
    order = sorted(per_id, key=lambda k: per_id[k]["iou_det"])
    picks = order[:6] + order[len(order) // 2 - 1:len(order) // 2 + 2]
    tiles = []
    for pid in picks:
        img = load_gray(UPSTREAM / "extracted" / "TILDE" / (pid + ".jpg"))
        q = np.asarray(per_id[pid] and quads[pid]["quad"], np.float32)
        gx0, gy0, gx1, gy1 = _rect_of(q)
        crop, cx0, cy0 = crop_photo(img, (gx0, gy0, gx1, gy1))
        vis = cv2.cvtColor(cv2.resize(crop, (200, int(crop.shape[0] * 200 /
                                                       crop.shape[1]))),
                           cv2.COLOR_GRAY2BGR)
        pred = det_predict(model, crop, dev) * np.array(
            [vis.shape[1] / crop.shape[1], vis.shape[0] / crop.shape[0]],
            np.float32)
        hu = np.asarray(next(b for b in bands if b["id"] == pid)["quad"]) \
            - [cx0, cy0]
        hu = hu * np.array([vis.shape[1] / crop.shape[1],
                            vis.shape[0] / crop.shape[0]], np.float32)
        cv2.polylines(vis, [pred.reshape(-1, 1, 2).astype(np.int32)], True,
                      (0, 0, 255), 2)
        cv2.polylines(vis, [hu.reshape(-1, 1, 2).astype(np.int32)], True,
                      (0, 255, 0), 1)
        vis = cv2.copyMakeBorder(vis, 15, 2, 2, 2, cv2.BORDER_CONSTANT,
                                 value=(0, 0, 0))
        cv2.putText(vis, f"{pid.split('/')[-1]} {per_id[pid]['iou_det']:.2f}",
                    (3, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        tiles.append(vis)
    H = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 0,
                                cv2.BORDER_CONSTANT, value=(40, 40, 40))
             for t in tiles]
    while len(tiles) % 3:
        tiles.append(np.full_like(tiles[0], 40))
    rows = [np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
    wmax = max(r.shape[1] for r in rows)
    rows = [cv2.copyMakeBorder(r, 0, 0, 0, wmax - r.shape[1],
                               cv2.BORDER_CONSTANT, value=(40, 40, 40))
            for r in rows]
    cv2.imwrite(str(out / "gate_worst.png"), np.vstack(rows))
    print(f"눈검증 시트(최저 6 + 중앙 3, 빨강=제안 초록=사람): "
          f"{out / 'gate_worst.png'}")

    if args.all_proposals:
        outj = open(out / "band_proposals_all.jsonl", "w", encoding="utf-8")
        n_ok = 0
        all_ids = sorted(quads)
        for k, pid in enumerate(all_ids):
            rel = UPSTREAM / "extracted" / "TILDE" / (pid + ".jpg")
            img = load_gray(rel) if rel.exists() else None
            if img is None:
                continue
            gq = np.asarray(quads[pid]["quad"], np.float32)
            cr = crop_photo(img, _rect_of(gq))
            if cr is None:
                continue
            crop, cx0, cy0 = cr
            q_photo = det_predict(model, crop, dev) + np.array([cx0, cy0],
                                                               np.float32)
            outj.write(json.dumps(dict(id=pid, quad=np.round(q_photo, 1)
                                       .tolist(), by="det_v0",
                                       slope=slope_deg(q_photo))) + "\n")
            n_ok += 1
            if (k + 1) % 500 == 0:
                print(f"  proposals {k + 1}/{len(all_ids)}", flush=True)
        outj.close()
        print(f"전량 제안 {n_ok}/{len(all_ids)} -> {out / 'band_proposals_all.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
