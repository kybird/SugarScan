---
status: active
version_context: "sugarScan lib/app/providers.dart"
tags: [ux, anti-pattern]
aliases: [대기 n건 오표시, 큐 행 세기]
created: 2026-09-02
confidence: 5
---
# 큐 행 수를 사용자에게 그대로 보여 주는 것

아웃박스는 변경마다 행을 쌓지만, 서버로는 **현재 상태 한 번**만 간다. 행을 세면 한 기록을 세 번 고친 사용자에게 "대기 3건"이 보인다.

## 실패 모드

- 실제로 올라가는 것은 1건인데 3건으로 보인다.
- 시도 한도에 닿아 **멈춘** 행까지 함께 세면 `SyncStatusBlocked` 와 숫자가 겹쳐, 같은 것을 두 번 센다.
- 한도 값이 엔진과 표시에서 갈리면 화면이 **이미 멈춘 항목을 아직 올라가는 중인 것처럼** 센다.

## 점검 체크리스트

- [ ] 사용자에게 보이는 개수가 **기록(엔티티)** 단위인가
- [ ] 이미 멈춘(blocked) 항목이 대기 수에서 빠졌는가
- [ ] 한도 같은 임계값을 엔진과 표시가 **같은 출처**에서 읽는가
- [ ] 개수만 필요한 화면이 엔진 전체를 만들지 않는가

## 올바른 대안

```dart
final count = db.syncOutboxRows.entityId.count(distinct: true);
final query = db.selectOnly(db.syncOutboxRows)
  ..addColumns([count])
  ..where(db.syncOutboxRows.attempts.isSmallerThanValue(maxAttempts));
```
임계값은 `syncMaxAttemptsProvider` 하나에서 엔진과 표시가 함께 읽는다.

## Grounding (References)

- `doc/raw/2026-09-02.md#case-10` (`hash:d7042da`)
- `test/app/pending_sync_count_test.dart`
