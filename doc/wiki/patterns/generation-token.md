---
status: active
version_context: "sugarScan webtool.html · lib/ocr"
tags: [concurrency, pattern]
aliases: [세대 토큰, 세션 토큰, stale-response-guard, lb.gen, _session, GlucoseScanner.offer, show()]
created: 2026-09-02
confidence: 5
---
# Generation Token

비동기 작업을 시작할 때 세대 번호를 찍고, 결과를 반영하기 전에 **그 세대가 아직 유효한지** 확인한다. 유효하지 않으면 결과를 버린다.

## The Rule

```js
async function show(idx) {
  const gen = ++lb.gen;          // 이 호출의 세대
  const info = await api(url);
  if (gen !== lb.gen) return;    // 그 사이 다른 장으로 넘어갔다
  img.onload = () => { if (gen !== lb.gen) return; applyImage(img, id, gen); };
}
```

```dart
final session = _session;                       // start()/stop() 마다 ++
final result = await _throttler.run(...);
if (session != _session) return _last;          // 늦게 온 프레임은 버린다
```

## Why it works

`await` 하나마다 "그 사이에 무엇이든 일어날 수 있는" 구멍이 생긴다. 사용자는 응답을 기다리는 동안 다음 장으로 넘어가고, 스캐너는 단위를 바꾼다. 늦게 도착한 결과가 **새 상태 위에 옛 맥락을 덮는 것**이 이 구멍의 유일한 실패 모드이므로, 맥락에 번호를 붙여 비교하면 전부 막힌다.

## Trade-offs

- 버려지는 작업이 생긴다 — 12MP 디코드 한 번이 낭비될 수 있다. 대안(취소 가능한 작업)은 훨씬 복잡하고, 이 도메인에서는 다음 프레임/다음 장이 곧 온다.
- **세대 토큰은 결과 반영만 막는다. 동시 실행은 못 막는다.** 엔진이 재진입 불가라면 잠금이 따로 필요하다 → [[reset-clears-in-flight-lock]]

## Anti-Pattern

[[stale-client-writes]]

## Related

- Concepts: [[coordinate-frame]]
- Patterns: [[frame-provenance-binding]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-6` — 라벨러 `lb.gen` (연속 `show()` 5회에도 프레임 일치 유지 실측)
- `doc/raw/2026-09-02.md#case-9` — `GlucoseScanner._session`
- `test/ocr/glucose_scanner_contract_test.dart` — 'stop 뒤에 돌아온 프레임은 확정하지 않는다'
