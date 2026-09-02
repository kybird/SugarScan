---
status: active
version_context: "Drift 2.x · flutter_riverpod 3.x"
tags: [data, anti-pattern]
aliases: [굳은 now, 기간 상한 고정, statsReadingsProvider, watchBetween, StreamProvider, DateTime.now(), providers.dart]
created: 2026-09-02
confidence: 5
---
# 살아 있는 질의의 경계를 구독 시점 시각으로 굳히는 것

```dart
final now = DateTime.now();
return repo.watchBetween(now.subtract(Duration(days: days)), now);  // ← 상한이 얼었다
```

## 실패 모드

Drift 는 테이블이 바뀌면 **처음 만든 SQL 을 그대로 다시 돌린다.** 파라미터는 다시 계산되지 않는다. Riverpod `StreamProvider` 는 `autoDispose` 가 아니면 앱 수명 동안 살아 있다.

결과: **통계 화면을 한 번 연 뒤 저장한 기록이 통계에 영원히 나타나지 않는다.** 기본값(14일)을 쓰는 사용자는 의존값을 바꾸지 않으므로 앱을 재시작하기 전까지 갱신되지 않는다 — 가장 흔한 경로가 가장 오래 얼어 있다.

혈당 앱에서 "방금 잰 값이 통계에 안 나온다"는 사용자가 즉시 알아채는 결함이다.

## 점검 체크리스트

- [ ] 스트림 질의의 파라미터에 `DateTime.now()` 나 그 파생값이 들어가는가
- [ ] 그것이 **상한**인가 (상한이면 데이터가 사라진다, 하한이면 범위가 넓어질 뿐)
- [ ] 프로바이더가 `autoDispose` 인가, 아니면 무엇이 바뀌어야 다시 만들어지는가
- [ ] 회귀 테스트가 **수정 전 코드에서 실제로 실패하는지** 확인했는가

## 올바른 대안

[[open-upper-bound-for-live-window]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-8` (`hash:5ed3f06`)
- `test/app/stats_window_test.dart`
