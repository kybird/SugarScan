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
from train_band_detector import (BandQuadNet, load_detector, letterbox,
                                 quad_to_target, IMG_SIZE)

HERE = Path(__file__).resolve().parent

# GM 쿼드는 사람 라벨 우선이다(gm_quads.load_gm_quads, 2026-09-13).
# 구판은 검출기 출력(gmscreen_quads_oriented)만 봤고 그걸 실측이라
# 불렀다 — 사람이 그린 화면 상자 411행이 따로 있었는데 측정 경로
# 어디도 쓰지 않았다.
from gm_quads import quad_rows  # noqa: E402
from band_exclusions import drop  # noqa: E402
UPSTREAM = HERE.parent / "upstream" / "datumo"
QUADS_ORIENTED = HERE / "gmscreen_quads_oriented.jsonl"   # 읽기 전용
BAND_BOXES = HERE / "band_boxes.jsonl"                    # 읽기 전용(게이트)
DEVICE_LABELS = HERE / "device_labels.jsonl"
CKPT = HERE / "band_det_v0.pt"


# 가로형 기기 — **선언**이다(사람 기기 라벨의 이름). 측정한 종횡비로 가르지
# 않는다: 게이트 271장에서 유리 종횡비 1.0~1.5 구간에 GluNEO plus·OneTouch
# Ultra 같은 **세로형 선언 기기**가 섞여 있고, 1.5 위에는 아래 둘만 있다.
WIDE_DEVICES = ("OneTouch UltraMini", "이름모를 가로형모델")


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


# ── 포함 기준 — 이 게이트의 정본 (2026-09-15) ────────────────────────────
# 사람 지침: "게이트는 숫자를 전부 포함 여부이다. 노이즈가 끼든 안 끼든 일단
# 숫자는 다 포함해야 할 것 아니냐. 넉넉하게 포함하든 타이트하게 포함하든
# 잘리지는 말아야지."
#
# IoU 를 정본으로 쓰면 안 되는 이유는 **자에 천장이 있어서**다. 사람 라벨은
# 축정렬 직사각형이고 예측은 기울어진 쿼드라, 완벽히 맞춰도 IoU 가 1 이 되지
# 않는다. 기울기 t, 종횡비 r 일 때 천장은
#     IoU_max = r / ((cos t + r sin t)(r cos t + sin t))
# 4° 0.864 · 6° 0.809 · 8° 0.762 · 10° 0.715. 합성 기울기를 넓히면 검출이
# 좋아져도 이 숫자는 내려간다 — 목표와 반대로 움직이는 대리 지표다.
#
# 그래서 **1순위는 포함률**, 2순위는 넓이비(얼마나 넉넉한가), 진단은 변별
# 삐져나옴이다. IoU 는 옛 판과 잇대어 보라고 남기지만 합격을 정하지 않는다.
CONTAIN_PASS = 0.999   # 부동소수 오차만 봐준다. 한 획이라도 밖이면 불합격이다.


def contain_ratio(pred, label):
    """사람 라벨 중 예측 **안에** 든 넓이 비율. 1.0 이면 한 획도 안 잘렸다."""
    a = np.asarray(pred, np.float32).reshape(-1, 1, 2)
    b = np.asarray(label, np.float32).reshape(-1, 1, 2)
    ret, inter = cv2.intersectConvexConvex(a, b)
    lab = cv2.contourArea(np.asarray(label, np.float32))
    if lab <= 0:
        return 0.0
    if not ret or inter.size == 0:
        return 0.0
    return float(min(1.0, cv2.contourArea(inter) / lab))


def area_ratio(pred, label):
    """예측 넓이 / 라벨 넓이. 1 보다 크면 넉넉하게 감쌌다는 뜻.

    포함률만 보면 **사진 전체를 찍는 예측이 만점**이다. 이 값이 그걸 막는
    2순위 지표다 — 합격을 정하지 않고, 같은 포함률끼리 줄을 세운다."""
    lab = cv2.contourArea(np.asarray(label, np.float32))
    return float(cv2.contourArea(np.asarray(pred, np.float32)) / lab)         if lab > 0 else 0.0


