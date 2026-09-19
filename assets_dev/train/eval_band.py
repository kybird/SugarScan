# 밴드 검출망 평가 — **합성 게이트**(SPEC 4: 합성을 먼저 넘고 그 다음 실촬).
#
# 게이트 지표는 IoU 가 아니다(SPEC 7-3). IoU 는 양방향으로 틀린다 — 상자가 커서
# 낮은 장은 리더에 무해하고, IoU 가 높은데 숫자를 자르는 장이 있다.
#
# 합성에는 진짜 정답이 있다: 매니페스트의 `digit_box`(숫자 필드의 축정렬 상자,
# 이미지 좌표, SPEC 9.5). 그래서 **숫자가 예측 상자에 온전히 들어오는가**를
# 직접 셀 수 있다.
#
#   합격 = 검출됐고 **digit_box 가 예측 상자 안에 100% 든다**
#   검출 실패는 불합격. 분모는 전체 장이다.
#
# 그리고 **평균으로 판정하지 않는다** — 프로파일별 최저값을 함께 낸다.
# (docs/OCR_REBUILD_PLAN.md 3 에서 살아남은 원칙: 평균은 못하는 기기를 숨긴다)
import argparse
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch

from band_net import BandNet, decode
from train_band import letterbox

WIDE_PROFILES = {"onetouch_ultramini", "wide_unknown"}


def load(ckpt, dev):
    c = torch.load(ckpt, map_location="cpu", weights_only=False)
    m = BandNet(width=c["width"]).to(dev).eval()
    m.load_state_dict(c["model"])
    return m, c


def contains(outer, inner, eps=0.5):
    """inner 가 outer 안에 온전히 드는가. eps 는 픽셀 반올림 여유."""
    return (inner[0] >= outer[0] - eps and inner[1] >= outer[1] - eps
            and inner[2] <= outer[2] + eps and inner[3] <= outer[3] + eps)


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    i = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / u if u > 0 else 0.0


