# GM 검출 근접 동점 전량 측정 — 카드 「GM 검출이 근접 동점일 때 top-1 을
# 그냥 받는다」(2026-09-24 무인). 재기만 한다 — 정책 채택은 사람 몫(AC#4).
#
# 대상: 코퍼스 전량(datumo labels). 추론 경로는 운영과 동일하게
# detect_datumo_gm 기본(stretch 전처리·conf 0.25). 후보 추출은
# diag_gm_candidate_tie.load_model/candidates 를 그대로 import(자 복제 금지).
# 사람 라벨은 gm_quads.quad_rows(표시 좌표계 — GM 라벨러 규약).
#
# 동점 기준 TIE_REL=0.05: 1826 재현(카드 Notes)에서 점수차 0.3%·입력
# 픽셀 평균 3.37/255 흔들림에 top-1 이 뒤집혔다 — 안정 여유가 5% 도 안
# 되는 장은 '모델이 못 정한' 상태로 본다(보수 상한).
#
# 사용: python measure_gm_ties.py   (→ _diag/gm_ties/ 보고)
import json
import sys

import numpy as np

import detect_datumo_gm as D                       # noqa: E402
from diag_gm_candidate_tie import load_model, candidates, TIE_REL  # noqa: E402

HERE = __import__("pathlib").Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"
OUT = HERE / "_diag" / "gm_ties"
CONF = 0.25
MODE = "stretch"          # 운영 detect_datumo_gm 기본
AR_MIN, AR_MAX = 0.30, 3.5     # 제정신 검사: 후보 종횡비 범위(AC#3)
SCREEN_FRAC_MIN = 0.02         # 화면이 사진 면적에서 차지할 하한
AREA_RATIO_CAP = 4.0           # 동점 경쟁자 간 넓이비 상한


def _iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1])
          - inter)
    return inter / ua if ua > 0 else 0.0


def sane(box, W, H):
    """제정신 검사 — 종횡비·화면 면적비."""
    w, h = box[2] - box[0], box[3] - box[1]
    if w <= 0 or h <= 0:
        return False
    ar = w / h
    if not (AR_MIN <= ar <= AR_MAX):
        return False
    if (w * h) / (W * H) < SCREEN_FRAC_MIN:
        return False
    return True


def main() -> int:
    labels = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labels[j["id"]] = j["image"]
    hq = {}
    for r in __import__("gm_quads").quad_rows():
        q = np.asarray(r["quad"], float)
        hq[r["id"]] = [q[:, 0].min(), q[:, 1].min(),
                       q[:, 0].max(), q[:, 1].max()]

    model = load_model()
    rows = []
    n_done = 0
    for cid, rel in sorted(labels.items()):
        img = D._load_bgr(DATUMO / rel)
        if img is None:
            continue
        H, W = img.shape[:2]
        cands, _ = candidates(model, img, 416, MODE, CONF)
        if not cands:
            rows.append({"id": cid, "miss": True})
            n_done += 1
            continue
        s1, b1 = cands[0]
        s2, b2 = cands[1] if len(cands) > 1 else (0.0, None)
        gap = (s1 - s2) / s1 if s1 > 0 else 1.0
        a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        a2 = ((b2[2] - b2[0]) * (b2[3] - b2[1])) if b2 else 0.0
        ar_ratio = (max(a1, a2) / min(a1, a2)) if min(a1, a2) > 0 else 0.0
        near_tie = gap < TIE_REL
        sane1 = sane(b1, W, H)
        # 제정신 검사 적용 시의 top-1 (정책 제안이 아니라 측정 — AC#3)
        pick = b1
        picked = "top1"
        if not sane1:
            for s, b in cands[1:]:
                if sane(b, W, H):
                    pick = b
                    picked = "first-sane"
                    break
            else:
                pick, picked = b1, "top1(검사 통과 후보 없음)"
        gt = hq.get(cid)
        rows.append({
            "id": cid, "s1": s1, "s2": s2, "gap": gap,
            "area_ratio": ar_ratio, "near_tie": near_tie,
            "iou_top1": _iou(b1, gt) if gt else None,
            "iou_pick": _iou(pick, gt) if gt else None,
            "picked": picked, "changed": pick is not b1,
            "tie_flip_area": bool(near_tie and ar_ratio > AREA_RATIO_CAP),
        })
        n_done += 1
        if n_done % 250 == 0:
            print(f".. {n_done}", file=sys.stderr)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8")

    scorable = [r for r in rows if r.get("iou_top1") is not None]
    ties = [r for r in scorable if r["near_tie"]]
    rest = [r for r in scorable if not r["near_tie"]]
    rep = []
    rep.append(f"전량 {len(rows)}장 — 사람 라벨과 채점 가능 {len(scorable)}장"
               f" · 검출 실패 {sum(1 for r in rows if r.get('miss'))}장")
    rep.append(f"근접 동점(gap<{TIE_REL}): {len(ties)}장 "
               f"({100*len(ties)/max(1,len(scorable)):.1f}%) · "
               f"동점+넓이비>{AREA_RATIO_CAP}: "
               f"{sum(1 for r in ties if r['tie_flip_area'])}장")
    for name, grp in (("동점", ties), ("비동점", rest)):
        v = np.asarray([r["iou_top1"] for r in grp])
        rep.append(f"  {name} n={len(grp)} · top1 IoU 중앙 {np.median(v):.3f}"
                   f" · p10 {np.percentile(v,10):.3f}"
                   f" · <0.5 {int((v<0.5).sum())}장")
    ch = [r for r in scorable if r["changed"]]
    up = [r for r in ch if r["iou_pick"] > r["iou_top1"] + 1e-9]
    dn = [r for r in ch if r["iou_pick"] < r["iou_top1"] - 1e-9]
    rep.append(f"제정신 검사 후보 교체: {len(ch)}장 — 회복 {len(up)} · "
               f"퇴보 {len(dn)} · 동일 {len(ch)-len(up)-len(dn)}")
    rep.append("회복/퇴보 장(±0.1 이상만):")
    for r in sorted(ch, key=lambda r: r["iou_pick"]-r["iou_top1"]):
        d = r["iou_pick"] - r["iou_top1"]
        if abs(d) >= 0.1:
            rep.append(f"  {r['id']}  {r['iou_top1']:.3f}→{r['iou_pick']:.3f}"
                       f"  ({d:+.3f})")
    text = "\n".join(rep)
    (OUT / "report.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
