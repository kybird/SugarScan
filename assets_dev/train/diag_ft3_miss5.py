# ft3 가 놓친 5장 회귀 진단 — 1046 · 1826 · 2198 · 498 · 702.
#
# 물음 둘:
#   ① 점수 임계(CONF=0.25) 때문인가, 아예 후보가 없는가
#   ② 다섯 장의 공통 성격은 무엇인가
#
# 임계 문제와 후보 부재는 눈으로 구별되지 않는다 — 둘 다 "출력 없음"으로
# 보인다. 그래서 임계를 0 에 가깝게 내려 **원시 후보의 최고 점수**를 직접 찍는다.
# 후보가 0.25 바로 아래에 있으면 임계 문제이고, 바닥이면 모델이 못 본 것이다.
#
# 같은 장을 stretch / letterbox 두 전처리로 나란히 본다 — 2026-09-16 A/B 에서
# 다섯 장이 레터박스로는 전부 살아났기 때문이다. 전처리가 원인인지 여기서
# 점수로 확인한다.
#
# 사용: python diag_ft3_miss5.py
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

sys.path.insert(0, "D:/tmp/YOLOX")
from yolox.exp import get_exp  # noqa: E402
from yolox.utils import postprocess  # noqa: E402

import detect_datumo_gm as D  # _load_bgr 를 그대로 쓴다
# 후보 뽑기(모델 적재 + 전처리 + postprocess)는 diag_gm_candidate_tie 에 하나만
# 둔다. 2026-09-17 에 그 경로를 두 파일이 각자 짜 놨다가 합쳤다
# ([[duplicated-geometry-implementation]]).
from diag_gm_candidate_tie import candidates, load_model

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "_diag" / "ft3_miss5"

IDS = [f"glucose_batch1/{n}" for n in ("1046", "1826", "2198", "498", "702")]
CKPT = HERE / "yolox_out" / "gmscreen_ft3" / "best_ckpt_np1.pth"
BASE = HERE / "gmscreen_quads_base_before_ft3_20260912.jsonl"
HUMAN = HERE / "screen_boxes.jsonl"
DEVICES = HERE / "device_labels.jsonl"
CONF_PROD = 0.25          # 운영 임계 — detect_datumo_gm.CONF 와 같은 값
CONF_PROBE = 0.001        # 후보를 끝까지 보려고 내리는 값


def load_rows(p, pred=lambda j: True):
    out = {}
    for l in Path(p).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            if pred(j):
                out[j["id"]] = j
    return out


