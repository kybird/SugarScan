# G3 — 기록 목록에 메모 표시

- 브랜치: `glm/G3-note-in-list`
- 커밋: `a3e2121` (코드) + 보고서 커밋 (이 파일)
- 상태: 완료

## 무엇을 했나

- `lib/features/shared/reading_tile.dart` — 부제(시각 · 태그 · 출처) 아래에 메모를
  한 줄로 보여 준다. `maxLines: 1`, `TextOverflow.ellipsis`. 스타일은 기존 부제와
  같은 `bodySmall`/`onSurfaceVariant`.
- `test/features/reading_tile_test.dart` — 신규 위젯 테스트. 메모 있음(위치·한 줄
  잘림 확인) / 메모 없음·공백(그리지 않음 + 높이 불변) 두 케이스.

## 왜 그렇게 했나

- 메모가 null 이 아니더라도 공백 문자열이면 그리지 않게 했다. `GlucoseRepository
  .update` 는 빈 문자열을 "지움"으로 정규화하지만, 다른 경로(동기화 pull 등)로
  공백이 내려올 가능까지 막으려면 그리는 쪽에서도 버텨야 한다.
- "메모 없는 기록의 높이가 지금과 같다"는 완료 기준을, 메모 없을 때 부제 Column
  자식이 정확히 1개이고 공백 메모에서도 타일 높이가 변하지 않는 것으로 검증했다.

## 검증

flutter analyze  → No issues found! (ran in 3.8s)
flutter test     → All tests passed! (329 tests)

## 건드리지 않고 남긴 것

- 값·시각·태그·출처의 기존 배치는 그대로다. 메모 줄만 추가했다.
- 메모에 아이콘이나 색을 붙이지 않았다(판정하지 않는 타일이다).

## 막힌 것

없음
