---
status: active
version_context: "sugarScan · 2026-09-12"
tags: [modeling, synthesis, anti-pattern]
aliases: [문자열 동일성, 표기 변형 중복, used_texts, string identity, 라벨 부류]
created: 2026-09-12
confidence: 5
---
# 라벨의 동일성을 문자열 일치로 판정한다

도메인에서 같은 것(같은 annunciator, 같은 표시등)이 **표기 변형** 때문에 문자열로는
달라진다. 중복 검사를 문자열 집합으로 하면 그 둘이 동시에 나온다.

## 실패 양상

합성 패널의 중복 방지가 `used_texts` 라는 문자열 집합이었다.
`"mem" != "memory"` 이므로 중복으로 잡히지 않았고, 한 화면에 `mem` 과 `memory`
가 같이 그려졌다(12장 중 5장). 실기기에서 메모리 표기는 **기기당 한 종류**다.

같은 함정에 걸리는 다른 부류: `M`/`mem`/`memory`, `am`/`AM`/`a.m.`,
`mg/dL`/`mgdL`/`mg/dl`.

## 왜 생기는가

자료구조의 동일성(문자열 일치)이 도메인의 동일성(같은 라벨)의 **대리**로
쓰였다. 대부분의 경우 둘이 일치하기 때문에 오래 버티다가, 변형이 있는 부류
하나에서만 조용히 깨진다. 에러가 나지 않고 **산출물을 봐야만** 보인다.

## 고치는 방법

부류를 명시하고 부류 단위로 소진한다.

```python
_MEM_VARIANTS = {"M", "mem", "memory"}   # 같은 라벨 부류의 표기 변형
...
used_texts |= _MEM_VARIANTS              # 하나를 쓰면 부류 전체 소진
```

근본 해법은 요소를 `(부류, 표기)` 쌍으로 들고 다니며 **부류로 중복을 보고
표기로 렌더링하는** 것이다. 위 사례는 변형 부류가 하나뿐이라 상수 집합으로
막았다 — 범위 밖 확대는 하지 않았다.

## 예방 체크리스트

- [ ] 중복·유일성 검사의 키가 **도메인 식별자**인가, 표시 문자열인가
- [ ] 같은 것을 여러 방식으로 쓸 수 있는 부류가 있는가(대소문자·약어·단위 표기)
- [ ] "기기당 하나" 같은 도메인 제약이 코드 어디에 적혀 있는가 — 없으면
      상수로 적는다
- [ ] 조용히 깨지는 결함이므로 **산출물을 눈으로 본다**

## Related

- [[canonical-value]] — 정본과 표시의 분리
- [[tolerance-without-preservation]] — 표기를 관대하게 받고 원본을 잃는 것
- [[coupled-budget-loop-defeats-per-element-tuning]] — 같은 루프의 다른 결함
- [[count-rows-not-entities]] — 세는 단위가 도메인 단위와 어긋나는 것

## Grounding (References)

- `doc/raw/2026-09-12.md#case-9`
- `hash:7bb19a9` · `_diag/panel_rebuild/montage_fix3_12.png`