def rect(quad):
    q = np.asarray(quad, float)
    return [q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    model = load_model(CKPT)

    base = load_rows(BASE)
    human = load_rows(HUMAN, lambda j: j.get("source") == "human" and j.get("quad"))
    devs = load_rows(DEVICES)
    labels = load_rows(DATUMO / "labels.jsonl")

    print(f"체크포인트 {CKPT.name} · 운영 임계 {CONF_PROD} · 탐침 임계 {CONF_PROBE}")
    print(f"\n{'id':<10}{'기기':<18}{'전처리':<11}{'최고점수':>9}"
          f"{'후보수':>7}{'운영임계':>9}{'IoU(사람)':>11}")

    tiles = []
    summary = []
    for gid in IDS:
        img0 = D._load_bgr(DATUMO / labels[gid]["image"])
        sh, sw = img0.shape[:2]
        row = {"id": gid, "wh": round(sw / sh, 3),
               "brand": devs.get(gid, {}).get("brand", "?"),
               "mean_lum": round(float(cv2.cvtColor(
                   img0, cv2.COLOR_BGR2GRAY).mean()), 1)}
        panels = {}
        for mode in ("stretch", "letterbox"):
            cands, _ = candidates(model, img0, 416, mode, CONF_PROBE)
            if not cands:
                row[mode] = {"top": 0.0, "n": 0, "box": None}
            else:
                row[mode] = {"top": cands[0][0], "n": len(cands),
                             "box": cands[0][1]}
            panels[mode] = row[mode]["box"]

            iou = "-"
            if gid in human and row[mode]["box"]:
                h = rect(human[gid]["quad"])
                b = row[mode]["box"]
                x0, y0 = max(b[0], h[0]), max(b[1], h[1])
                x1, y1 = min(b[2], h[2]), min(b[3], h[3])
                inter = max(0., x1 - x0) * max(0., y1 - y0)
                ua = ((b[2]-b[0])*(b[3]-b[1]) + (h[2]-h[0])*(h[3]-h[1]) - inter)
                iou = f"{inter/ua:.3f}" if ua > 0 else "-"
            row[f"iou_{mode}"] = iou
            print(f"{gid.split('/')[1]:<10}{row['brand']:<18}{mode:<11}"
                  f"{row[mode]['top']:>9.4f}{row[mode]['n']:>7}"
                  f"{'통과' if row[mode]['top'] >= CONF_PROD else '탈락':>9}"
                  f"{iou:>11}")
        summary.append(row)
        tiles.append(draw(img0, gid, base.get(gid), human.get(gid), panels))

    sheet(tiles, OUT / "miss5.png")
    (OUT / "miss5.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n── 공통 성격 (n={len(summary)}) " + "─" * 30)
    print(f"{'id':<8}{'기기':<18}{'사진 w/h':>9}{'평균휘도':>9}"
          f"{'stretch점수':>12}{'letterbox점수':>14}")
    for r in summary:
        print(f"{r['id'].split('/')[1]:<8}{r['brand']:<18}{r['wh']:>9.3f}"
              f"{r['mean_lum']:>9.1f}{r['stretch']['top']:>12.4f}"
              f"{r['letterbox']['top']:>14.4f}")
    br = {}
    for r in summary:
        br[r["brand"]] = br.get(r["brand"], 0) + 1
    print("  기기 분포: " + " · ".join(f"{k} {v}장" for k, v in br.items()))
    wide = sum(1 for r in summary if r["wh"] > 1.0)
    print(f"  가로 사진(w/h>1) {wide}장 / {len(summary)}")
    compare_population(summary, human, labels)
    thr = sum(1 for r in summary
              if 0 < r["stretch"]["top"] < CONF_PROD)
    none_ = sum(1 for r in summary if r["stretch"]["n"] == 0)
    print(f"  stretch 에서 임계 탈락(후보는 있음) {thr}장 · 후보 자체 없음 {none_}장")
    print(f"-> {OUT/'miss5.png'} · {OUT/'miss5.json'}")
    return 0


def compare_population(summary, human, labels, sample_n=300, seed=20260916):
    """다섯 장의 성질을 **모집단과 견준다.**

    "어둡다" · "화면이 작다" 는 비교 없이는 말이 안 된다. 면적비는 사람 화면
    라벨 전량(ow/oh 가 행에 있다)으로, 휘도는 코퍼스 무작위 표본으로 견준다.
    표본이라 n 을 함께 적는다.
    """
    import random

    def area_ratio(row):
        r = rect(row["quad"])
        return ((r[2] - r[0]) * (r[3] - r[1])) / (row["ow"] * row["oh"])

    def screen_wh(row):
        r = rect(row["quad"])
        return (r[2] - r[0]) / max(r[3] - r[1], 1e-6)

    pop_ar = np.array([area_ratio(j) for j in human.values()
                       if j.get("ow") and j.get("oh")])
    five = [r["id"] for r in summary]
    five_ar = np.array([area_ratio(human[i]) for i in five if i in human])
    pop_wh = np.array([screen_wh(j) for j in human.values()])
    five_wh = np.array([screen_wh(human[i]) for i in five if i in human])

    rng = random.Random(seed)
    pool = [g for g in labels if g not in set(five)]
    pick = rng.sample(pool, min(sample_n, len(pool)))
    lum = []
    for g in pick:
        im = cv2.imread(str(DATUMO / labels[g]["image"]), cv2.IMREAD_GRAYSCALE)
        if im is not None:
            lum.append(float(im.mean()))
    lum = np.array(lum)
    five_lum = np.array([r["mean_lum"] for r in summary])

    print(f"\n── 모집단 대조 " + "─" * 40)
    print(f"  화면 종횡비  다섯 장 n={len(five_wh)} "
          + " ".join(f"{v:.2f}" for v in sorted(five_wh))
          + f"  | 사람 라벨 전량 n={len(pop_wh)} 중앙 {np.median(pop_wh):.2f}"
          f" (p90 {np.percentile(pop_wh,90):.2f} · p99 "
          f"{np.percentile(pop_wh,99):.2f})")
    for i in five:
        if i in human:
            v = screen_wh(human[i])
            print(f"    {i.split('/')[1]:<6} w/h {v:5.2f} — 모집단 상위 "
                  f"{100.0*(pop_wh > v).mean():4.1f}%")
    print(f"  화면 면적비  다섯 장 n={len(five_ar)} 중앙 {np.median(five_ar):.4f}"
          f"  | 사람 라벨 전량 n={len(pop_ar)} 중앙 {np.median(pop_ar):.4f}"
          f" (p10 {np.percentile(pop_ar,10):.4f} · p90 {np.percentile(pop_ar,90):.4f})")
    pct = 100.0 * (pop_ar < np.median(five_ar)).mean()
    print(f"    다섯 장 중앙값은 모집단의 하위 {pct:.0f}% 지점이다")
    print(f"  평균 휘도    다섯 장 n={len(five_lum)} 중앙 {np.median(five_lum):.1f}"
          f"  | 코퍼스 무작위 표본 n={len(lum)} 중앙 {np.median(lum):.1f}"
          f" (p10 {np.percentile(lum,10):.1f} · p90 {np.percentile(lum,90):.1f})")
    pct = 100.0 * (lum < np.median(five_lum)).mean()
    print(f"    다섯 장 중앙값은 표본의 하위 {pct:.0f}% 지점이다")
    print(f"    (휘도 표본 시드 {seed} · 다섯 장은 풀에서 제외)")


def draw(img0, gid, base_row, human_row, panels):
    im = img0.copy()
    if human_row:
        h = [int(v) for v in rect(human_row["quad"])]
        cv2.rectangle(im, (h[0], h[1]), (h[2], h[3]), (0, 0, 230), 8)
    if base_row:
        b = [int(v) for v in rect(base_row["quad"])]
        cv2.rectangle(im, (b[0], b[1]), (b[2], b[3]), (230, 230, 0), 8)
    for mode, col in (("stretch", (0, 165, 255)), ("letterbox", (0, 230, 0))):
        if panels.get(mode):
            p = [int(v) for v in panels[mode]]
            cv2.rectangle(im, (p[0], p[1]), (p[2], p[3]), col, 8)
    cv2.putText(im, gid.split("/")[1], (20, 90), cv2.FONT_HERSHEY_SIMPLEX,
                3.0, (255, 255, 255), 8)
    return im


def sheet(tiles, out_png, cols=5, cell=(520, 660)):
    pads = []
    for im in tiles:
        s = min(cell[0] / im.shape[1], cell[1] / im.shape[0])
        im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)))
        pad = np.zeros((cell[1], cell[0], 3), np.uint8)
        pad[:im.shape[0], :im.shape[1]] = im
        pads.append(pad)
    grid = [np.hstack(pads[i:i + cols]) for i in range(0, len(pads), cols)]
    w = max(g.shape[1] for g in grid)
    grid = [np.pad(g, ((0, 0), (0, w - g.shape[1]), (0, 0))) for g in grid]
    canvas = np.vstack(grid)
    cv2.putText(canvas, "red=human  cyan=base  orange=ft3 stretch  green=ft3 letterbox",
                (10, canvas.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 255), 2)
    cv2.imwrite(str(out_png), canvas)


if __name__ == "__main__":
    raise SystemExit(main())
