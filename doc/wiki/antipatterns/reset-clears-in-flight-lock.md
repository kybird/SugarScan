---
status: active
version_context: "sugarScan lib/ocr/src/pipeline"
tags: [concurrency, anti-pattern]
aliases: [reset 이 잠금을 푸는 것, _busy = false, FrameThrottler, frame_throttler.dart, _busy, reset(), isBusy]
created: 2026-09-02
confidence: 5
---
# reset() 이 진행 중인 작업의 잠금을 푸는 것

```dart
void reset() {
  _busy = false;   // ← 아직 돌고 있는 작업이 있다
  _dropped = 0;
  _processed = 0;
}
```

## 실패 모드

`reset()` 이 "전부 초기화"로 읽혀 잠금까지 내린다. 그러면 아직 돌고 있는 추론과 새 추론이 **겹쳐 돈다.** 제품이 "엔진이 재진입 가능한가"에 의존하게 되는데, TFLite 인터프리터처럼 아닌 것도 있다.

지금 안 터지는 이유는 엔진이 우연히 재진입 가능하기 때문이다. 엔진을 바꾸는 순간 터진다.

**세대 토큰으로는 못 막는다.** 세대 토큰은 *결과 반영*을 막지 *동시 실행*을 막지 않는다 — 별개 층이다.

## 점검 체크리스트

- [ ] `reset()`/`clear()` 가 통계·상태만 되돌리는가, 잠금까지 건드리는가
- [ ] 잠금은 그 작업 자신이 `finally` 에서 푸는가
- [ ] 스캔 재시작 직후 몇 프레임이 버려지는 것을 허용할 수 있는가 (허용해야 한다)

## 올바른 대안

`reset()` 은 통계만 되돌린다. 잠금은 작업이 스스로 푼다.

## Related

- Patterns: [[generation-token]], [[contract-boundary-equals-method-boundary]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-9` (`hash:d7042da`)
- `test/ocr/frame_throttler_test.dart` — 'reset 은 진행 중인 작업의 잠금을 풀지 않는다'
