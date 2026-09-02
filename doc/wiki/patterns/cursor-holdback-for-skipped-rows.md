---
status: active
version_context: "sugarScan lib/data/sync/sync_engine.dart"
tags: [sync, pattern]
aliases: [커서 홀드백, delta cursor, SyncCursorStore, _pull, _apply, updated_at, skippedFrom]
created: 2026-09-02
confidence: 5
---
# Cursor Holdback for Skipped Rows

델타 커서를 어디까지 미느냐는 **왜 건너뛰었는지에 따라 정반대**다.

## The Rule

| 건너뛴 이유 | 커서 | 이유 |
|---|---|---|
| 해석하지 못했다 | **넘긴다** | 다시 받아도 또 못 읽는다. 붙잡으면 그 자리에서 제자리를 돈다 |
| 로컬이 `pending` 이라 덮지 않았다 | **앞에 세운다** | 나중에 다시 받아야 한다 |

```dart
var next = newest;                                        // 못 읽은 행: 넘긴다
if (heldBack != null && heldBack.isBefore(next)) next = heldBack;  // pending: 앞에
if (next != null) await _cursor.write(userId, next);
```

## Why it works

`pending` 행을 건너뛰는 것 자체는 옳다(서버 시계와 단말 시계를 크기 비교하는 LWW 를 피하는 설계). 문제는 그 뒤다 — 보통은 다음 push 가 서버 `updated_at` 을 올려 자연히 다시 받지만, **그 push 가 시도 한도에 닿아 막히면** 서버 쪽 변경은 영영 다시 오지 않는다. 조용한 분기다.

커서가 `gte` 이므로 앞에 세워 두면 다음 회차에 그 행부터 다시 받는다. 적용은 멱등이라 다시 받아도 결과가 같다.

## Trade-offs

- pending 이 오래 남으면 매 회차 같은 지점부터 다시 받는다. 진행은 계속되고(뒤 페이지는 적용됨) 비용은 재요청 한 번 — 조용한 분기보다 훨씬 싸다.

## Anti-Pattern

커서를 "이 배치에서 본 가장 큰 `updated_at`" 하나로만 미는 것.

## Related

- Concepts: [[wire-schema-evolution]]
- Patterns: [[row-level-decode-tolerance]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-10` (`hash:d7042da`)
- `test/data/sync_engine_test.dart` — 'pending 때문에 건너뛴 행 앞에 커서를 세운다'
- `CLAUDE.md` — "커서는 `gt` 가 아니라 `gte`"
