---
status: active
version_context: "sugarScan lib/data/sync"
tags: [sync, pattern]
aliases: [행 단위 관용, poison-row 방어, ReadingPage]
created: 2026-09-02
confidence: 5
---
# Row-Level Decode Tolerance

배치에서 행 하나를 해석하지 못했다고 배치 전체를 실패시키지 않는다. **관용의 단위는 행이다.**

## The Rule

1. 행마다 `try` 로 감싸고, 실패한 행은 **버리고 센다**(`SyncReport.malformed`).
2. **페이지 경계 판정과 offset 은 서버가 돌려준 행 수 기준**이다. 버린 행을 뺀 수로 세면 마지막 페이지로 오판해 **뒷 페이지를 통째로 놓친다.** — 이 함정이 원래 버그보다 위험하다.
3. 못 읽은 행의 `updated_at` 은 **따로 읽어서** 커서 전진에 반영한다. 안 그러면 그 행에서 영원히 제자리를 돈다.
4. 사용자에게는 예외 원문을 보이지 않는다. 로그로만 남긴다.

```dart
class ReadingPage {
  final List<GlucoseReading> readings;
  final int fetchedRows;        // 버린 행 포함 — 페이지 판정의 기준
  final List<String> malformed;
  final DateTime? newestSeen;   // 버린 행의 updated_at 도 본다
}
```

## Why it works

스키마가 하나뿐인 동안에는 절대 안 터지고, **앱 버전이 둘 이상 도는 순간부터만** 터진다. 출시 전에는 관측이 불가능하므로 구조로 막아 두는 수밖에 없다.

## Trade-offs

- 버린 행은 이 클라이언트에서 보이지 않는다. 데이터가 사라진 것은 아니지만(서버에 그대로), **사용자는 그 사실을 모른다.** 알릴지는 앱 버전이 둘 이상 도는 시점의 판단으로 남겨 두었다.
- 인터페이스가 `List` → `ReadingPage` 로 무거워진다. 페이지 판정 기준을 정확히 하려면 피할 수 없다.

## Anti-Pattern

[[poison-row-blocks-pipeline]]

## Related

- Concepts: [[wire-schema-evolution]]
- Patterns: [[cursor-holdback-for-skipped-rows]], [[tolerant-decode-with-preservation]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-10` (`hash:d7042da`)
- `test/data/sync_engine_test.dart` — '버린 행이 페이지 경계 판정을 흐리지 않는다'
