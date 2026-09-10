# dot·unit 지표의 측정 가능성 감사 — 홀드아웃 GT 분포 집계.
#
# 동기(칸반 「dot·unit 지표 추가」): mmol/L 소수점 오독은 10배 오류를 내는
# 제품 리스크인데, 완전일치율 하나에 묻혀 있다(aggregate-hides-stratified-
# failure). 지표를 추가하려면 측정할 표본이 있어야 한다 — 먼저 세야 한다.
#
# 확인하는 것:
#   1. 전체 라벨(labels.jsonl) 의 reading 형태 — 숫자/소수점/비숫자(HI·LO 등)
#   2. 학습 풀(build_cache_v2 의 isdigit 필터 통과분) 과 홀드아웃의 GT 분포
#   3. 소수점·단위 표본이 존재하는가 — 없으면 dot 지표는 이 코퍼스에서
#      측정 불가다(데이터 확보가 선행 과제).
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATUMO = HERE.parent / "upstream" / "datumo"


def classify(s: str) -> str:
    s = str(s)
    if s.isdigit():
        return "integer"
    # 소수점 포함 숫자
    try:
        float(s.replace(",", "."))
        return "decimal"
    except ValueError:
        return "non_numeric"


def main() -> int:
    labels = {}
    for l in (DATUMO / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            j = json.loads(l)
            labels[j["id"]] = str(j["reading"])
    corr = HERE / "gt_corrections.jsonl"
    if corr.exists():
        for l in corr.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                labels[j["id"]] = str(j["corrected"])

    kinds = Counter(classify(v) for v in labels.values())
    non_numeric = Counter(v for v in labels.values() if classify(v) == "non_numeric")
    print(f"전체 라벨 {len(labels)}: {dict(kinds)}")
    print(f"비숫자 상위: {non_numeric.most_common(8)}")

    cache = np.load(HERE / "data_cache_v2.npz", allow_pickle=True)
    ho = [str(x) for x in cache["real_holdout_ids"]]
    tr = [str(x) for x in cache["real_train_ids"]]
    for name, ids in (("train", tr), ("holdout", ho)):
        vals = [labels.get(i, "?") for i in ids]
        k = Counter(classify(v) for v in vals)
        lens = Counter(len(v) for v in vals)
        ints = [int(v) for v in vals if classify(v) == "integer"]
        print(f"{name} {len(ids)}: {dict(k)} · 자릿수 {dict(sorted(lens.items()))} · "
              f"값 범위 {min(ints)}~{max(ints)}")

    dec = [v for v in labels.values() if classify(v) == "decimal"]
    unit_field = [j for j in (DATUMO / "labels.jsonl")
                  .read_text(encoding="utf-8").splitlines() if "unit" in j]
    print(f"소수점 표본: {len(dec)}건 {dec[:5]}")
    print(f"단위(unit) 필드가 있는 라벨: {len(unit_field)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
