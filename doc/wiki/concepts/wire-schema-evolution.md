---
status: active
version_context: "sugarScan lib/data/remote · supabase/migrations"
tags: [sync, concept]
aliases: [스키마 진화, 버전 공존, forward-compatibility, additive-only-wire-schema, fromWireName, wireName, ReadingDto, MeasurementTag, ReadingSource]
created: 2026-09-02
confidence: 4
---
# Wire Schema Evolution

앱이 출시되는 순간부터 **여러 버전이 동시에 같은 서버를 읽고 쓴다.** 구버전 클라이언트는 이미 사용자 기기에 설치돼 있어 나중에 고칠 수 없다 — 이것이 이 주제의 모든 제약을 만든다.

## First Principles

**마이그레이션 코드로는 이 축을 못 푼다.** 마이그레이션은 "내 로컬 스키마를 앞으로 옮기는" 도구다(Drift 버전 마이그레이션, 서버 SQL 백필). 하지만 여기서 필요한 것은 **이미 배포된 옛 리더가 새 라이터의 데이터를 만났을 때** 무너지지 않는 것이고, 옛 리더에는 코드를 더 넣을 수 없다.

그러므로 해법은 코드 추가가 아니라 **프로토콜 규율**이다. 규율은 세 줄이다.

1. **덧붙이기만 한다.** 열은 nullable + 기본값으로 추가한다. 이름 변경·용도 전용·타입 변경 금지. enum `wireName` 은 추가만, 이름 변경·삭제 금지.
2. **모르는 값에서 죽지 않는다.** 관용은 배치가 아니라 **행 단위**여야 한다 → [[row-level-decode-tolerance]]
3. **모르는 값을 되돌려 쓰지 않는다.** 관용하되 **보존**해야 한다. 기본값으로 치환하고 그대로 push 하면 다른 기기의 데이터를 파괴한다 → [[tolerance-without-preservation]]

## Details

필드마다 정책이 달라야 하고, 가르는 기준은 **틀리게 추측했을 때 무엇이 일어나는가**다.

| 필드 | 잘못 추측하면 | 옳은 정책 |
|---|---|---|
| `entered_unit` | 값의 **의미가 뒤집힌다**(10~50 은 두 단위 모두 검증 통과) | 추측 금지. 행을 통째로 건너뛴다 |
| `tag` | 라벨 하나가 어긋난다 | 중립 표시로 관용하되 **원문 보존**, 되돌려 쓰지 않는다 |
| `source` | 중복 제거 판정이 흔들린다 | 위와 같음 |

**현재 상태(2026-09-02):** 동기화되는 기록 필드 셋(`GlucoseUnit`·`MeasurementTag`·`ReadingSource`)은 전부 `UnknownWireNameException` 을 던진다. 그 행은 pull 이 건너뛰고 `SyncReport.malformed` 로 센다. 로컬 설정(`TargetRangePreset`)만 기본값으로 떨어진다 — 서버로 되돌아 나가지 않아 파괴 경로가 없다.

**서버가 Postgres enum 이라는 점이 유일한 안전장치다.** `create type measurement_tag as enum (...)` 이므로 새 값은 우리가 `ALTER TYPE ... ADD VALUE` 를 하기 전에는 서버에 들어올 수 없다. 그래서 **순서가 전부다**:

1. 모르는 값에서 던지는 클라이언트를 **먼저 배포**한다
2. 충분히 퍼진 뒤 서버 enum 에 값을 추가한다
3. 그 다음 새 값을 쓰는 앱을 낸다

1을 건너뛰고 2를 하면 되돌릴 수 없다 — 그때 필드에 남아 있는 구버전은 고칠 수 없기 때문이다.

## Related

- Patterns: [[row-level-decode-tolerance]], [[tolerant-decode-with-preservation]], [[cursor-holdback-for-skipped-rows]]
- Anti-Patterns: [[poison-row-blocks-pipeline]], [[tolerance-without-preservation]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-10` (`hash:d7042da`) — 행 하나가 pull 을 영구히 막던 것
- `test/data/sync_engine_test.dart` 그룹 '해석 못 한 행'
- `lib/domain/models/{measurement_tag,reading_source,glucose_unit}.dart` — 세 갈래 정책
