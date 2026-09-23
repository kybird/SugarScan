# 지터 증강 판정 자 — 카드 '리더 지터 증강 학습으로 상자 오차에 강인해진다'.
#
# 비교: B 팔(예측 상자 학습, §27) vs J 팔(GT 상자 + --jitter 0.2 학습).
# 같은 VE 1000장 · 같은 평가 상자원(gt/pred/tepred)의 ok 벡터를 이미지 짝으로
# 붓스트랩 4000회. 사전등록 판정(카드 Note — 결과를 보고 고치지 않는다):
#   (1) J_gt >= 98.0% — 못 지키면 기각(천장을 깎고 강인해진 척)
#   (2) J_tepred − B_tepred 의 95% CI (기준값 96.90%)
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
RD = HERE / "_diag" / "reader_dump"
SRCS = ("gt", "pred", "tepred")
B = 4000


def okvec(p):
    rows = [json.loads(l) for l in
            Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
    return {r["file_name"]: r["ok"] for r in rows}


def boot(a, b):
    d = [b[f] - a[f] for f in a]
    rng = random.Random(20260922)
    n = len(d)
    boots = sorted(sum(d[i] for i in (rng.randrange(n) for _ in range(n))) / n
                   for _ in range(B))
    return (sum(d) / n * 100,
            boots[int(0.025 * B)] * 100, boots[int(0.975 * B) - 1] * 100)


def main() -> int:
    data = {}
    for arm in ("B", "J"):
        for s in SRCS:
            p = RD / f"VE_{arm}_{s}.jsonl"
            if not p.exists():
                raise SystemExit(f"덤프가 없다: {p} — reader_dump 를 먼저")
            data[(arm, s)] = okvec(p)

    print("지터 증강 — VE 1,000 완전일치 %")
    print(f"  {'':10}{'GT 상자':>10}{'atone 상자':>12}{'tone2te 상자':>14}")
    for arm in ("B", "J"):
        print(f"  {arm + ' 팔':10}"
              f"{100*sum(data[(arm,'gt')].values())/1000:>9.2f}%"
              f"{100*sum(data[(arm,'pred')].values())/1000:>11.2f}%"
              f"{100*sum(data[(arm,'tepred')].values())/1000:>13.2f}%")

    print("\n짝비교 B → J (이미지 붓스트랩 4000회, 95% CI)")
    for s in SRCS:
        diff, lo, hi = boot(data[("B", s)], data[("J", s)])
        print(f"  {s:7}Δ {diff:+6.2f}pt  CI [{lo:+.2f}, {hi:+.2f}]")

    jgt = 100 * sum(data[("J", "gt")].values()) / 1000
    print(f"\n[사전등록 판정]")
    print(f"  (1) J_gt {jgt:.2f}% — 기준 ≥98.0: "
          f"{'충족' if jgt >= 98.0 else '기각(천장 붕괴)'}")
    d, lo, hi = boot(data[("B", "tepred")], data[("J", "tepred")])
    if lo > 0:
        print(f"  (2) 배포 조건 유의 상승 Δ{d:+.2f}pt [{lo:+.2f}, {hi:+.2f}]")
    elif hi < 0:
        print(f"  (2) 배포 조건 유의 하락 Δ{d:+.2f}pt [{lo:+.2f}, {hi:+.2f}]")
    else:
        print(f"  (2) 배포 조건 유의차 없음 Δ{d:+.2f}pt [{lo:+.2f}, {hi:+.2f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
