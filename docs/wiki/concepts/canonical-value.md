---
status: active
version_context: "sugarScan lib/domain · lib/data"
tags: [data, concept]
aliases: [정본, single-source-of-truth, value_mgdl, valueMgdl, enteredValue, enteredUnit, valueIn, GlucoseReading]
created: 2026-09-02
confidence: 5
---
# Canonical Value

한 사실을 두 군데에 적으면 언젠가 갈라진다. 이 앱에서 갈라짐이 가장 비싼 곳은 혈당값이다 — 화면은 `enteredValue` 를 보여 주고 통계·동기화·헬스 연동은 `valueMgdl` 을 쓴다.

## First Principles

정본은 "둘 중 하나가 맞다"가 아니라 **"하나만 계산의 근거가 된다"**는 규칙이다. 파생값은 정본에서 항상 다시 계산되어야 하고, 정본이 바뀔 수 있는 모든 경로가 그 재계산을 지나야 한다.

경로가 하나라도 새면 그 기록은 **두 숫자를 갖는 기록**이 된다. 화면과 통계가 다른 값을 가리키고, 사용자는 어느 쪽이 맞는지 알 방법이 없다.

## Details

- `valueMgdl` 이 정본, `enteredUnit`/`enteredValue` 는 왕복 오차를 막기 위한 원본 보존이다.
- 표시할 때는 `valueIn(unit)` 이 입력 단위와 같으면 원본을 그대로 돌려준다 — 그래서 **정본만 갱신하고 원본을 안 고치면 화면이 옛 값을 보여 준다.** 반대도 마찬가지다.
- UTC 가 시각의 정본이고, 태깅·일별 집계는 `measuredAtLocalWallClock` 기준이다.
- **부분 수정 API 는 정본 재계산의 구멍이 된다.** `update(value:)` 만 부르는 호출부가 하나라도 생기면 그 순간 갈라진다 → [[partial-update-desyncs-canonical]]

## Related

- Patterns: [[contract-boundary-equals-method-boundary]]
- Anti-Patterns: [[partial-update-desyncs-canonical]], [[tolerance-without-preservation]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-9` (`hash:5ed3f06`) — `update(value:)` 만 부르면 정본이 안 따라오던 것
- `test/data/glucose_repository_edit_test.dart` 그룹 '정본 일관성'
- `CLAUDE.md` — "UTC 가 정본이고 `value_mgdl` 이 정본이다"
