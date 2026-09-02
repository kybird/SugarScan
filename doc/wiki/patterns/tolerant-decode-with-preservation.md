---
status: draft
version_context: "sugarScan lib/domain/models · lib/data/remote"
tags: [sync, pattern]
aliases: [관용 디코드, unknown 보존, additive-only, fromWireName, orElse, MeasurementTag, ReadingSource, GlucoseUnit]
created: 2026-09-02
confidence: 3
---
# Tolerant Decode with Preservation

모르는 값을 만나면 **관용하되 보존한다.** 기본값으로 치환하고 그대로 되돌려 쓰면, 관용이 곧 데이터 파괴가 된다.

## The Rule

1. enum 은 `unknown(원문)` 변형으로 디코드한다 — 예외도, 조용한 치환도 아니다.
2. 표시할 때는 중립 라벨로 떨어진다.
3. **직렬화할 때는 받은 원문을 그대로 돌려보낸다.**
4. 추측이 값의 **의미를 뒤집는** 필드는 예외다(→ 단위). 그런 필드는 관용 대신 **행을 건너뛴다**.
5. 스키마 변경은 덧붙이기만. 이름 변경·용도 전용·타입 변경 금지.

## Why it works

관용의 목적은 "옛 클라이언트가 살아남는 것"이다. 하지만 살아남은 옛 클라이언트가 **모르는 값을 기본값으로 덮어 서버에 올리면** 새 클라이언트의 데이터가 사라진다. 살아남는 것과 해를 끼치지 않는 것은 다른 요구다.

## Trade-offs

- 도메인 enum 이 sealed class 로 무거워지고, UI 가 "모르는 값" 표시를 가져야 한다(6개 언어).
- 지금은 앱 버전이 하나뿐이라 발생률 0. **버전이 둘 이상 도는 시점 전에** 넣어야 하고, 그 뒤에는 늦다 — 이미 배포된 클라이언트를 고칠 수 없기 때문이다.

## Anti-Pattern

[[tolerance-without-preservation]]

## Related

- Concepts: [[wire-schema-evolution]], [[canonical-value]]
- Patterns: [[row-level-decode-tolerance]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-10` — 세 enum 의 정책이 제각각인 것을 발견
- `lib/domain/models/measurement_tag.dart` (`orElse: random`), `reading_source.dart` (`orElse: manual`), `glucose_unit.dart` (던짐)
