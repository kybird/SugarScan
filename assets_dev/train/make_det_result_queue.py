# 밤 학습(atone_tf640w15) 결과 열람 큐 — 잘됨/못됨 두 큐를 낸다.
#
# 사람 요청(2026-09-28): 웹툴에서 결과를 잘된 것·못된 것 같이 보고 싶다.
# 두 평가 jsonl(atone_s0 · atone_tf640w15)을 교차해 IoU 변화로 가른다.
#   better — 개선 상위순(파란 예측이 새 모델이다)
#   worse — 악화순(완전 오탐이 최상단)
# 웹툴에서 파란 박스 = atone_tf640w15 예측(band_quads_pred.jsonl 를 이
# 모델로 다시 썼다 — atone_s0 예측은 band_quads_pred_atone_s0_20260928
# .jsonl 백업).
#
# 사용:
#   python make_det_result_queue.py
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE / "_diag" / "band_real" / "atone_s0.jsonl"
NEW = HERE / "_diag" / "band_real" / "atone_tf640w15.jsonl"


def load(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def main():
    old = {r["id"]: r for r in load(OLD)}
    rows = []
    for r in load(NEW):
        o = old.get(r["id"])
        if not o:
            continue
        d_old = o.get("det", False)
        d_new = r.get("det", False)
        if d_old and d_new:
            delta = r["iou"] - o["iou"]
            note = f"IoU {o['iou']:.2f}→{r['iou']:.2f} ({delta:+.2f}) · 면적비 {r['area_ratio']:.2f}"
        elif not d_new:
            delta = -1.0
            note = f"미검출(score {r['score']:.2f}) — s0 IoU {o['iou']:.2f}"
        else:
            delta = 1.0
            note = f"s0 미검출 → 신규 검출 IoU {r['iou']:.2f}"
        rows.append({"id": r["id"], "delta": round(delta, 4), "note": note})

    better = sorted(rows, key=lambda r: -r["delta"])
    worse = sorted(rows, key=lambda r: r["delta"])

    (HERE / "det_better_queue.json").write_text(json.dumps(
        [{"id": r["id"], "stratum": "better", "note": r["note"]}
         for r in better], ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "det_worse_queue.json").write_text(json.dumps(
        [{"id": r["id"], "stratum": "worse", "note": r["note"]}
         for r in worse], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"better {len(better)}장 · worse {len(worse)}장")
    print("worse 앞 5:")
    for r in worse[:5]:
        print(f"  {r['id']:<26} {r['note']}")


if __name__ == "__main__":
    main()
