---
status: active
version_context: "sugarScan lib/domain/models"
tags: [sync, anti-pattern]
aliases: [모르는 값 치환, orElse 기본값, silent-normalization, fromWireName, orElse, firstWhere, MeasurementTag, ReadingSource, measurement_tag.dart]
created: 2026-09-02
confidence: 4
---
# 모르는 값을 기본값으로 치환하고 되돌려 쓰는 것

`values.firstWhere(..., orElse: () => SomeDefault)` — 관용처럼 보이지만, 그 값을 나중에 서버로 되돌려 쓰는 순간 **다른 기기의 데이터를 파괴한다.**

## 실패 모드

1. 새 버전 앱이 새로운 `tag` wireName 을 서버에 쓴다.
2. 구버전 앱이 pull 하며 그 값을 모른다 → `random` 으로 치환해 로컬에 저장한다.
3. 사용자가 그 기록의 **메모만** 고친다 → 아웃박스 → push.
4. push 는 행 전체를 보내므로 **서버의 태그가 `random` 으로 덮인다.**
5. 새 버전 앱에서 태그가 사라진다. 아무도 오류를 보지 못한다.

관용의 목적은 "옛 클라이언트가 살아남는 것"이지 "옛 클라이언트가 새 데이터를 지우는 것"이 아니다. **살아남는 것과 해를 끼치지 않는 것은 다른 요구다.**

## 점검 체크리스트

- [ ] `orElse` 로 기본값을 돌려주는 enum 디코더가 있는가
- [ ] 그 값이 직렬화 경로로 **되돌아 나가는가** (나간다면 파괴 경로가 있다)
- [ ] 모르는 값을 **원문 그대로 보존**하는 변형이 있는가
- [ ] 추측이 값의 **의미를 뒤집는** 필드인가 (단위 등) → 그렇다면 관용이 아니라 행 건너뛰기
- [ ] 스키마 변경이 덧붙이기만인가 (이름 변경·타입 변경 금지)

## 현재 상태 (2026-09-02 해결)

세 정책이 제각각이었고 그중 어느 것도 버전 공존을 고려해 정해지지 않았다.
이제 **동기화되는 기록 필드는 전부 던진다.**

| 디코더 | 이전 | 지금 |
|---|---|---|
| `GlucoseUnit.fromWireName` | 던짐(`Bad state: No element`) | `UnknownWireNameException` — 진단 가능 |
| `MeasurementTag.fromWireName` | **`random` 치환** | 던짐 |
| `ReadingSource.fromWireName` | **`manual` 치환** | 던짐 |
| `TargetRangePreset.fromWireName` | 기본값 | **그대로** — 동기화되지 않는 로컬 설정이라 파괴 경로가 없다 |

던진 행은 [[row-level-decode-tolerance]] 가 받아 건너뛰고 `SyncReport.malformed`
로 센다. **구버전에서 그 기록이 잠깐 안 보이는 것은 앱을 업데이트하면 낫지만,
덮어쓴 값은 업데이트해도 못 살린다** — 이 비대칭이 결정의 근거다.

행을 건너뛰는 대신 값·시각은 보이게 하려면 [[tolerant-decode-with-preservation]]
(2단계)로 올리면 된다. 데이터가 죽지 않으므로 **급하지 않다.**

## 올바른 대안

[[tolerant-decode-with-preservation]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-10`
- `lib/domain/models/{measurement_tag,reading_source,glucose_unit}.dart`
