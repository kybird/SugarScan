---
tags: [index]

# Wiki Index

이 프로젝트의 구조화된 지식 베이스입니다. `doc/raw/` 로그에서 추출한 핵심 개념과 패턴을 정리했습니다.

---

## Concepts

| 개념 | 설명 | 별칭 |
|------|------|------|
| [[canonical-value]] | 한 사실을 두 군데에 적으면 언젠가 갈라진다. | 정본, single-source-of-truth, value_mgdl |
| [[coordinate-frame]] | 좌표 4개짜리 배열은 **그 자체로는 아무 의미가 없다.** `(559, 345)` 는 "어느 이미지의, 어느 크기·방향 공간에서" 잰 값인지가 붙어야 비로소 위치를 가리킨다. | 좌표계, frame, 표시 좌표계, cross-space-comparison |
| [[live-query]] | Drift 의 `watch()` 는 테이블이 바뀔 때마다 **처음 만든 SQL 을 그대로 다시 돌린다.** 파라미터를 다시 계산하지 않는다. | 살아 있는 질의, Drift watch, 스트림 질의 |
| [[wire-schema-evolution]] | 앱이 출시되는 순간부터 **여러 버전이 동시에 같은 서버를 읽고 쓴다.** 구버전 클라이언트는 이미 사용자 기기에 설치돼 있어 나중에 고칠 수 없다 — 이것이 이 주제의 모든 제약을 만든다. | 스키마 진화, 버전 공존, forward-compatibility, additive-only-wire-schema |

---

## Patterns

| 패턴 | 설명 | 별칭 |
|------|------|------|
| [[build-fingerprint]] | 돌고 있는 클라이언트가 **어느 빌드인지** 화면에서 읽히게 한다. | 빌드 지문, stale-tab-detection, /api/build |
| [[contract-boundary-equals-method-boundary]] | "이 메서드는 예외를 던지지 않는다"는 계약을 걸었으면, `try` 는 **메서드 전체**를 감싸야 한다. | 계약 경계, never-throws |
| [[cursor-holdback-for-skipped-rows]] | 델타 커서를 어디까지 미느냐는 **왜 건너뛰었는지에 따라 정반대**다. | 커서 홀드백, delta cursor |
| [[dry-run-before-repair]] | 사람이 만든 데이터를 되돌리는 스크립트는 **기본 동작이 "계산만"** 이어야 한다. | 복구 스크립트 규약, --apply, 백업 후 수정 |
| [[frame-provenance-binding]] | 좌표를 다루는 상태에는 **그 좌표계가 누구의 것인지**를 함께 들고 다닌다. | 프레임 이름표, frame-id-binding, 좌표계 귀속 |
| [[generation-token]] | 비동기 작업을 시작할 때 세대 번호를 찍고, 결과를 반영하기 전에 **그 세대가 아직 유효한지** 확인한다. | 세대 토큰, 세션 토큰, stale-response-guard, lb.gen |
| [[open-upper-bound-for-live-window]] | "최근 N일" 같은 살아 있는 기간 질의는 **위쪽 경계를 열어 둔다.** 상한에 "지금"을 넣지 않는다. | 열린 상한, 기간 질의 |
| [[row-level-decode-tolerance]] | 배치에서 행 하나를 해석하지 못했다고 배치 전체를 실패시키지 않는다. **관용의 단위는 행이다.** | 행 단위 관용, poison-row 방어, ReadingPage |
| [[server-side-write-verification]] | 클라이언트가 "무엇을 기준으로 만든 값인지"를 함께 보내게 하고, **서버가 정본에서 직접 재확인한 뒤에만** 기록한다. | 저장 검문, 쓰기 검증, 409 거부 |
| [[tolerant-decode-with-preservation]] | 모르는 값을 만나면 **관용하되 보존한다.** 기본값으로 치환하고 그대로 되돌려 쓰면, 관용이 곧 데이터 파괴가 된다. | 관용 디코드, unknown 보존, additive-only |

---

## Anti-Patterns

| 안티패턴 | 설명 | 별칭 |
|------|------|------|
| [[bounds-check-as-correctness-proof]] | 파손된 좌표를 보정할 때 **결과가 이미지 경계 안에 들어오는지**로 맞았는지 판정하는 것. | 경계 통과를 정답으로 오인, oob 검사 과신 |
| [[contract-guard-too-narrow]] | "이 메서드는 예외를 던지지 않는다"고 문서에 적어 두고, `try` 는 **위험해 보이는 호출 하나만** 감싸는 것. | 좁은 try, 계약보다 좁은 방어 |
| [[count-rows-not-entities]] | 아웃박스는 변경마다 행을 쌓지만, 서버로는 **현재 상태 한 번**만 간다. | 대기 n건 오표시, 큐 행 세기 |
| [[duplicated-geometry-implementation]] | 거의 같은 100줄(디코드 → 회색 변환 → 호모그래피 역샘플링)이 두 함수에 복사돼 있는 것. | 좌표 변환 중복, 워프 두 벌 |
| [[frozen-now-in-live-query]] | ```dart | 굳은 now, 기간 상한 고정 |
| [[label-without-visual-ground-truth]] | 좌표만 저장하고, 저장된 좌표를 **다시 이미지에 그려 확인하는 경로 없이** 계속 진행하는 것. | 눈검증 없는 라벨링, 좌표만 저장 |
| [[mixed-image-decode-conventions]] | `cv2.imread` 는 EXIF orientation 을 **자동 적용**하고, `PIL.Image.open` 은 **무시**한다. | EXIF 관례 불일치, cv2 vs PIL |
| [[padding-as-content]] | CTC 라벨 배열의 blank(클래스 10)를 필터하지 않고 문자열로 조인해 `"90" + "10"` → `"9010"` 이 된 것. | blank 조인, 패딩 직렬화 |
| [[partial-update-desyncs-canonical]] | ```dart | 부분 수정, 정본 미갱신 |
| [[poison-row-blocks-pipeline]] | 관용의 단위가 **행이 아니라 배치**인 것. | 독행, 배치 단위 관용, 행 하나가 전체를 막음 |
| [[reset-clears-in-flight-lock]] | ```dart | reset 이 잠금을 푸는 것, _busy = false |
| [[stale-client-writes]] | 브라우저에 어느 버전의 JS 가 떠 있는지 **아무도 모르는 상태**로 저장 요청을 받는 것. | 낡은 탭 쓰기, stale build |
| [[tolerance-without-preservation]] | `values.firstWhere(..., orElse: () => SomeDefault)` — 관용처럼 보이지만, 그 값을 나중에 서버로 되돌려 쓰는 순간 **다른 기기의 데이터를 파괴한다.** | 모르는 값 치환, orElse 기본값, silent-normalization |
| [[unnamed-coordinate-frame]] | 좌표 배열만 저장하고, **그 좌표가 어느 프레임에서 만들어졌는지**는 저장하지 않는 것. | 이름 없는 좌표계, 프레임 미기록 |

---

## Answers

| 답변 | 설명 | 별칭 |
|------|------|------|

---

## Statistics

- Total concepts: 4
- Total patterns: 10
- Total anti-patterns: 14
- Total answers: 0
- Last updated: 2026-09-02
