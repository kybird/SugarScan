---
status: active
version_context: "sugarScan lib/data/sync"
tags: [sync, anti-pattern]
aliases: [독행, 배치 단위 관용, 행 하나가 전체를 막음]
created: 2026-09-02
confidence: 5
---
# 행 하나가 파이프라인 전체를 막는 것

관용의 단위가 **행이 아니라 배치**인 것. 한 행의 해석 실패가 배치 전체의 실패로 승격된다.

## 실패 모드

`ReadingDto.fromJson` 이 던지면 `_pull` 이 통째로 실패하고 `syncOnce` 는 `failed` 를 돌려주며 **커서가 전혀 전진하지 않는다.** 그 행이 고쳐질 때까지 pull 전체가 죽는다. push 는 계속 되므로 사용자는 "동기화가 되고 있다"고 믿는다.

가장 현실적인 트리거는 **버전 차이**다. 새 앱이 모르는 enum wireName 을 쓰는 순간 구버전 앱은 영원히 받지 못한다. 스키마가 하나뿐인 동안에는 절대 안 터지므로 **출시 전에는 관측이 불가능하다.**

## 파생 함정 (이쪽이 더 위험하다)

행을 버리기 시작하면 **페이지 계산이 조용히 틀어진다.**

- 버린 행을 뺀 수로 "다음 페이지가 있나"를 판정 → 마지막 페이지로 오판 → **뒷 페이지를 통째로 놓친다**
- 버린 행을 뺀 수로 offset 을 밀기 → 행이 새거나 겹친다
- 버린 행의 `updated_at` 을 안 보면 → 커서가 그 행을 못 넘어가 **제자리를 돈다**

## 점검 체크리스트

- [ ] 역직렬화가 행 단위로 감싸져 있는가
- [ ] 페이지 경계 판정과 offset 이 **서버가 돌려준 행 수** 기준인가
- [ ] 버린 행의 커서 기준값(`updated_at`)을 따로 읽는가
- [ ] 버린 개수가 보고에 실리는가
- [ ] 사용자에게 예외 원문이 노출되지 않는가

## 올바른 대안

[[row-level-decode-tolerance]] + [[cursor-holdback-for-skipped-rows]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-10` (`hash:d7042da`)
- `test/data/sync_engine_test.dart` 그룹 '해석 못 한 행'
