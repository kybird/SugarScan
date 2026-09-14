# 극성 정의 셋을 사람 정답에 대조한다 — 2026-09-13.
#
# 자끼리는 어느 정의가 맞는지 못 가린다. polarity_gt.jsonl(사람 30장, 블라인드)
# 이 정답이고, 이 스크립트는 정의를 '고르는' 게 아니라 '채점'한다.
#
# 세 정의는 전부 같은 꼴이다 — 밴드의 두 꼬리(p5·p95) 중 배경에서 더 먼 쪽이
# 잉크다. 다른 것은 **배경(bg)을 어디서 재는가** 하나뿐이다:
#   crop   GM 크롭 전체 중앙값        (현행 measure_polarity.polarity_of)
#   out    GM 크롭에서 밴드를 뺀 나머지 중앙값
#   band   밴드 안 중앙값
#
#   conda run -n sugartrain python score_polarity_defs.py
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from diag_polarity_bg import rows_for  # noqa: E402

GT = HERE / "polarity_gt.jsonl"


def main():
    gt = {}
    meta = {}
    for line in open(GT, encoding="utf-8"):
        r = json.loads(line)
        gt[r["id"]] = bool(r["inverted"])
        meta[r["id"]] = r["n"]
    rows = {r[0]: r for r in rows_for(set()) if r[0] in gt}
    print(f"정답 {len(gt)}장 중 자로 다시 잰 것 {len(rows)}장 "
          f"· 사람 반전 {sum(gt.values())}장\n")

    defs = {"crop(현행)": 2, "out(밴드밖)": 3, "band(밴드안)": 9}
    score = {k: [0, 0, 0] for k in defs}     # 맞힘, 반전을 정상으로, 정상을 반전으로
    wrong = {k: [] for k in defs}
    for img_id, r in rows.items():
        p5, p95 = r[4], r[5]
        truth = gt[img_id]
        for name, idx in defs.items():
            bg = r[idx]
            pred = abs(p95 - bg) > abs(p5 - bg)
            if pred == truth:
                score[name][0] += 1
            elif truth:
                score[name][1] += 1
                wrong[name].append((meta[img_id], r[1], "반전->정상"))
            else:
                score[name][2] += 1
                wrong[name].append((meta[img_id], r[1], "정상->반전"))

    n = len(rows)
    print(f"{'정의':16} {'정확':>6} {'반전 놓침':>9} {'정상 오검':>9}")
    for name in defs:
        a, b, c = score[name]
        print(f"{name:16} {a:3d}/{n:<3} {b:9d} {c:9d}")
    for name in defs:
        if wrong[name]:
            print(f"\n[{name}] 틀린 장 {len(wrong[name])}")
            for num, dev, how in sorted(wrong[name]):
                print(f"  {num:02d}  {dev:28} {how}")


if __name__ == "__main__":
    main()
