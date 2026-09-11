# G10 — 접근성 라벨 나머지 화면 요소

- 브랜치: `glm/G10-accessibility-rest`
- 커밋: 이 보고서와 함께 하나
- 상태: 완료 — 세 곳에 라벨·액션 추가, 한 곳은 조합 불가로 보고만.

## 무엇을 했나

G6 이 남긴 네 대상 중 세 곳을 고치고(화면 코드는 라벨 추가만), 한 곳은
새 l10n 키 없이는 불가능해 보고로 남겼다.

| 대상 | 한 일 | 테스트 |
|---|---|---|
| `stats_screen.dart` `_ByTagList` | 행 전체를 한 문장으로 읽는 `Semantics(label:)` 추가(reading_tile 관용구). 라벨 = "태그, 평균 값 단위" — 행에 보이는 내용 그대로. 안쪽 제목·trailing 은 `excludeSemantics` 로 중복 낭독 제외. | `stats_screen_test` — 뷰포트 아래 목록이라 스크롤 후 라벨 확인 |
| `settings_screen.dart` 단위·목표 범위 라디오 | `RadioGroup` 을 `Semantics(label:)` 로 감싸 그룹 진입 시 섹션 제목이 읽히게. 라벨은 **화면에 보이는 섹션 제목과 같은 문구**(`settingsUnitSection`·`settingsTargetSection`) — 새 키 없음. 섹션 제목 Text 는 `excludeSemantics` 로 두 번 읽히지 않게. | `settings_semantics_test`(신규 파일) — 두 그룹 라벨 확인(목표 범위는 스크롤 후) |
| `history_screen.dart` 스와이프 삭제 | `Dismissible` 자식에 `Semantics(customSemanticsActions:)` 로 "삭제" 액션 노출. 라벨은 스와이프 배경과 같은 `actionDelete`, 실행도 같은 `_delete` — 스크린리더 사용자가 제스처 없이 같은 경로에 접근한다. | `history_screen_test` — 살아 있는 의미론 트리 덤프에서 `customActions` + `Delete` 확인. 실행 경로 `_delete` 는 기존 스와이프 테스트가 같은 함수로 커버 |
| `stats_screen.dart` 기간 `SegmentedButton` | **고치지 않았다** — 아래 "왜" 참조 | — |

`flutter analyze` 무경고, `flutter test` 전체 **390 통과**(387 + 신규 3).

## 왜 그렇게 했나

- **SegmentedButton 보고 사유**: 세그먼트는 네이티브 낭독으로 이미 내용
  그대로("7 days", 탭 n/m, 선택 상태) 읽힌다. 그룹에 덧붙일 라벨로 쓸 수 있는
  **보이는 문구가 화면에 없다** — "라벨은 화면에 보이는 것과 같은 내용" 규칙과
  "새 l10n 키 금지"를 함께 지키는 방법이 없었다. 섹션 제목 텍스트를 추가하면
  그 자체가 화면 변경이라 지시 범위를 넘는다. 필요하면 사람이 키 추가를
  결정해야 한다.
- **스와이프 삭제 액션 검증 방법**: `customSemanticsActions` 는 위젯·노드
  어디에도 게터로 노출되지 않는다. 테스트는 뷰 owner 의 의미론 루트
  (`tester.binding.renderViews.first.owner!.semanticsOwner!`)에서 덤프를 떠
  확인했다 — 스크린리더가 실제로 받는 트리에서 확인하는 셈이다. 실행
  유발(레이블로 콜백 직접 호출)까지는 게터 부재로 검증하지 못했다.
- 낭독문에 판정어는 없다 — 전부 보이는 문구의 조합이다.

## 검증

```text
flutter analyze  → No issues found!
flutter test     → All tests passed! (390 tests)
```

- stats byTag 라벨: `find.bySemanticsLabel(RegExp('Fasting, 100 mg/dL'))`.
- 설정 그룹 라벨: `RegExp('Display unit')` / 스크롤 후 `RegExp('Target range')`.
- 삭제 액션: 의미론 덤프에 `customActions` + `Delete` 실림.

## 건드리지 않고 남긴 것

- `_TrendChart` — 지시서 금지. 그대로.
- SegmentedButton 그룹 라벨(위 사유).

## 막힌 것

없음 — 커스텀 액션의 실행 유발 검증만 게터 부재로 단념(위).
