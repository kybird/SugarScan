---
status: active
version_context: "sugarScan · 2026-09-15"
tags: [layout, rendering, pattern]
aliases: [최댓값으로 자리를 잡는다, 가변 길이 예약, 칸은 고정 값은 오른쪽부터,
  reserve by widest]
created: 2026-09-15
confidence: 4
---
# 가변 길이 내용의 자리는 **가장 넓은 값**으로 예약하고, 그 안에서 정렬한다

길이가 변하는 내용(날짜 `9-3` ~ `12-25`, 값 `88` ~ `511`)을 **실제 값**으로
예약하면 렌더마다 자리가 움직인다. **어림**으로 예약하면 좁을 때 배치가
실패해 요소가 사라진다. 그 형식이 낼 수 있는 가장 넓은 문자열로 칸을 잡고,
칸 안에서 정렬한다.

## The Rule

1. 형식에서 **최대 폭 문자열**을 만든다(난수를 쓰지 않는다 — 예약이 렌더마다
   흔들리면 예약하는 의미가 없다).
2. 그 폭으로 칸을 잡는다. 칸은 고정이다.
3. 실제 값은 칸 **안에서** 정렬한다. 7-세그 계열은 오른쪽 정렬이 맞다 —
   자릿수가 바뀌어도 오른쪽 끝이 안 움직인다.
4. 예약 폭과 렌더 폭은 **같은 함수**에서 낸다.

```python
_wide = _dot_time_text(rng, fmt_i=0, fmts=[fmt], widest=True)
cell_w = text_width(_wide, h)          # 칸
x = cell_right - text_width(actual, h) # 그 안에서 오른쪽 정렬
```

## Why it works

실물 액정이 그렇게 생겼다 — 셀이 고정이고 값이 오른쪽부터 찬다. 합성이
같은 물리를 따르면 자리 안정성 검사(같은 기기는 같은 칸)가 저절로 통과한다.

균등 분할은 대안이 아니다. sugarScan 에서 하단 행을 3등분했더니 시각(188px)이
칸(168px)보다 넓어 통째로 빠졌다 — [[silent-drop-on-placement-failure]].

## Trade-offs

- 짧은 값에서 칸 안에 여백이 남는다. 실물도 그러므로 결함이 아니다.
- 최대 폭을 잘못 잡으면(형식에 없는 값이 들어오면) 다시 좁아진다. 최대 폭을
  **형식에서 유도**하고 손으로 적지 않는 이유다.

## Anti-Pattern

[[silent-drop-on-placement-failure]] — 예약이 좁아 요소가 조용히 사라진다.

## Related
- [[silent-drop-on-placement-failure]]
- [[duplicated-geometry-implementation]]
- [[device-fixed-to-a-single-point]]

## Grounding (References)
- `doc/raw/2026-09-15.md` Case 6 — `hash:b9aa317`
- `assets_dev/train/synth_panel.py` row-bottom · `synth_profiles.dot_text_width`
