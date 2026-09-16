---
status: active
version_context: "sugarScan · 2026-09-15"
tags: [configuration, tooling, pattern]
aliases: [분기하는 값만 고르게 한다, 열거값은 드롭다운으로,
  스키마를 소비 코드 옆에, enumerate branches]
created: 2026-09-15
confidence: 4
---
# 코드가 분기하는 값의 목록을 소비하는 코드 옆에 두고, 거기서만 고르게 한다

설정값이 자유 입력이면 오타가 **에러가 아니라 옛 동작**으로 떨어진다.
`pos="top-left"` 를 적었는데 분기가 `below` 밖에 없으면 조용히 아래에
그려진다. 고를 수 있는 값을 코드가 아는 값으로 제한하면 이 길이 막힌다.

## The Rule

1. 분기하는 값을 **한 곳에 모아 적는다.** 그 파일은 분기하는 코드 옆이다 —
   멀어지면 갈라진다.
2. 편집 도구는 그 목록에서만 고르게 한다(드롭다운·칩).
3. 새 분기를 만들 때 목록도 같이 고친다. 같은 커밋에서.
4. 값의 **뜻도 거기 적는다.** 설명이 도구 쪽에 있으면 코드가 바뀔 때 같이
   안 바뀐다.

```python
# synth_schema.py — 렌더러가 실제로 분기하는 값 그대로
TIME_POS = ["below-left", "below-right", "below-center", "row-bottom",
            "top-left", "top-right", "column"]
UNIT_POS = ["below-right", "below", "above-right"]   # 같은 줄 자리는 뺐다
```

## Why it works

- 고를 수 없는 값은 선언될 수 없다 — [[declaration-not-read-by-the-consumer]]
  의 주된 입구가 막힌다.
- 목록 자체가 **문서**가 된다. "이 기기는 어디에 놓을 수 있나" 가 코드를
  읽지 않고 답해진다.
- 렌더러가 `assert` 로 막는 값(sugarScan 의 `unit` 같은 줄 자리)을 목록에서
  빼 두면, 사람이 그 값을 골라 죽는 일이 없다.

## Trade-offs

- 목록과 분기가 **두 곳**이 된다. 같은 커밋에서 고치는 규율이 없으면 이것도
  갈라진다. 그래서 파일을 옆에 둔다(다른 저장소·다른 언어로 보내지 않는다).
- 실험적으로 새 값을 시험하기 번거로워진다 — 그때는 분기를 먼저 만든다.
  그게 올바른 순서다.

## Anti-Pattern

[[declaration-not-read-by-the-consumer]] — 선언은 있는데 읽는 코드가 없다.

## Related
- [[declaration-not-read-by-the-consumer]]
- [[declare-what-the-human-knows]]
- [[wire-schema-evolution]]

## Grounding (References)
- `doc/raw/2026-09-15.md` Case 3 — `hash:b9aa317`
- `assets_dev/train/synth_schema.py`
