# G21 — 위키 안티패턴 체크리스트로 `lib/` 전수 점검 (보고만)

- 브랜치: `glm/G21-antipattern-sweep`
- 커밋: 이 보고서 + 작업 목록 이관 커밋 하나
- 상태: 완료 — **코드 변경 0줄.** 다음 사이클 작업 목록이 산출물이다.

## 무엇을 했나

안티패턴 8종의 점검 체크리스트를 `lib/` 전체에 적용했다
(`lib/l10n/generated/`·`*.g.dart` 제외). 각 페이지의 Grounding 에 이미 실린
파일(터졌던 자리와 고친 자리)은 세지 않았다. 판별은 grep 후보 전부를 읽어서
분류했다.

## 요약 — 8종 중 신규 3건

| 안티패턴 | 신규 | 내용 |
|---|---|---|
| duplicated-geometry-implementation | 1건(3곳) | `_cropRoi` 세 벌 |
| contract-guard-too-narrow | 2건 | 엔진 `recognize` 무방비 · 대시보드 저장 무가드 |
| frozen-now-in-live-query | 0건 | 알려진 1곳은 수정본 확인, 나머지 후보 전부 질의 경계 아님 |
| partial-update-desyncs-canonical | 0건 | 알려진 1곳은 수정본 확인 |
| reset-clears-in-flight-lock | 0건 | `reset` 3곳 전부 상태만 되돌림 |
| count-rows-not-entities | 0건 | 알려진 1곳(아웃박스 개수)만 존재 |
| tolerance-without-preservation | 0건 | `orElse` 6곳 전부 던지거나 문서화된 예외 |
| poison-row-blocks-pipeline | 0건 | pull 은 행 단위 관용(알려진 수정), push 는 로컬 발생 행만 |

## 발견 상세

### 1. `_cropRoi` 세 벌 — duplicated-geometry-implementation · **함정만**

- `lib/ocr/src/engines/segment_rule/segment_rule_engine.dart:222`
  (GrayImage — 클램프는 `gray_image.dart:29` 의 `crop` 내부)
- `lib/ocr/src/engines/sevenseg_cnn/seven_seg_cnn_engine.dart:224` (img.Image)
- `lib/features/scan/photo_align_screen.dart:163` (인라인)

