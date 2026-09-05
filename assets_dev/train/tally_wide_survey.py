# 가로 화면 표본 조사 집계 — 사람이 센 번호로 비율과 신뢰구간을 낸다.
#
# 사용:
#   python tally_wide_survey.py 3 17 22 41 ...
#   python tally_wide_survey.py --file counts.txt      (한 줄에 하나 또는 공백 구분)
#
# 왜 신뢰구간까지 내는가: 200장 표본에서 "11%" 와 "6%" 는 겹칠 수 있다.
# 구간을 안 보면 "GM 이 1.2% 만 가로로 잡는다"와 비교할 때 과대·과소 판단을
# 하게 된다.
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SURVEY = HERE / "_diag" / "wide_survey"


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, c - h), min(1.0, c + h)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("nums", nargs="*", type=int, help="가로로 보인 번호")
    ap.add_argument("--file", help="번호가 적힌 텍스트 파일")
    ap.add_argument("--dir", default=None,
                    help="대지 폴더 이름 (예: wide_all). 기본 wide_survey")
    args = ap.parse_args()

    survey = HERE / "_diag" / args.dir if args.dir else DEFAULT_SURVEY

    nums = list(args.nums)
    if args.file:
        nums += [int(t) for t in Path(args.file).read_text().split()]
    nums = sorted(set(nums))

    index = json.loads((survey / "index.json").read_text(encoding="utf-8"))
    SURVEY = survey
    n = len(index)
    by_no = {r["no"]: r["id"] for r in index}
    bad = [x for x in nums if x not in by_no]
    if bad:
        print(f"범위 밖 번호 무시: {bad}")
        nums = [x for x in nums if x in by_no]

    k = len(nums)
    lo, hi = wilson(k, n)
    full = n >= 2500          # 전수면 신뢰구간이 필요 없다 — 그게 곧 답이다
    print(f"{'전수' if full else '표본'} {n}장 중 가로 {k}장 = {100*k/n:.1f}%")
    if full:
        print("  (전수 조사이므로 신뢰구간 없음 — 이 값이 곧 모집단 비율이다)")
    else:
        print(f"95% 신뢰구간: {100*lo:.1f}% ~ {100*hi:.1f}%")
        print(f"전체 2,512장 환산: 약 {int(2512*k/n)}장 "
              f"({int(2512*lo)}~{int(2512*hi)}장)")
    print()
    print("비교 대상:")
    print(f"  GM ft3 가 w/h>1.5 로 잡는 장: 30/2497 = 1.2%")
    print(f"  GM ft3 가 w/h>1.2 로 잡는 장: 46/2497 = 1.8%")
    if k:
        print(f"\n  → 사람이 본 비율이 GM 보다 {100*k/n/1.2:.1f}배 높다면,")
        print("     그 차이가 곧 '검출기가 놓치거나 접어서 잡는 양' 이다.")
        out = SURVEY / "wide_ids.json"
        out.write_text(json.dumps([by_no[x] for x in nums], ensure_ascii=False,
                                  indent=1), encoding="utf-8")
        print(f"\n  가로로 표시된 장의 id 를 저장했다 → {out.name}")
        print("  (증강·재라벨링 대상 선정에 쓸 수 있다)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
