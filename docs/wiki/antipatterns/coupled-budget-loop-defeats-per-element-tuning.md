---
status: active
version_context: "sugarScan · 2026-09-12"
tags: [synthesis, generator, anti-pattern]
aliases: [총량 제약 루프, 확률만 조정, 밀도 채움 회귀, coupled budget loop, 풍선 효과]
created: 2026-09-12
confidence: 5
---
# 총량 제약 루프에서 요소별 확률만 조정한다

"목표치에 닿을 때까지 뽑는다"는 루프에서는 요소들의 출현 확률이 **독립이 아니다.**
한 요소의 확률을 낮추면 루프가 남은 후보를 더 많이 뽑아 총량을 채운다. 그래서
결함 하나를 고치면 고치지 않은 자리가 무너진다 — 풍선을 누르는 것과 같다.

## 실패 양상

합성 패널 렌더러의 밀도 채움 루프는 목표 엣지 밀도에 닿을 때까지 요소를 뽑아
배치한다. 결함 다섯을 고치자 두 번 연속 회귀가 났다.

| 수정 | 의도 | 실제로 일어난 일 |
|---|---|---|
| 텍스트 채움을 근거 있는 후보로 제한 | 지어낸 문자열 제거 | 후보가 2개로 줄어 **`mem` 이 12장 중 11장** |
| 밀도를 도트 시간줄로 채우게 변경 | 텍스트 반복 완화 | **한 화면에 도트줄 서너 개** |

둘 다 "확률을 낮췄다 / 다른 쪽으로 돌렸다"였고, 총량 제약은 그대로였다.

## 왜 생기는가

결함을 **요소 단위**로 보는데 결합은 **루프 단위**에 있다. 코드를 읽으면
`if kind < 0.62: ... elif kind < 0.70: ...` 처럼 확률 분기만 보여서
독립처럼 읽힌다. 결합은 바깥 `for` 와 종료 조건(`d >= fill_target`)에 있다.

## 고치는 방법

**확률은 상한을 대신하지 못한다.** 총량 제약이 있는 루프에서는 요소별
**개수 상한**을 따로 둔다.

```python
dot_rows = 0
for attempt in range(48):
    if ... d >= fill_target: break        # 총량 제약
    if kind < 0.62 and dot_rows < 2:      # ← 개수 상한
        ...
    elif kind < 0.70:                     # 텍스트 채움 30% → 8%
        fresh = [t for t in filler_pool if t not in used_texts]
```

후보 수가 적은 부류는 확률을 낮춰도 **뽑히면 반드시 같은 것**이 나온다.
후보가 적을수록 상한이 더 필요하다.

## 예방 체크리스트

- [ ] 루프에 총량 종료 조건이 있는가? 있으면 요소 확률은 독립이 아니다
- [ ] 확률을 낮춘 요소가 있으면 **어디로 흘러갔는지** 확인한다
- [ ] 후보 풀이 3개 미만인 부류에는 개수 상한을 둔다
- [ ] 한 자리를 고칠 때마다 **산출물을 다시 본다.** 이 저장소에서는
      12장 montage — 눈검 없이 다섯을 한 번에 고쳤으면 회귀가 학습에 들어갔다

## Related

- [[degradation-past-legibility]] — 같은 렌더러의 다른 상한 문제
- [[string-identity-for-label-class]] — 같은 루프에서 나온 중복 검사 결함
- [[sampled-uniformity-as-proof]]

## Grounding (References)

- `doc/raw/2026-09-12.md#case-8`
- `hash:7bb19a9` · `_diag/panel_rebuild/montage_fix_12.png` ~ `montage_fix4_12.png`
