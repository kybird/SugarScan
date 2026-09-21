# Roboflow 사진을 **우리 밴드 규약으로** 라벨할 대기열을 짠다.
#
# 왜(BAND_EXP_PLAN §20.5): 우리 검출기는 우리 규약(Datumo)에서 98.3% 이고
# 좌우가 대칭인데(쏠림 +0.001) Roboflow 에서는 93.4% 이고 +0.247 쏠려 있다.
# **그 6.6점이 모델 결함인지 라벨 규약 차이인지 가르지 못한 채로** 개입을
# 세 번 걸었고 세 번 다 기각됐다. 가르려면 같은 사진을 우리 규약으로 재야 한다.
#
# 대기열은 두 층으로 짠다. 층을 **저장해 두는 이유**는 나중에 섞어 세지
# 않기 위해서다 — 실패만 라벨해 놓고 전체 쏠림을 말하면 표본이 편향된다.
#
#   fail  `일부만`으로 떨어진 장. 4시드 중 2시드 이상에서 그런 장만 센다
#         (시드 하나의 변덕을 층으로 올리지 않는다). 이 층이 답하는 질문:
#         **그 실패 중 몇 장이 규약 때문인가.**
#   rand  나머지에서 무작위. 이 층이 답하는 질문:
#         **좌-우 쏠림 +0.247 이 규약 차이로 설명되는가.**
#         연속량이라 장수가 적게 든다.
#
# 대기열에는 **모델 예측도 Roboflow 라벨도 담지 않는다.** 화면에 미리 보여
# 주면 사람이 그것을 따라 그리게 되고, 그러면 규약 차이를 재려던 측정이
# 모델과의 일치도 측정으로 바뀐다.
#
# 봉인 시험(rf_split.json test 687)은 **넣지 않는다.** 개발 586 에서만 뽑는다.
import argparse
import json
import random
from pathlib import Path

from report_fail_mix import rows, classify

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="atone")
    ap.add_argument("--dir", default="_diag/tone")
    ap.add_argument("--seeds", default="0,1,2,3")
    ap.add_argument("--rand", type=int, default=50, help="무작위 층 장수")
    ap.add_argument("--seed", type=int, default=20260920, help="추첨 시드")
    ap.add_argument("--out", default="rf_label_queue.json")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]

    dev = set(json.loads((HERE / "rf_split.json")
                         .read_text(encoding="utf-8"))["dev"])

    votes = {}
    for s in seeds:
        for r in rows(HERE / a.dir / f"roboflow_{a.arm}_s{s}.jsonl"):
            if r["id"] not in dev:
                continue
            c = classify(r)
            if c:
                votes.setdefault(r["id"], []).append(c)

    fail = sorted(i for i, v in votes.items()
                  if sum(x == "일부만" for x in v) >= 2)
    rest = sorted(i for i in votes if i not in set(fail))
    rng = random.Random(a.seed)
    rand = rng.sample(rest, min(a.rand, len(rest)))

    items = ([{"id": i, "stratum": "fail"} for i in fail]
             + [{"id": i, "stratum": "rand"} for i in sorted(rand)])
    # 층이 화면에서 섞이도록 한 번 흔든다. 실패만 연달아 그리면 사람이
    # "이건 실패한 장이구나" 하고 손이 달라진다.
    rng.shuffle(items)

    q = {"items": items,
         "arm": a.arm, "seeds": seeds, "pick_seed": a.seed,
         "note": (f"개발 586 에서 {len(items)}장 — 일부만 {len(fail)} · "
                  f"무작위 {len(rand)}. 우리 규약(숫자 칸 + 사방 "
                  f"0.10x숫자높이)으로 그린다. 측정 전용, 학습 금지.")}
    p = HERE / a.out
    p.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"일부만(2시드 이상) {len(fail)}장 · 무작위 {len(rand)}장 "
          f"= 합계 {len(items)}장")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
