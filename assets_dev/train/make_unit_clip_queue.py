# 밴드 라벨 전수 감사 큐 — 사람 제외 선언 장을 빼고 전 라벨을 depth
# 내림차순(걸침 의심 순)으로 웹툴 큐로 내보낸다.
#
# 사람 선언(2026-09-27, peteroh): 밴드 라벨 규약은 '숫자줄만' 하나다.
# 단위가 라벨에 보이는 장은 여백이 넉넉해 가장자리에 걸친 것 — 조여
# 없앤다. 판정 기준(사람 확정): 단위 글자가 절반 이상 보이면 조임,
# 모서리 걸침은 방치, 기울어 불가피한 걸침은 허용(숫자 온전 포함이
# 우선). 1픽셀까지 자르지 않는다.
#
# 2026-09-27 밤 전수로 확장(사람 결정: "그냥 전수 검사하는게 낫겠다"):
# depth 0.95~1.2 임계로 가리니 예외가 계속 나왔다 — 1091(depth 1.51)은
# '예측 실패'로 제외했으나 단위 전체 포함 의심이고, 709·993(저depth)은
# 반대편에서 누락됐다. 임계를 없애고 전부 본다. depth 는 정렬 순서일
# 뿐 판정에 쓰지 않는다.
#
# 사용:
#   python make_unit_clip_queue.py          # band_unit_clip_queue.json 갱신
import json
from pathlib import Path

from band_exclusions import load_excluded

HERE = Path(__file__).resolve().parent
LABELS = HERE / "band_boxes.jsonl"
PRED = HERE / "band_quads_pred.jsonl"
OUT = HERE / "band_unit_clip_queue.json"


def main():
    ex = load_excluded()
    pred = {}
    for line in PRED.read_text(encoding="utf-8").splitlines():
        if line.strip():
            j = json.loads(line)
            if j.get("quad"):
                pred[j["id"]] = j["quad"]

    rows = []
    for line in LABELS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        j = json.loads(line)
        if not j.get("quad") or j["id"] not in pred or j["id"] in ex:
            continue
        l, p = j["quad"], pred[j["id"]]
        l_y1 = max(pt[1] for pt in l)
        p_ys = [pt[1] for pt in p]
        p_y0, p_y1 = min(p_ys), max(p_ys)
        depth = (l_y1 - p_y0) / (p_y1 - p_y0) if p_y1 > p_y0 else 0.0
        rows.append({"id": j["id"], "depth": round(depth, 3)})

    rows.sort(key=lambda r: -r["depth"])
    out = [{"id": r["id"], "stratum": "unit-clip",
            "note": f"전수감사 depth {r['depth']:.2f}"} for r in rows]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{OUT.name} · {len(out)}장 (사람 제외 {len(ex)}장 뺀 전수, depth 내림차순)")
    for r in rows[:5]:
        print(f"  {r['id']:<26} {r['depth']:.3f}")


if __name__ == "__main__":
    main()
