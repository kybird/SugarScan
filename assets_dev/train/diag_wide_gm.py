# G25 보조 — 가로 LCD 51장에 대한 GM 검출 성적을 세고, ft2/ft3/ft4 를 같은 잣대로 비교한다.
#
# "GM 실패"의 정의(2026-09-04 Case 9 와 동일): 가로로 보이는 화면인데
#   - 검출이 없거나 (미검출)
#   - 검출 박스의 w/h < 1.2 (세로로 접힘 — wide 화면을 잡았다면 1.2 을 넘어야 한다)
# 사진이 회전돼 화면이 세로로 보이는 장(1564·1565)은 이 기준에서 제외한다.
#
# 사용:
#   python diag_wide_gm.py --quads gmscreen_quads.jsonl --label ft2
#   python diag_wide_gm.py --quads gmscreen_quads_ft3.jsonl --label ft3
#   python diag_wide_gm.py --quads gmscreen_quads_ft4.jsonl --label ft4
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WIDE = HERE / "_diag" / "wide_all" / "wide_ids.json"
# 사진이 회전돼 화면이 세로로 보이는 장(Case 9: 2장뿐, 사람 라벨 0.37·0.38)
ROTATED = {"glucose_batch1/1564", "glucose_batch1/1565"}


def horiz_ids():
    """가로로 보이는 장의 id — 회전 사진 2장은 뺀다."""
    return [i for i in json.loads(WIDE.read_text(encoding="utf-8"))
            if i not in ROTATED]


def classify(quads, fold_thr=1.2):
    """가로 장마다 (id, 판정, score, w/h) 를 낸다.

    판정 규칙은 **여기 하나뿐이다.** gm_preproc_ab.py 도 이 함수를 부른다 —
    같은 규칙을 두 군데 쓰면 한쪽만 고쳐져 두 보고서가 조용히 갈라진다
    (antipatterns/duplicated-geometry-implementation).
    """
    rows, ok, miss, fold = [], 0, 0, 0
    for i in horiz_ids():
        q = quads.get(i)
        if q is None:
            miss += 1
            rows.append((i, "미검출", None, None))
            continue
        a = q["quad"]
        w = max(p[0] for p in a) - min(p[0] for p in a)
        h = max(p[1] for p in a) - min(p[1] for p in a)
        ar = w / max(h, 1e-6)
        if ar < fold_thr:
            fold += 1
            rows.append((i, f"접힘 w/h={ar:.2f}", round(q.get("score", 0), 3), ar))
        else:
            ok += 1
            rows.append((i, f"OK w/h={ar:.2f}", round(q.get("score", 0), 3), ar))
    return rows, ok, miss, fold


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quads", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--fold", type=float, default=1.2,
                    help="이 w/h 미만이면 '접힘'으로 센다")
    args = ap.parse_args()

    wide = json.loads(WIDE.read_text(encoding="utf-8"))
    quads = {}
    for l in Path(args.quads).read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            quads[j["id"]] = j

    total_all = len(quads)
    rows, ok, miss, fold = classify(quads, args.fold)
    n = ok + miss + fold
    print(f"=== {args.label} ===")
    print(f"전량 검출: {total_all}/2512")
    print(f"가로로 보이는 {n}장 중: OK {ok} · 미검출 {miss} · 접힘(w/h<{args.fold}) {fold}"
          f" → GM 실패 {miss + fold}/{n}")
    print("실패 목록:")
    for i, why, s, ar in rows:
        if not why.startswith("OK"):
            print(f"  {i:26s} {why}  score={s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
