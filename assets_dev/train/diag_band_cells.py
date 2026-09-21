# 실패를 **선택 실패**와 **회귀 실패**로 가른다 (2026-09-18 외부 자문 §6.1).
#
# 왜 필요한가: 실촬에서 예측 상자가 기기 전체만 하게 나온다. 여기에는 서로
# 다른 두 원인이 겹칠 수 있다.
#
#   선택 실패  진짜 밴드 근처에 좋은 상자가 이미 있는데, 배경 칸의 objectness
#              가 더 높아서 그쪽이 뽑힌다. 양성으로 감독받지 않은 칸의 거리
#              회귀는 아무 값이나 낼 수 있으므로, 그 칸이 뽑히면 상자가 기기
#              전체보다 커도 이상하지 않다.
#   회귀 실패  정답 근처 칸을 골라 줘도 좋은 상자를 못 만든다.
#
# 처방이 정반대다. 선택 실패면 점수 감독(상자 품질을 점수에 반영)을 보고,
# 회귀 실패면 표현·입력 품질·좌표를 본다. **특징맵을 촘촘하게 하는 것
# (stride-8/FPN)은 회귀 실패가 확인된 뒤에나 후보다.**
#
# 재는 법: 체크포인트를 고정하고 한 장마다 26x26=676 칸 전부의 점수와 상자를
# 편다. 그리고 네 가지를 견준다.
#   sel        지금 방식 — 전역 objectness argmax
#   gt_top     정답 밴드의 **양성 영역**(학습과 같은 규칙: 중심 반경 ∩ GT 안)
#              안에서 점수가 가장 높은 칸
#   gt_best    같은 영역 안에서 **상자가 가장 좋은** 칸 (통과 우선, 면적비 최소)
#   topK       전역 점수 상위 K 안에 통과하는 상자가 있는가
#
# 좌표계: 전부 **레터박스 좌표**에서 잰다. 원본으로 되돌리면 비율 지표
# (포함률·면적비)는 어차피 같고, 되돌리는 과정에서 좌표계를 섞을 위험만
# 는다 ([[unnamed-coordinate-frame]]).
#
# 판정: 포함률 1.0 **그리고** 면적비 <= τ. 포함률만 쓰면 이미지 전체를 내는
# 퇴화해가 통과한다(같은 자문 §1). 실촬에는 digit_box 가 없어 사람이 그린
# **밴드 전체 포함**을 쓴다 — 숫자 포함보다 엄격하므로 그렇게 부르지 않는다.
#
# 사용:
#   python diag_band_cells.py --ckpt band_out/curve_07998.pt
#   python diag_band_cells.py --ckpt band_out/curve_07998.pt --tau 1.5 --limit 50
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import torch

from band_net import BandNet
from train_band import letterbox
from eval_band_real import population, DATUMO, OUT


def boxes_all(obj, reg, stride):
    """모든 칸의 점수와 상자를 편다. decode() 와 같은 기하, argmax 만 뺐다."""
    _, _, H, W = obj.shape
    score = torch.sigmoid(obj.view(-1)).cpu().numpy()
    gy, gx = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")
    cx = (gx.reshape(-1) + 0.5) * stride
    cy = (gy.reshape(-1) + 0.5) * stride
    r = reg.view(4, -1).cpu().numpy()
    box = np.stack([cx - r[0], cy - r[1], cx + r[2], cy + r[3]], 1)
    return score, box


def quality(box, gt):
    """(포함률, 면적비). 포함률은 정답 밴드가 예측에 드는 넓이 비."""
    x0 = np.maximum(box[:, 0], gt[0]); y0 = np.maximum(box[:, 1], gt[1])
    x1 = np.minimum(box[:, 2], gt[2]); y1 = np.minimum(box[:, 3], gt[3])
    inter = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
    ga = max(1e-6, (gt[2] - gt[0]) * (gt[3] - gt[1]))
    pa = np.clip(box[:, 2] - box[:, 0], 0, None) * \
        np.clip(box[:, 3] - box[:, 1], 0, None)
    return inter / ga, pa / ga


