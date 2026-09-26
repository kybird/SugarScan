# 리더 자릿수 누락 원인 분리 — 박스 문제인가 인식 문제인가(2026-09-26,
# 사람 지시: "검출기의 결과가 잘못됐을 수도 있다"). GPU 를 쓰지 않는다 —
# 이미 구운 C2 패널·박스만 분석한다.
#
# 방법: C2 의 GT 상자(정답 밴드) vs 검출 예측 상자(C2_boxes_panel) 를 비교해
#   (1) 예측 박스가 GT 대비 좌/우로 얼마나 잘랐는가(끝자리 숫자 잘림)
#   (2) IoU·포함률 분포 — 오독 장 vs 정답 장
#   (3) 자릿수 누락 오독(104→10 등) 장의 박스 폭 비 GT/예측
# 를 집계한다. 판독 재현이 필요한 장은 크롭+예측 상자 오버레이 시트를 남긴다.
#
# 사용: python diag_digit_loss_boxes.py
import json

import cv2
import numpy as np

HERE = __import__("pathlib").Path(__file__).resolve().parent
C2 = HERE / "synth_coco" / "C2"
PRED = HERE / "_diag" / "bandft" / "C2_boxes_panel.jsonl"
MANIFEST = C2 / "manifest.jsonl"
OUT = HERE / "_diag" / "reader_digit_loss"


def rect_of(quad):
    q = np.asarray(quad, float)
    return [q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()]


def main() -> int:
    gt = {}
    coco = json.loads((C2 / "annotations" / "instances_train2017.json")
                      .read_text(encoding="utf-8"))
    ims = {im["id"]: im for im in coco["images"]}
    for a in coco["annotations"]:
        im = ims[a["image_id"]]
        x, y, w, h = a["bbox"]
        gt[im["file_name"]] = [x, y, x + w, y + h]
    labels = {}
    for l in MANIFEST.read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labels[j["id"] + ".png"] = j["label"]
    pred = {}
    for l in PRED.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            pred[r["file_name"]] = r["pred"]

    rows = []
    for fn, g in gt.items():
        p = pred.get(fn)
        if p is None:
            continue
        gx0, gy0, gx1, gy1 = g
        px0, py0, px1, py1 = p
        inter = (min(gx1, px1) - max(gx0, px0)) * (min(gy1, py1)
                                                   - max(gy0, py0))
        union = ((gx1-gx0)*(gy1-gy0) + (px1-px0)*(py1-py0) - inter)
        iou = inter/union if union > 0 else 0
        cover = inter / max(1e-6, (gx1-gx0)*(gy1-gy0))
        rows.append({"file": fn, "label": labels.get(fn, "?"),
                     "iou": iou, "cover": cover,
                     "left_cut": px0 - gx0,     # 양수=예측이 오른쪽으로 시작(왼쪽 잘림)
                     "right_cut": gx1 - px1,    # 양수=예측이 먼저 끝남(오른쪽 잘림)
                     "w_ratio": (px1-px0)/max(1e-6, gx1-gx0)})
    (OUT).mkdir(parents=True, exist_ok=True)
    (OUT / "rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")

    ok = [r for r in rows]  # 전부 수집(판독 성공 여부는 리더 로그와 매칭 못 하므로 분포로 본다)
    iou = np.asarray([r["iou"] for r in ok])
    cov = np.asarray([r["cover"] for r in ok])
    lc = np.asarray([r["left_cut"] for r in ok])
    rc = np.asarray([r["right_cut"] for r in ok])
    print(f"n={len(rows)}")
    print(f"IoU 중앙 {np.median(iou):.3f} · p10 {np.percentile(iou,10):.3f} · <0.5 {int((iou<0.5).sum())}장")
    print(f"GT 포함률 중앙 {np.median(cov):.3f} — 예측 박스가 GT 밴드를 덮는 비율")
    print(f"왼쪽 절단(예측 시작이 GT보다 안쪽): 중앙 {np.median(lc):+.1f}px · "
          f"절단>10px {int((lc>10).sum())}장 · >25px {int((lc>25).sum())}장")
    print(f"오른쪽 절단: 중앙 {np.median(rc):+.1f}px · >10px {int((rc>10).sum())}장 · "
          f">25px {int((rc>25).sum())}장")
    # 자릿수 누락 위험: 밴드 폭이 GT 보다 눈에 띄게 작은 장
    wr = np.asarray([r["w_ratio"] for r in ok])
    print(f"박스 폭비(예측/GT): 중앙 {np.median(wr):.3f} · <0.85 {int((wr<0.85).sum())}장 · "
          f"<0.7 {int((wr<0.7).sum())}장")
    worst = sorted(rows, key=lambda r: r["w_ratio"])[:15]
    print("폭비 최악 15장(잠재 자릿수 잘림):")
    for r in worst:
        print(f"  {r['file']}  라벨 {r['label']:>4}  폭비 {r['w_ratio']:.2f} "
              f" 좌절단 {r['left_cut']:+.0f} 우절단 {r['right_cut']:+.0f} IoU {r['iou']:.2f}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