@torch.no_grad()
def evaluate(ckpt, root, ann, manifest, conf=0.25, batch=32, out=None):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model, meta = load(ckpt, dev)
    size = meta["size"]
    root = Path(root)
    j = json.loads((root / "annotations" / ann).read_text(encoding="utf-8"))
    split = "val2017" if "val" in ann else "train2017"
    by = {a["image_id"]: a["bbox"] for a in j["annotations"]}
    man = {}
    for line in Path(manifest).read_text(encoding="utf-8").splitlines():
        if line.strip():
            m = json.loads(line)
            man[m["id"] + ".png"] = m

    items = []
    for im in j["images"]:
        b = by.get(im["id"])
        if b is None:
            continue
        items.append((im["file_name"], [b[0], b[1], b[0]+b[2], b[1]+b[3]]))

    rows = []
    for s in range(0, len(items), batch):
        chunk = items[s:s+batch]
        xs, metas = [], []
        for fn, gt in chunk:
            img = cv2.imread(str(root / split / fn), cv2.IMREAD_GRAYSCALE)
            lb, r, dx, dy = letterbox(img, size)
            xs.append(torch.from_numpy(lb).float().div_(255.).unsqueeze(0))
            metas.append((fn, gt, r, dx, dy))
        x = torch.stack(xs).to(dev)
        obj, reg = model(x)
        boxes, scores = decode(obj.float(), reg.float(), model.stride)
        boxes = boxes.cpu().numpy()
        scores = scores.cpu().numpy()
        for (fn, gt, r, dx, dy), bx, sc in zip(metas, boxes, scores):
            # 레터박스 좌표 -> 원본 이미지 좌표
            p = [(bx[0]-dx)/r, (bx[1]-dy)/r, (bx[2]-dx)/r, (bx[3]-dy)/r]
            mm = man.get(fn, {})
            db = mm.get("digit_box")
            det = bool(sc >= conf)
            rows.append({
                "file_name": fn, "profile": mm.get("profile", "?"),
                "score": float(sc), "pred": [round(v, 1) for v in p],
                "gt": gt, "iou": round(iou(p, gt), 4) if det else 0.0,
                "det": det,
                "pass": bool(det and db is not None and contains(p, db)),
                "digit_box": db,
                # 밴드가 프레임에서 차지하는 **선형** 비. 촬영 배율의 자다
                # (CAM_ZOOM_RANGE 가 만드는 다양성이 그대로 여기에 나온다).
                # 과대 상자 제한용. **포함률만 최적화하면 이미지 전체를
                # 내는 퇴화해가 통과한다**(2026-09-18 자문 지적). 정답 밴드
                # 넓이에 대한 예측 넓이의 비를 함께 적어 τ 곡선을 낸다.
                # τ 확정은 후속 숫자 인식기의 입력 규격이 정해진 뒤다 —
                # 인식기가 아직 없으므로 여기서는 **곡선으로만** 보고한다.
                "area_ratio": float(((p[2]-p[0]) * (p[3]-p[1]))
                                    / max(1.0, (gt[2]-gt[0]) * (gt[3]-gt[1]))),
                "frac": float(np.sqrt(max(0.0, (gt[2]-gt[0]) * (gt[3]-gt[1]))
                                      / max(1.0, mm.get("w", 1) * mm.get("h", 1)))),
            })

    n = len(rows)
    miss = sum(1 for r in rows if not r["det"])
    ok = sum(1 for r in rows if r["pass"])
    wide = [r for r in rows if r["profile"] in WIDE_PROFILES]
    tall = [r for r in rows if r["profile"] not in WIDE_PROFILES]
    print(f"체크포인트 {Path(ckpt).name} · 학습장수 {meta['n_images']} · "
          f"{meta['param']/1e6:.3f}M · 스텝 {meta['steps']}")
    print(f"  모집단 {root.name}/{ann}  n={n}  conf>={conf}")
    print(f"  검출 실패 {miss}  ·  **합격률 {100*ok/n:.2f}%** "
          f"(숫자 필드가 예측 상자에 100% 듦)")
    for name, sel in (("세로형", tall), ("가로형", wide)):
        if not sel:
            continue
        m2 = sum(1 for r in sel if not r["det"])
        o2 = sum(1 for r in sel if r["pass"])
        v = np.array([r["iou"] for r in sel if r["det"]])
        print(f"    {name} n={len(sel)} 실패 {m2} 합격 {100*o2/len(sel):.2f}% "
              f"· IoU 중앙 {np.median(v) if len(v) else 0:.4f}")
    agg = defaultdict(list)
    for r in rows:
        agg[r["profile"]].append(r)
    worst = sorted(((sum(1 for r in v if r["pass"])/len(v), k, len(v))
                    for k, v in agg.items()))
    # τ 게이트 곡선 — 포함률 ∧ 면적비<=τ
    ar = np.array([r["area_ratio"] for r in rows])
    ps = np.array([r["pass"] for r in rows])
    print("  τ 게이트 (숫자 100% 포함 **그리고** 예측넓이/정답넓이 <= τ)")
    print(f"    면적비 분포  p50={np.median(ar):.2f} p90={np.percentile(ar,90):.2f} "
          f"p99={np.percentile(ar,99):.2f} max={ar.max():.2f}")
    cells = "  ".join(f"τ={t:<4.1f} {100*(ps & (ar <= t)).mean():6.2f}%"
                      for t in (1.2, 1.5, 2.0, 3.0, 5.0))
    print(f"    {cells}")
    print("    **τ 확정은 숫자 인식기의 입력 규격이 나온 뒤다 — 곡선만 낸다.**")
    print("  프로파일별 합격률 (낮은 순 5) — **평균으로 판정하지 않는다**")
    for rate, k, cnt in worst[:5]:
        print(f"    {k:<24} {100*rate:6.2f}%  (n={cnt})")
    # **배율로 층을 가른다** — 실촬에서 촬영 거리가 성적을 강하게 물었다
    # (2026-09-18, Datacluster 전체사진: 가까움 23.1% / 멂 1.3%). 합성에서도
    # 작은 밴드가 약하면 원인은 도메인이 아니라 **모델 구조**(stride 16 단일
    # 특징맵, stride-8 없음) 쪽이다. 여기서 평평하면 구조는 혐의를 벗는다.
    fr = np.array([r["frac"] for r in rows])
    q1, q2 = np.percentile(fr, [33.3, 66.7])
    ps = np.array([r["pass"] for r in rows])
    ds = np.array([r["det"] for r in rows])
    print("  배율별 합격률 (밴드가 프레임에서 차지하는 선형 비)")
    for lbl, m in (("큼  ", fr >= q2), ("중간", (fr >= q1) & (fr < q2)),
                   ("작음", fr < q1)):
        if not m.any():
            continue
        print(f"    {lbl} {fr[m].min():.3f}~{fr[m].max():.3f} "
              f"n={int(m.sum()):<4} 합격 {100*ps[m].mean():6.2f}% "
              f"· 검출실패 {int((~ds[m]).sum())}")
    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  -> {p}")
    return {"n": n, "miss": miss, "pass_rate": ok / n,
            "worst_profile": worst[0][0] if worst else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--ann", default="instances_val2017.json")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    evaluate(a.ckpt, a.data, a.ann, a.manifest, a.conf, out=a.out)


if __name__ == "__main__":
    main()
