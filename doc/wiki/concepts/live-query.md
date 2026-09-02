---
status: active
version_context: "Drift 2.x · flutter_riverpod 3.x"
tags: [data, concept]
aliases: [살아 있는 질의, Drift watch, 스트림 질의]
created: 2026-09-02
confidence: 5
---
# Live Query

Drift 의 `watch()` 는 테이블이 바뀔 때마다 **처음 만든 SQL 을 그대로 다시 돌린다.** 파라미터를 다시 계산하지 않는다.

## First Principles

"스트림이 살아 있다"와 "질의가 갱신된다"는 다른 말이다. 질의를 만들 때 평가된 값(`DateTime.now()`, 사용자 id, 임계값)은 **그 스트림의 수명 동안 얼어 있다.**

따라서 살아 있는 질의의 경계에 "지금"을 넣으면, 그 뒤에 들어온 데이터는 영원히 범위 밖이다.

## Details

- Riverpod 의 `StreamProvider` 는 `autoDispose` 가 아니면 앱 수명 동안 살아 있다. 의존하는 프로바이더가 바뀌지 않으면 질의는 **한 번도 다시 만들어지지 않는다.**
- 기본값을 쓰는 사용자는 의존값을 바꾸지 않으므로 **가장 흔한 경로가 가장 오래 얼어 있다.**
- 테스트 함정: `StreamProvider` 의 `.future` 는 **구독자가 있어야** 값을 흘린다. `container.listen(...)` 없이 `read(p.future)` 만 하면 영원히 대기한다.

## Related

- Patterns: [[open-upper-bound-for-live-window]]
- Anti-Patterns: [[frozen-now-in-live-query]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-8` (`hash:5ed3f06`)
- `test/app/stats_window_test.dart` — 수정 전 코드에서 실패하는 것을 확인한 회귀 테스트
- `test/app/pending_sync_count_test.dart` — `.future` 함정 주석