def pos_mask(gt, H, W, stride, radius=1.5):
    """학습과 **같은 규칙**의 양성 영역: 중심 반경 ∩ GT 안 (train_band.assign)."""
    gy, gx = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")
    cx = (gx.reshape(-1) + 0.5) * stride
    cy = (gy.reshape(-1) + 0.5) * stride
    mx, my = (gt[0] + gt[2]) / 2, (gt[1] + gt[3]) / 2
    near = (np.abs(cx - mx) <= radius * stride) & \
           (np.abs(cy - my) <= radius * stride)
    inside = (cx > gt[0]) & (cx < gt[2]) & (cy > gt[1]) & (cy < gt[3])
    m = near & inside
    if not m.any():                      # 상자가 작아 한 칸도 안 들면 최근접
        m[np.argmin((cx - mx) ** 2 + (cy - my) ** 2)] = True
    return m


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="band_out/curve_07998.pt")
    ap.add_argument("--tau", type=float, default=2.0,
                    help="면적비 상한. 통과 = 포함률 1.0 이고 면적비 <= τ")
    ap.add_argument("--topk", type=int, nargs="+", default=[1, 5, 20])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ck = Path(a.ckpt) if Path(a.ckpt).is_absolute() else Path(__file__).parent / a.ckpt
    c = torch.load(ck, map_location="cpu", weights_only=False)
    model = BandNet(width=c["width"], stride=c.get("stride", 16)).to(dev).eval()
    model.load_state_dict(c["model"])
    size, stride = c["size"], model.stride

    ids, band, lab, n_ex = population()
    if a.limit:
        ids = ids[:a.limit]

    rows = []
    for cid in ids:
        img = cv2.imread(str(DATUMO / lab[cid]), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        lb, r, dx, dy = letterbox(img, size)
        x = torch.from_numpy(lb).float().div_(255.).unsqueeze(0).unsqueeze(0)
        obj, reg = model(x.to(dev))
        H, W = obj.shape[-2:]
        score, box = boxes_all(obj.float(), reg.float()[0], stride)
        g = band[cid]
        gt = [g[0] * r + dx, g[1] * r + dy, g[2] * r + dx, g[3] * r + dy]
        con, ar = quality(box, gt)
        ok = (con >= 0.999) & (ar <= a.tau)

        m = pos_mask(gt, H, W, stride)
        sel = int(np.argmax(score))
        order = np.argsort(-score)
        idx_in = np.flatnonzero(m)
        gt_top = int(idx_in[np.argmax(score[idx_in])])
        # 영역 안에서 가장 좋은 상자: 통과하는 것 우선, 그중 면적비 최소
        cand = idx_in[ok[idx_in]]
        gt_best = int(cand[np.argmin(ar[cand])]) if cand.size else \
            int(idx_in[np.argmax(con[idx_in] - 0.001 * ar[idx_in])])

        row = {"id": cid,
               "sel_ok": bool(ok[sel]), "sel_con": float(con[sel]),
               "sel_ar": float(ar[sel]), "sel_score": float(score[sel]),
               "gt_top_ok": bool(ok[gt_top]), "gt_top_ar": float(ar[gt_top]),
               "gt_top_score": float(score[gt_top]),
               "gt_best_ok": bool(ok[gt_best]), "gt_best_ar": float(ar[gt_best]),
               # 정답 영역 최고점 칸이 전역 점수에서 몇 등인가
               "gt_rank": int(np.flatnonzero(order == gt_top)[0]) + 1,
               "sel_in_gt": bool(m[sel]),
               "any_ok": bool(ok.any()),
               # 촬영 거리의 자 — 밴드가 **원본 사진**에서 차지하는 선형 비.
               "frac": float(np.sqrt(((g[2]-g[0]) * (g[3]-g[1]))
                                     / max(1.0, img.shape[0] * img.shape[1])))}
        for k in a.topk:
            row[f"top{k}_ok"] = bool(ok[order[:k]].any())
        rows.append(row)

    n = len(rows)
    print(f"체크포인트 {ck.name} · 실촬 코퍼스 A n={n} (사람 제외 {n_ex}장 뺌)")
    print(f"  통과 정의: **밴드 전체 포함** 그리고 면적비 <= {a.tau}")
    print(f"  좌표는 레터박스({size}), 격자 {H}x{W}, stride {stride}\n")

    def pct(k):
        return 100.0 * sum(1 for r in rows if r[k]) / n

    print(f"  sel      지금 방식(전역 argmax)          통과 {pct('sel_ok'):5.1f}%")
    print(f"  gt_top   정답 영역 안 최고점 칸          통과 {pct('gt_top_ok'):5.1f}%")
    print(f"  gt_best  정답 영역 안 최선 칸            통과 {pct('gt_best_ok'):5.1f}%")
    for k in a.topk:
        print(f"  top{k:<3}    전역 점수 상위 {k} 안에 통과 상자  "
              f"{pct(f'top{k}_ok'):5.1f}%")
    print(f"  any      676칸 어디든 통과 상자 존재     {pct('any_ok'):5.1f}%\n")

    print(f"  선택된 칸이 정답 영역 안이었다: {pct('sel_in_gt'):5.1f}%")
    rk = np.array([r["gt_rank"] for r in rows])
    print(f"  정답 영역 최고점 칸의 전역 등수  중앙 {int(np.median(rk))} "
          f"· p90 {int(np.percentile(rk, 90))} · 최대 {int(rk.max())} (/{H*W})")
    for k, lbl in (("sel_ar", "sel"), ("gt_top_ar", "gt_top"),
                   ("gt_best_ar", "gt_best")):
        v = np.array([r[k] for r in rows])
        print(f"  면적비 {lbl:<8} p50 {np.median(v):.2f} "
              f"p90 {np.percentile(v, 90):.2f} max {v.max():.2f}")
    ss = np.array([r["sel_score"] for r in rows])
    gs = np.array([r["gt_top_score"] for r in rows])
    out_gt = [i for i, r in enumerate(rows) if not r["sel_in_gt"]]
    if out_gt:
        print(f"\n  정답 밖 칸이 뽑힌 {len(out_gt)}장에서 점수 경쟁:")
        print(f"    뽑힌 칸 점수  중앙 {np.median(ss[out_gt]):.3f}")
        print(f"    정답 영역 최고 중앙 {np.median(gs[out_gt]):.3f}")

    # 거리로 층을 가른다 — **평균은 못하는 층을 숨긴다.**
    fr = np.array([r["frac"] for r in rows])
    q1, q2 = np.percentile(fr, [33.3, 66.7])
    print("\n  촬영 거리별 (밴드가 사진에서 차지하는 선형 비)")
    print(f"    {'층':<7}{'n':>5}{'sel':>9}{'gt_top':>9}{'gt_best':>9}{'any':>9}")
    for lbl, m in (("가까움", fr >= q2), ("중간", (fr >= q1) & (fr < q2)),
                   ("멂", fr < q1)):
        idx = np.flatnonzero(m)
        if idx.size == 0:
            continue

        def f100(k, idx=idx):
            return 100.0 * sum(1 for i in idx if rows[i][k]) / idx.size
        print(f"    {lbl:<7}{idx.size:>5}{f100('sel_ok'):>8.1f}%"
              f"{f100('gt_top_ok'):>8.1f}%{f100('gt_best_ok'):>8.1f}%"
              f"{f100('any_ok'):>8.1f}%")

    print("\n  읽는 법 (자문 §6.1)")
    print("    gt_top 이 sel 보다 크게 높다      -> **선택 실패**(점수 경쟁)")
    print("    gt_best 가 gt_top 보다 크게 높다  -> 점수와 위치 품질 불일치")
    print("    gt_best 도 낮다                   -> **회귀·표현·입력 품질**")

    p = Path(a.out) if a.out else OUT / f"cells_{ck.stem}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n  -> {p}")


if __name__ == "__main__":
    main()
