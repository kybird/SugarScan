---
status: active
version_context: "sugarScan lib/data/repositories"
tags: [data, anti-pattern]
aliases: [부분 수정, 정본 미갱신, GlucoseRepository.update, valueMgdl, enteredValue, Value.absent, glucose_repository.dart]
created: 2026-09-02
confidence: 5
---
# 부분 수정이 정본을 따라오지 않는 것

```dart
valueMgdl: value == null || unit == null ? const Value.absent() : Value(unit.toMgdl(value)),
```

`value` 와 `unit` 이 **둘 다** 있을 때만 정본을 갱신한다. 값만 고치면 `enteredValue` 는 바뀌고 `valueMgdl` 은 그대로다.

## 실패 모드

같은 기록이 **두 숫자**를 갖는다. 화면(`valueIn` 이 입력 단위와 같으면 원본을 돌려준다)은 새 값을, 통계·동기화·헬스 연동(정본 `valueMgdl`)은 옛 값을 가리킨다. 어느 쪽이 맞는지 사용자는 알 수 없고, 서버로도 옛 정본이 올라간다.

**지금 당장은 안 터진다** — 유일한 호출부가 둘을 함께 넘기기 때문이다. 그래서 리뷰에서 안 잡힌다. "보통 함께 오는 값"을 계약으로 착각한 전형이다.

## 점검 체크리스트

- [ ] 파생값(정본)을 계산하는 조건이 **모든 입력이 있을 때**로 좁혀져 있지 않은가
- [ ] 빠진 입력을 저장된 행에서 채워 항상 재계산하는가
- [ ] 그 읽기가 같은 트랜잭션 안인가
- [ ] "지금 호출부가 늘 둘 다 넘긴다"에 기대고 있지 않은가

## 올바른 대안

```dart
if (value != null || unit != null) {
  final row = await select(...).getSingleOrNull();
  if (row == null) return;
  mgdl = (unit ?? row.enteredUnit).toMgdl(value ?? row.enteredValue);
}
```

## Related

- Concepts: [[canonical-value]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-9` (`hash:5ed3f06`)
- `test/data/glucose_repository_edit_test.dart` 그룹 '정본 일관성'