셋 다 정규화 ROI 를 픽셀로 환산해 자르는 같은 기하다. 현재는 셋 의미
동치(round + `clamp(0, w-1)` / `clamp(1, w-l)`)지만 **동치를 고정하는 테스트가
없다**(`test/` 에서 `cropRoi`·photo_align 관련 0건). 앱쪽 복제는 모듈 경계
(`lib/ocr/src/` 비공개)가 강제한 것이고, 그 자리의 주석("엔진과 같은 반올림으로
자른다… 다르게 자르면 진단 도구가 거짓말을 한다")이 스스로 경고한다.
**지금은 안 터진다** — 한 곳의 반올림·클램프를 고치는 순간 조용히 갈라지며,
갈라져도 결과가 그럴듯한 이미지로 나온다. photo_align 은 사용자가 눈으로 본
것과 엔진이 본 것이 같음을 보장하려는 진단 도구라 어긋나면 거짓 진단을 한다.

### 2. 엔진 `recognize` 자체 무방비 — contract-guard-too-narrow · **함정만**

- 계약: `lib/ocr/src/engine/ocr_engine.dart:74` "예외를 던지지 말고
  `OcrResult.failed` 로 돌려준다"
- `segment_rule_engine.dart:76` · `seven_seg_cnn_engine.dart:70` — 두 구현 모두
  `try` 없음(알려진 실패 조건만 구조화 반환). 이진화·샘플링·분류 호출에서
  `RangeError` 등이 나면 계약 위반 예외가 그대로 샌다.

실제 방어는 스캐너의 `_recognizeSafely`(`glucose_scanner.dart:155`, 알려진
사이트) 한 곳뿐이다. **지금은 안 터진다** — 현재 엔진 소비 경로 전부가
`scanner.offer` 를 지난다(photo_align 도 스캐너를 쓴다). 엔진을 스캐너 밖에서
직접 부르는 코드가 생기는 순간 계약 문구와 방어 범위가 어긋난다. 인터페이스
문서가 "구현자 의무"로 읽히는 반면 실제로는 "상위 백스톱"에 의존하는 구조라는
것 자체가 기록 가치가 있다.

### 3. 대시보드 저장 무가드 — contract-guard-too-narrow · **조건부**

- `lib/features/dashboard/dashboard_screen.dart:67` — "저장 자체는 저장소가
  로컬 트랜잭션으로 끝내므로 네트워크가 없어도 실패하지 않는다"
- 같은 파일 `:75` — `await ref.read(glucoseRepositoryProvider).add(...)` 에
  `try` 없음. `glucose_repository.dart:47` 의 `add` 자체에도 없다.

주장 문구는 "네트워크가 없어도"로 좁혀 읽을 여지가 있지만, 호출부에는 아무
방어가 없다 — Drift 오류(디스크 만료, 마이그레이션 실패 등)가 나면 미처리
비동기 예외가 되고 "저장되었습니다" 스낵바도 건너뛴다. **조건부** — 로컬 DB
계층 실패에서만 발화하며 일상 경로에선 안 터진다. 같은 `add` 를 쓰는 다른
호출부(스캔 확인 시트 등)는 확인하지 않았다 — 이 표를 읽는 사람이 범위를
정하는 몫으로 남긴다.

## 해당 없음으로 본 자리 (0건 패턴의 근거)

- **frozen-now**: 알려진 `statsReadingsProvider`(`providers.dart:353`)는 수정본
  확인(상한 `now+365d` 열림·하한은 `refreshStats` 에포크). 나머지
  `DateTime.now()` 3곳 — 대시보드 eAG(`dashboard_screen.dart:165`, `build` 마다
  재계산이라 굳지 않음) · 태그 제안 2곳(`manual_entry_sheet.dart:47` 시트 열림
  때 1회, `scan_screen.dart:233` 확인 시점 1회) — 전부 질의 경계가 아니다.
- **partial-update**: `glucose_repository.update`(`:133`)는 백플렉 수정본
  확인(트랜잭션 안 행 재판독). `Value.absent` 도 이곳만 쓰인다.
- **reset-clears**: `glucose_scanner.reset`(`:141`, 상태만)·`stop`(`:148`,
  세대 토큰 선행) · `reading_stabilizer.reset`(`:110`, 창 데이터만) — 잠금을
  건드리는 곳 없음. `frame_throttler.reset` 은 알려진 사이트.
- **tolerance-without-preservation**: `orElse` 6곳 — 세 enum 은 던짐(알려진
  수정), `target_range_preset.dart:66` fallback 은 페이지에 문서화된 승인,
  `scan_screen.dart:131` 카메라 선택 fallback 은 직렬화 경로가 없어 파괴
  경로가 없다.
- **poison-row**: `_pull` 은 행 단위 관용 + `updatedAtOf` 커서 홀드백
  (알려진 수정, `reading_dto.dart:77`). `_push`(`sync_engine.dart:159`)는 배치
  단위 `try` 지만 행이 전부 같은 앱 버전이 로컬에서 쓴 것이라 이질 버전이
  들어올 수 없다 — 함정만(로컬 데이터가 오염되면 전체 push 가 막힘).
- **count-rows**: 사용자에게 보이는 개수는 아웃박스 대기 수(알려진 수정)와
  목록 `itemCount`(엔티티 목록 길이)뿐.
- **계약 문구 나머지**: `system_timezone.dart`(전체 try) ·
  `initializeRemoteBackend`(구간별 전체 try) · `tflite_digit_classifier.tryLoad`
  (전체 try) · `reading_dto.idOf`(던질 코드 없음) · `main.dart:12`(callee 계약
  확인됨) — 전부 계약=방어 범위.

## 검증

코드를 한 줄도 바꾸지 않았으므로 게이트는 확인만 한다.

```text
flutter analyze  → No issues found!
flutter test     → All tests passed! (387 tests)
```

## 건드리지 않고 남긴 것

- 신규 3건 전부 — 수정 여부·순서는 사람이 정한다(이 보고서가 다음 사이클
  작업 목록의 입력이다).
- `_cropRoi` 통합은 모듈 경계 설계와 얽혀 있다(앱쪽 복제를 없애려면 배럴
  공개 또는 진단용 썸네일 생성의 모듈 이동 필요) — 구조 결정이라 GLM 몫이
  아니다.

## 막힌 것

없음.
