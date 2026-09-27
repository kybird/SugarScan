# 단위가 밴드 라벨에 '걸쳐진' 의심 장을 내림차순 정렬해 웹툴 큐로 내보낸다.
#
# 사람 선언(2026-09-27, peteroh): 밴드 라벨 규약은 '숫자줄만' 하나다.
# 단위(mg/dL)가 라벨에 보이는 장은 단위를 포함하려 한 것이 아니라 여백이
# 넉넉해 박스 가장자리에 단위가 **걸쳐진 것**이다. 그래서 이 감사는
# '어느 규약인지 고르기'가 아니라 '걸침을 조여 없애기'다 — 걸친 장은
# 드래그로 하단을 올리고 저장, 깨끗한 장은 I키로 확인 마크만 남긴다.
#
# 판별 자: 사람 라벨 하단이 atone_s0 예측 하단에 가까울수록 의심이다.
# 예측은 단위 줄을 흡수하는 경향(2026-09-27 진단, 높이비 중앙 1.10)이
# 있어 "예측만큼 깊은 라벨"은 단위까지 내려갔을 가능성이 크다.
#   depth = (라벨하단 - 예측상단) / (예측하단 - 예측상단)
# 큐에는 0.95 <= depth <= 1.2 만 넣는다(내림차순). 1.2 을 크게 넘는 장은
# 라벨 걸침이 아니라 예측이 위쪽에 붙어 실패한 장이라 대상이 아니다.
# 이 자는 순위를 낼 뿐 판정하지 않는다 — 걸쳤는지는 사람이 화면에서 본다.
#
# 사용:
#   python make_unit_clip_queue.py          # band_unit_clip_queue.json 갱신
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = HERE / "band_boxes.jsonl"
PRED = HERE / "band_quads_pred.jsonl"
OUT = HERE / "band_unit_clip_queue.json"


def main():
    pred = {}
    for line in PRED.read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            if j.get("quad"):
                pred[j["id"]] = j["quad"]

    rows, skipped_deep = [], 0
    for line in LABELS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        j = json.loads(line)
        if not j.get("quad") or j["id"] not in pred:
            continue
        l, p = j["quad"], pred[j["id"]]
        l_y1 = max(pt[1] for pt in l)
        p_ys = [pt[1] for pt in p]
        p_y0, p_y1 = min(p_ys), max(p_ys)
        depth = (l_y1 - p_y0) / (p_y1 - p_y0) if p_y1 > p_y0 else 0.0
        if depth > 1.2:
            skipped_deep += 1   # 예측이 위에 붙은 실패 장 — 걸침 감사 대상 아님
            continue
        if depth >= 0.95:
            rows.append({"id": j["id"], "depth": round(depth, 3)})

    rows.sort(key=lambda r: -r["depth"])
    out = [{"id": r["id"], "stratum": "unit-clip",
            "note": f"걸침 depth {r['depth']:.2f}"} for r in rows]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{OUT.name} · {len(out)}장 (depth>1.2 예측실패 {skipped_deep}장 제외)"
          f" · 상위 10:")
    for r in rows[:10]:
        print(f"  {r['id']:<28} {r['depth']:.3f}")


if __name__ == "__main__":
    main()
