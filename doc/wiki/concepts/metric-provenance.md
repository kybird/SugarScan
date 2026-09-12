---
status: active
version_context: "sugarScan · 2026-09-12"
tags: [process, concept]
aliases: [수치 출처, 지표 출처, 무엇을 잰 값인가, metric provenance, 비교 가능성]
created: 2026-09-12
confidence: 5
---
# 수치의 출처 — 무엇을, 어떤 대상에서, 어떤 자로 쟀는가

숫자는 출처를 달고 다니지 않는다. 표에 옮겨 적히는 순간 맥락이 떨어져 나가고
남는 것은 자릿수뿐이다. 그래서 **모든 인용 가능한 수치에는 세 가지가 붙어
있어야 한다** — 무엇을 잰 값인지, 어떤 대상에서 잰 값인지, 어떤 자로 잰 값인지.

## First Principles

두 수치를 나란히 놓는 행위는 **셋이 같다는 주장**이다. 하나라도 다르면 그
비교는 성립하지 않는다. 그런데 다르다는 사실은 숫자 자체에 나타나지 않으므로,
적어 두지 않으면 사라진다.

## Details

이 저장소에서 세 가지가 각각 무너진 적이 있다.

**무엇을 잰 값인가** — "검출률 99.4%" 는 정확도가 아니라 출력 존재율이었다.
정답 대비 IoU 는 중앙 0.795, 0.9 이상이 7.4% 였다.
→ [[presence-rate-quoted-as-accuracy]]

**어떤 대상에서** — 완전일치 97.06% / 96.67% / 95.52% 는 각각 다른 분할의
다른 홀드아웃에서 나온 값이다. 뺄셈해서 "-1.15pp 잃었다"로 쓴 보고서가 실제로
나왔고, 그 차이는 유의하지도 않았다(p=0.139).
→ [[stale-baseline-quoted-as-current]]

**어떤 자로** — 대리 지표(합성만 학습해 실사진에서 재기)를 품질 지표로 읽었다.
그 지표가 오르는 동안 위험 층이 함께 올랐다.
→ [[proxy-metric-moves-against-the-goal]]

그리고 아예 근거가 없는 수치도 있었다. 보고서 한 줄의 "코퍼스에 HI/LO 318건"
을 확인 없이 인용해 제품 위험을 논했는데, 원 라벨 2,512행의 값은 전부 정수였고
숫자 아닌 값은 0건이었다.

## 실무 규칙

- 수치를 인용하기 전에 **분모와 대상 집합**을 말할 수 있는지 자문한다
- 차이를 pp 로 적으면 **신뢰구간이나 p 값**을 같이 적는다
- 표본이 모델의 학습 데이터와 겹치면 그 사실을 수치 옆에 적는다
- 보고서의 수치는 1차 자료가 아니다. 자기 주장을 강화하는 방향일수록 원본을 본다

## Related

- [[experiment-budget-parity]] — 비교가 성립하려면 무엇이 같아야 하는가
- [[measure-the-premise-not-just-the-claim]] — 전제를 재는 습관
- [[verify-premises-before-executing]]
- [[verification-record-without-subject]] — 검증 기록에 주어가 없는 것

## Grounding (References)

- `doc/raw/2026-09-12.md#case-1` · `#case-3` · `#case-4`
- `doc/raw/2026-09-11.md#case-3`
