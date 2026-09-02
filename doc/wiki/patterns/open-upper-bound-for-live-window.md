---
status: active
version_context: "Drift 2.x · flutter_riverpod 3.x"
tags: [data, pattern]
aliases: [열린 상한, 기간 질의, statsReadingsProvider, watchBetween, refreshStatsProvider]
created: 2026-09-02
confidence: 5
---
# Open Upper Bound for Live Window

"최근 N일" 같은 살아 있는 기간 질의는 **위쪽 경계를 열어 둔다.** 상한에 "지금"을 넣지 않는다.

## The Rule

```dart
return repo.watchBetween(
  now.subtract(Duration(days: days)),
  now.add(const Duration(days: 365)),   // 상한을 열어 둔다
);
```

하한은 굳어도 데이터가 사라지지 않는다(범위가 넓어지는 방향). 그래도 화면 진입 시 다시 계산해 자정을 넘겨도 창이 늘어나지 않게 한다.

## Why it works

상한을 `now` 로 굳히면 **그 뒤에 저장한 기록이 전부 범위 밖**이다. 게다가 단말 시계가 살짝 앞선 기록이나 사용자가 미래 시각으로 넣은 기록도 함께 사라진다. 상한을 여는 비용은 0 이고, 얻는 것은 "방금 잰 값이 통계에 나온다"이다.

## Trade-offs

- 미래 시각 기록이 통계에 섞인다. 혈당 기록에서는 그게 옳다 — 사용자가 넣은 것을 안 보여 주는 쪽이 더 나쁘다.

## Anti-Pattern

[[frozen-now-in-live-query]]

## Related

- Concepts: [[live-query]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-8` (`hash:5ed3f06`)
- `test/app/stats_window_test.dart`
