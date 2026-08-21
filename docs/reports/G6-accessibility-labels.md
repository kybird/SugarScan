# G6 — 접근성 라벨 (스크린리더)

- 브랜치: `glm/G6-accessibility-labels`
- 커밋: `cc4d32a` (코드) + 보고서 커밋 (이 파일)
- 상태: 완료

## 무엇을 했나

- `lib/features/shared/reading_tile.dart` — 타일 전체를 감싼 `Semantics(label:)`
  추가. 라벨은 "값 단위, 시각, 태그, 출처" 순서의 한 문장. 안쪽 값·단위 Text
  와 시각·태그·출처 부제 Text 는 `excludeSemantics` 로 중복 낭독에서 제외.
  ListTile 의 탭 동작은 그대로 읽힌다.
- `lib/features/stats/stats_screen.dart` — `_SummaryCard`(평균·건수·최저·최고·
  편차)와 `_InRangeCard`(범위 안 비율·대상 범위·건수 기준 단서)에 카드 전체
  라벨을 붙이고 내부 Text 를 제외.
- `test/features/reading_tile_test.dart` — 의미론 테스트 추가(라벨 문장 전체가
  정확히 잡히는지, 메모도 낭독에 포함되는지).
- `test/features/stats_screen_test.dart` — 요약 카드 두 개의 라벨 확인 테스트 추가.

## 왜 그렇게 했나

- **l10n 키를 새로 만들지 않고 기존 현지화 조각으로 라벨을 구성했다.** 라벨에
  들어가는 문구(값 기호·시각·태그·출처·"평균"·"n건"·"목표 범위 안" 등)는 전부
  이미 en/ko 로 존재하는 l10n 출력이라 하드코딩이 없다. 새 키를 만들면 같은
  문장이 두 벌로 늘어나 G8 번역과 의료 문구 검토 대상도 그만큼 늘어난다.
- 라벨에 판정 단어를 넣지 않았다. "목표 범위 안" 같은 서술만 쓰고(§2.4),
  `_InRangeCard` 의 "건수 기준" 단서(`statsInRangeNote`)는 임상적으로 중요한
  문구라 낭독에서도 빼지 않았다.
- 메모는 라벨 문자열에 직접 넣지 않았는데, 확인해 보니 같은 의미론 노드로
  자동 병합되어 라벨에 이어서 읽힌다(선행 라벨과 개행 구분). 낭독 내용과 화면
  내용이 같아지므로 이 동작을 그대로 쓰고 테스트로 고정했다.
- 차트(`_TrendChart`)는 지시대로 건드리지 않았다.

## 검증

flutter analyze  → No issues found! (ran in 3.8s)
flutter test     → All tests passed! (331 tests)

## 건드리지 않고 남긴 것

- `_TrendChart`(추이 차트)와 `_ByTagList`(태그별 평균), `SegmentedButton` —
  지시 범위가 "요약 카드"라서 제외했다.
- 세그먼트 버튼·앱바 등 나머지 화면 요소의 라벨 — 범위 밖.

## 막힌 것

없음 — 초반에 메모 Text 의 의미론 노드를 `find.bySemanticsLabel` 정확 일치로
찾지 못해 막혔지만, 의미론 트리를 덤프해 보니 노드 병합이 원인이었다. 실제
동작(라벨에 이어 읽힘)이 의도에 부합해 테스트를 그에 맞춰 고쳤다.
