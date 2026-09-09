# 밴드 라벨 감사 큐 — 라벨 안에 잉크 없는 여백이 큰 장을 모아 사람이 눈으로
# 확인하게 한다. 산출: label_audit_queue.json
#
# 왜: 두 라벨 묶음의 관례가 갈린다는 측정이 나왔다. 이번 세션 51장은 왼쪽
# 여백 중앙 0.073(획에 붙임)인데 이전 묶음 35장은 0.215(빈 자리 포함)다.
# 관례가 섞이면 검출 목표가 오염되므로 정본을 정해야 하고, 그 전에 실제로
# 그렇게 찍혔는지 사람이 봐야 한다.
#
# 여백은 **라벨 상자 안에서** 잰다 — 열별 잉크 프로파일에서 첫/마지막 잉크
# 열까지의 거리다. 큰 순서로 정렬한다.
import json
from pathlib import Path

import cv2
import numpy as np

from eval_reader import load_gray

HERE = Path(__file__).resolve().parent
DAT = HERE.parent / "upstream" / "datumo" / "extracted" / "TILDE"
OUT = HERE / "label_audit_queue.json"
MIN_MARGIN = 0.08


def main() -> int:
    band = {}
    for l in (HERE / "band_boxes.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            q = np.array(j["quad"], float)
            band[j["id"]] = (q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max())
    wide = set(json.loads((HERE / "_diag" / "wide_all" / "wide_ids.json")
                          .read_text(encoding="utf-8")))
    gt = {}
    for l in (HERE.parent / "upstream" / "datumo" / "labels.jsonl").read_text(
            encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            gt[j["id"]] = str(j.get("reading") or "")
    corr = HERE / "gt_corrections.jsonl"
    if corr.exists():
        for l in corr.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                gt[j["id"]] = str(j["corrected"])

    rows = []
    for cid, b in sorted(band.items()):
        p = DAT / f"{cid}.jpg"
        if not p.exists():
            continue
        g = load_gray(p)
        x0, y0, x1, y1 = [int(v) for v in b]
        sub = g[max(0, y0):y1, max(0, x0):x1]
        if sub.size == 0 or sub.shape[1] < 10:
            continue
        t, _ = cv2.threshold(sub, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        dark = sub < t
        ink = dark if dark.mean() < 0.5 else ~dark
        col = ink.mean(axis=0)
        on = np.where(col > max(0.03, col.max() * 0.15))[0]
        if len(on) == 0:
            continue
        W = sub.shape[1]
        left = on[0] / W
        if left < MIN_MARGIN:
            continue
        batch = "이번세션(가로형)" if cid in wide else "이전묶음(세로형)"
        rows.append({
            "id": cid,
            "stratum": batch,
            "note": f"왼쪽 빈 여백 {left*100:.0f}% · 정답값 {gt.get(cid, '?')}",
            "_left": left,
        })
    rows.sort(key=lambda r: -r["_left"])
    for r in rows:
        r.pop("_left")
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"여백 {MIN_MARGIN:.0%} 이상: {len(rows)}장")
    for k, v in Counter(r["stratum"] for r in rows).items():
        print(f"  {k}: {v}")
    print(f"큐: {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