def edge_shortfall(pred, label, n=64):
    """라벨의 네 변이 예측 밖으로 얼마나 삐져나왔는가 — 변별 최대 거리.

    위/아래는 라벨 **높이** 대비, 좌/우는 라벨 **폭** 대비로 정규화한다.
    사람이 처음 본 증상이 "좌우 위아래 상관없이 잘린다" 였다 — 어느 변이
    잘리는지는 합격/불합격보다 고치는 데 필요한 정보다.
    """
    lab = np.asarray(label, np.float64)
    x0, y0 = lab[:, 0].min(), lab[:, 1].min()
    x1, y1 = lab[:, 0].max(), lab[:, 1].max()
    w, h = max(1e-6, x1 - x0), max(1e-6, y1 - y0)
    poly = np.asarray(pred, np.float32).reshape(-1, 1, 2)
    t = np.linspace(0.0, 1.0, n)
    sides = {
        "top":    (np.stack([x0 + t * w, np.full(n, y0)], 1), h),
        "bottom": (np.stack([x0 + t * w, np.full(n, y1)], 1), h),
        "left":   (np.stack([np.full(n, x0), y0 + t * h], 1), w),
        "right":  (np.stack([np.full(n, x1), y0 + t * h], 1), w),
    }
    out = {}
    for name, (pts, unit) in sides.items():
        d = np.array([cv2.pointPolygonTest(poly, (float(px), float(py)), True)
                      for px, py in pts])
        # 음수 = 밖. 가장 깊이 나간 곳을 그 변의 삐져나옴으로 본다.
        out[name] = round(float(max(0.0, -d.min()) / unit), 4)
    return out


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
    ap.add_argument("--portrait-only", action="store_true",
                    help="가로형 기기를 게이트에서 뺀다(2026-09-16 사람 결정: "
                         "세로형부터 세운다). 학습에서도 빠져 있어야 한다"
                         "(synth_panel.EXCLUDE_WIDE) — 한쪽만 빼면 못 배운 "
                         "것을 채점한다. **표본이 줄므로 이전 판과 나란히 "
                         "놓고 우열을 말할 수 없다.**")
    ap.add_argument("--tag", default=None,
                    help="결과 디렉터리 이름. 기본은 체크포인트 파일명 어간 — "
                         "여러 체크포인트를 재면서 서로 덮어쓰지 않게 한다")
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model, _arch = load_detector(args.ckpt, dev)

    quads = {r["id"]: r for r in quad_rows()}
    bands = _load_jsonl(BAND_BOXES)
    # 사람이 '숫자칸이 프레임에 잘렸다'고 선언한 장은 뺀다(2026-09-14).
    # 분모가 바뀌므로 제외 전 수치와 나란히 인용하면 안 된다 — drop 이 인쇄한다.
    bands = drop(bands, where="gate")
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
            # 1순위 — 사람 라벨을 다 담았는가
            contain=contain_ratio(q_photo, hq),
            # 2순위 — 얼마나 넉넉히 담았는가(넓을수록 쓸모가 준다)
            area=area_ratio(q_photo, hq),
            edges=edge_shortfall(q_photo, hq),
            contain_gm=contain_ratio(gm_rect, hq),
            area_gm=area_ratio(gm_rect, hq),
            # IoU 는 옛 판과 잇대어 보기 위해 남긴다 — 합격을 정하지 않는다
            iou_det=poly_iou(q_photo, hq),
            iou_gm=poly_iou(gm_rect, hq),
            iou_cv=poly_iou(cv_q_photo, hq) if cv_q_photo is not None else None,
            slope=slope_deg(q_photo),
            device=(lambda d: (d["brand"] + " " + d["model"]).strip()
                    if d and d.get("status") == "identified" else "(미식별)")(
                devices.get(pid)),
        )

    if args.portrait_only:
        _w = {k: v for k, v in per_id.items() if v["device"] in WIDE_DEVICES}
        for k in _w:
            per_id.pop(k)
        print(f"[gate] 가로형 제외 {len(_w)}장 — 세로형만 채점한다"
              f"(사람 결정 2026-09-16). 남은 {len(per_id)}장.")
        print("       **표본이 달라졌다** — 가로형 포함 판의 수치와 나란히 "
              "놓고 우열을 말하지 않는다.")

    con = np.asarray([v["contain"] for v in per_id.values()])
    ar = np.asarray([v["area"] for v in per_id.values()])
    con_gm = np.asarray([v["contain_gm"] for v in per_id.values()])
    ious = np.asarray([v["iou_det"] for v in per_id.values()])
    gms = np.asarray([v["iou_gm"] for v in per_id.values()])
    cvs = np.asarray([v["iou_cv"] for v in per_id.values()
                      if v["iou_cv"] is not None])
    npass = int((con >= CONTAIN_PASS).sum())
    print(f"== 게이트: 사람 밴드 라벨 join {len(con)}장 ==")
    print("")
    print("[1순위] 포함 — 사람 라벨을 다 담았는가")
    print(f"  전부 담음   {npass}/{len(con)}  ({100 * npass / len(con):.1f}%)")
    print(f"  포함률      median={np.median(con):.4f} "
          f"p10={np.percentile(con, 10):.4f} min={con.min():.4f}")
    for thr in (0.999, 0.99, 0.95, 0.90):
        print(f"    >= {thr:<6} {int((con >= thr).sum()):4d}장 "
              f"({100 * (con >= thr).mean():.1f}%)")
    _ar_gm = np.asarray([v["area_gm"] for v in per_id.values()])
    print(f"  (참고) GM 박스 그대로: 포함률 median={np.median(con_gm):.4f} · "
          f"넓이비 median={np.median(_ar_gm):.1f}배 — **포함만 보면 만점인 자리**."
          )
    print(f"         화면 전체를 찍으면 늘 담는다. 그래서 2순위가 있다.")
    print("")
    print("[2순위] 넓이비 — 얼마나 넉넉히 담았는가(예측/라벨)")
    print(f"  median={np.median(ar):.2f} p10={np.percentile(ar, 10):.2f} "
          f"p90={np.percentile(ar, 90):.2f} max={ar.max():.2f}")
    _ok = con >= CONTAIN_PASS
    if _ok.any():
        print(f"  합격 장만: median={np.median(ar[_ok]):.2f} "
              f"p90={np.percentile(ar[_ok], 90):.2f}")
    print("")
    print("[진단] 어느 변이 잘리나 — 라벨이 예측 밖으로 나간 깊이(변 길이 대비)")
    for side in ("top", "bottom", "left", "right"):
        v = np.asarray([per_id[k]["edges"][side] for k in per_id])
        print(f"  {side:<7} 잘린 장 {int((v > 0).sum()):4d}  "
              f"median(잘린 것만)={np.median(v[v > 0]) if (v > 0).any() else 0:.3f}  "
              f"max={v.max():.3f}")
    print("")
    print("[참고] IoU — 옛 판과 잇대어 보는 용도. **합격을 정하지 않는다.**")
    print(f"  det median={np.median(ious):.3f} p10={np.percentile(ious, 10):.3f} "
          f"p90={np.percentile(ious, 90):.3f}   gm median={np.median(gms):.3f}"
          + (f"   cv median={np.median(cvs):.3f} n={len(cvs)}" if len(cvs) else ""))
    slopes = np.abs([v["slope"] for v in per_id.values()])
    print(f"  제안 쿼드 기울기 |deg| >=1: {(slopes >= 1).mean() * 100:.1f}%  "
          f">=0.5: {(slopes >= 0.5).mean() * 100:.1f}%  (축정렬 퇴화 검사, AC#2)")

    by_dev = defaultdict(list)
    for v in per_id.values():
        by_dev[v["device"]].append(v["contain"])
    print("")
    print("-- 기기별 포함률 (n>=3, 오름차순 — AC#3) --")
    for name, vals in sorted(by_dev.items(), key=lambda kv: np.median(kv[1])):
        if len(vals) >= 3:
            _p = sum(1 for x in vals if x >= CONTAIN_PASS)
            print(f"  {name:30s} n={len(vals):3d}  median={np.median(vals):.4f} "
                  f"min={min(vals):.4f}  전부담음 {_p}/{len(vals)}")

    out = HERE / "_diag" / (args.tag or Path(args.ckpt).stem)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "gate_results.jsonl", "w", encoding="utf-8") as f:
        for pid, v in per_id.items():
            f.write(json.dumps(dict(id=pid, **v), ensure_ascii=False) + "\n")

    # 눈검증 시트 — 최저 6장 + 중앙 근처 3장
    order = sorted(per_id, key=lambda k: per_id[k]["contain"])
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
