# 완료 기록

끝난 작업과 잡은 버그를 쌓아 두는 곳이다. [`CLAUDE_TASKS.md`](CLAUDE_TASKS.md) 와
[`GLM_TASKS.md`](GLM_TASKS.md) 에서 항목이 사라지면 여기로 온다.

**이 문서는 "무엇을 했나"의 목록이지 "왜 그렇게 했나"의 정본이 아니다.** 판단의
정본은 [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) **§15 구현 로그**이고
규약의 정본은 [`CLAUDE.md`](../CLAUDE.md) 다. 여기에는 **한 줄과 링크**만 남긴다.
설명을 여기에 옮겨 적기 시작하면 정본이 셋으로 갈라진다.

한 줄에 담을 것: 언제 · 무엇이 · 어디에(커밋) · 검증됐는지.

---

## 1. 기능 (W 시리즈)

| 작업 | 완료 | 결과 | 실기기 검증 |
|---|---|---|---|
| W1 | 2026-08-20 | 프로젝트 골격 · 도메인 · OCR 인터페이스 계층 | — |
| W1-b | 2026-08-20 | OCR 모듈 격리 재구조화 (`lib/ocr/` 배럴 경계) | — |
| W1-c | 2026-08-20 | 7-세그먼트 CNN 엔진 부착 (모델 파일은 아직 없음) | — |
| W1-d | 2026-08-20 | 규칙 기반 7-세그먼트 판독기 — **현재 기본 엔진** | 아직 (→ C2) |
| W2 | 2026-08-20 | 카메라 → 스캐너 연결, 확인 시트 | 아직 (→ C2) |
| W8 | 2026-08-20 | Drift 로컬 저장 · 기록 목록 · 직접 입력 | ○ |
| W11-a | 2026-08-20 | 표시 단위 확인 온보딩 (`UnitGate`) | ○ |
| W9-a | 2026-08-20 | Supabase 연결 · 구글 로그인 · 로그인 게이트 | ○ |
| W10 | 2026-08-20 | 동기화 엔진 (아웃박스 push + 델타 pull) | 일부 (→ C4) |
| W12 | 2026-08-21 | 기록 편집 · 삭제 되돌리기 | 일부 (→ C4) |
| W11 | 2026-08-21 | 통계 화면 (마지막 placeholder 제거) | ○ |
| 목표 범위 설정 | 2026-08-21 | 근거 있는 프리셋 3개 중 선택 (`3332d5b`) | — |

**placeholder 화면은 남아 있지 않다.** 모든 탭에 실제 화면이 있다.

W9·W10 실기기 검증(2026-08-20, Redmi Note 11 / Android 14): 구글 로그인 →
`auth.users` 생성 → 직접 입력 저장 → **3.6초 뒤 서버 반영**. 서버의 `updated_at`
이 `created_at` 보다 늦게 찍힌 것으로 트리거 동작까지 확인. 재설치 후에도 로그인
화면이 뜨지 않아 Keystore 세션 복원도 확인. 상세는 §15 W10.

W11 실기기 검증(2026-08-21): 서버에 26건을 넣어 pull 로 그래프를 채웠다.
**여러 행 pull** 이 이때 함께 검증됐다.

---

## 2. 정리 작업 (G 시리즈)

지시서 [`GLM_TASKS.md`](GLM_TASKS.md) · 작업별 상세 [`reports/`](reports/) ·
정본 되먹임 [§15 G1~G8](IMPLEMENTATION_PLAN.md).
전부 2026-08-21 완료, main 병합 `96fac33`.

| 작업 | 결과 | 커밋 | 보고서 |
|---|---|---|---|
| G1 | 미사용 l10n 키 4개 삭제 | `cc8d02f` | [G1](reports/G1-unused-l10n-keys.md) |
| G2 | 삭제 되돌리기에 확인 스낵바 | `01d12b8` | [G2](reports/G2-restore-confirmation.md) |
| G3 | 기록 목록 타일에 메모 한 줄 | `a3e2121` | [G3](reports/G3-note-in-list.md) |
| G4 | 해결된 applicationId TODO 삭제 | `52fd501` | [G4](reports/G4-dead-todo.md) |
| G5 | `LICENSES.md` "확인 필요" 7건 실사 | `75b6302` | [G5](reports/G5-license-audit.md) |
| G6 | 기록 타일·통계 카드에 `Semantics` 라벨 | `cc4d32a` | [G6](reports/G6-accessibility-labels.md) |
| G7 | 예외 원문 노출 제거 → `readingsLoadFailed` | `4d62001` | [G7](reports/G7-error-message-localization.md) |
| G8 | es·pt·de·fr 4개 언어 추가 | `44d4f74` | [G8](reports/G8-locales-es-pt-de-fr.md) |

의료 문구 21개 × 4개 언어는 DeepL 역번역 교차검증으로 **의미 보존 84/84,
판정어 0건**을 확인했다 → [G8 역번역 표](reports/G8-backtranslate-input.md).

---

## 3. 잡은 버그

**같은 실수가 반복되는 자리다.** 새 버그를 적을 때는 이미 있는 줄 중에 같은
종류가 있는지 먼저 볼 것 — 있으면 그 아래에 붙인다.

### 값이 조용히 어긋나는 종류 (가장 위험)

| 언제 | 증상 | 원인 | 막은 것 |
|---|---|---|---|
| W1 | 저혈당 표시 `LO` 가 **`10`** 으로 저장됨 | `ReadingNormalizer` 가 글자 교정(L→1, O→0)을 `HI`/`LO` 판정보다 **먼저** 했다 | 처리 순서를 ①단위 제거 ②HI/LO 판정 ③글자 교정으로 고정. `test/ocr/reading_normalizer_test.dart` |
| W8 | 저장한 UTC 시각이 읽을 때 로컬 시각으로 돌아옴 | Drift 기본값이 날짜를 유닉스 정수로 저장 | `storeDateTimeAsText: true` (ISO-8601 문자열) |
| W8 | Dart enum 이름을 바꾸면 저장된 데이터가 깨짐 | `textEnum` 이 Dart 식별자를 저장 | `TypeConverter` 로 `wireName` 저장 (`pre_meal`) |
| W12 | 메모를 지울 수 없음 | `update(note: null)` 이 "바꾸지 않음"과 "지움"을 구분하지 않았다 | null = 바꾸지 않음, `''` = 지움 |
| W12 | mmol/L 로 넣은 7.6 이 편집 시트에서 137 로 보이고, 저장하면 원본이 사라짐 | 편집 시트가 값을 **표시 단위**로 그렸다 | 그 기록의 `enteredUnit` 으로 그린다 |
| G8 | 일본어 사용자에게 **독일어** 앱이 보임 | 언어가 6개가 되자 Flutter 기본 로케일 해석이 목록 첫 항목(`de`)을 집었다 | `resolveAppLocale` (`359a5b7`) · `test/app/locale_fallback_test.dart` |
| 2026-09-02 | 라벨러가 그린 박스를 **직전 장의 표시 크기** 프레임으로 저장 — LCD 2건 파손 | 캐시 히트로 장을 넘길 때 `lb.ow/oh` 만 갱신되지 않았다. 좌표계에 이름표가 없어 아무도 못 알아챘다 | 프레임 귀속(`lb.frameId`) + 세대 토큰 + `frameGuard` + **서버가 원본 파일로 대조 후 409 거부** + 빌드 지문. [보고서](reports/20260902-labeler-coordinate-frame.md) (`d5366c5`) |
| 2026-09-02 | band 라벨 5건이 이미지 경계를 초과 | EXIF **미적용(회전 전)** 좌표계로 그려졌다. 배율이 아니라 회전이라 스케일 보정으로는 못 맞춘다 | `repair_unrotated_band_labels.py` 로 90° 사상 복구. 육안 확인 후 적용 |
| 2026-09-02 | **통계 화면을 한 번 연 뒤 저장한 기록이 통계에서 사라짐** | `statsReadingsProvider` 가 기간 질의의 위쪽 경계를 구독 시점 `now` 로 굳혔다(autoDispose 아님) | 위 경계를 열고 화면 진입 시 재계산. `test/app/stats_window_test.dart` (`5ed3f06`) |
| 2026-09-02 | `update(value:)` 만 부르면 `enteredValue` 와 정본 `valueMgdl` 이 갈라짐 | 둘 다 있을 때만 `valueMgdl` 을 갱신했다 | 빠진 쪽을 저장된 행에서 채워 항상 정본 재계산. `glucose_repository_edit_test.dart` (`5ed3f06`) |
| 2026-09-02 | `GlucoseScanner.offer()` 가 예외를 흘릴 수 있었다 (계약 위반) | `try` 가 엔진 호출만 감쌌다 — 정규화·검증·안정화는 밖에 있었다 | 경계를 메서드 전체로 + 세션 토큰(stop 뒤 늦게 온 프레임이 옛 단위로 확정하지 않게). `test/ocr/glucose_scanner_contract_test.dart` (`5ed3f06`) |
| 2026-09-02 | **서버 행 하나가 해석 안 되면 pull 이 영구히 막힘** | `ReadingDto` 가 던지면 `_pull` 이 통째로 실패하고 커서가 전혀 전진하지 않았다. 새 앱이 모르는 enum wireName 을 쓰면 구버전 앱은 영영 못 받는다 | 해석 못 한 행은 버리고 `SyncReport.malformed` 로 센다. 페이지 경계·offset·커서는 **서버가 돌려준 행 수** 기준으로 바꿨다(`ReadingPage`). (`d7042da`) |
| 2026-09-02 | pending 이라 건너뛴 서버 변경이 영영 다시 안 옴 | 건너뛴 행 너머로 커서가 전진했다. push 가 한도에 닿아 막히면 복구 경로가 없다 | 커서를 그 행 앞에 세운다(`gte` 라 다시 받는다). 해석 못 한 행은 **반대로** 넘긴다 (`d7042da`) |
| 2026-09-02 | "대기 3건"인데 실제로 올라가는 건 1건 | `pendingSyncCount` 가 기록이 아니라 아웃박스 행을 셌고, 막힌 행까지 포함했다 | `distinct entity_id` + 한도 미만만. 한도는 `syncMaxAttemptsProvider` 로 엔진과 공유 (`d7042da`) |
| 2026-09-02 | 추론 두 개가 겹쳐 돌 수 있었다 | `FrameThrottler.reset()` 이 진행 중인 작업의 잠금을 강제로 내렸다 | 통계만 되돌린다. 잠금은 그 작업이 `finally` 에서 푼다 (`d7042da`) |
| 2026-09-02 | `warpQuadToRect` 주석이 하지 않는 일을 한다고 적혀 있었다 | 원근 펴기 구현이 두 벌로 중복돼 한쪽 주석만 낡았다 | `_warpQuad` 한 벌로 접고, "대비를 걸지 않는다"를 테스트로 고정 (`d7042da`) |

### 테스트가 잘못된 이유로 통과하던 종류

| 언제 | 증상 | 원인 |
|---|---|---|
| W12 | "범위 밖 값은 저장되지 않는다"가 검증기 덕이 아니라 **아무 일도 안 일어나서** 통과 | 시트가 뷰포트보다 길어 저장 버튼 탭이 화면 밖을 쳤다 |
| W11 | 태그 목록이 "없다"로 잘못 통과 | `ListView` 뷰포트 밖 자식은 요소가 만들어지지 않는다 |

→ 세 번째가 어디 있는지 찾는 것이 [G13](GLM_TASKS.md) 이다.

### 화면·문구

| 언제 | 증상 | 막은 것 |
|---|---|---|
| G7 | 사용자에게 `SqliteException(11): database disk image is malformed` 가 그대로 보임 | `readingsLoadFailed` 로 대체, 원문은 `debugPrint` 로만 |
| G2 | 삭제 되돌리기를 눌러도 아무 반응이 없어 눌렸는지 알 수 없음 | `readingRestored` 확인 스낵바 |
| W11 | 숫자를 보러 온 사람이 스크롤부터 해야 했다 (요약 카드 4개가 그래프를 밀어냄) | 카드 하나로 합침 + **차트 상단이 뷰포트 안인지 검사하는 테스트** |

### 빌드·환경

| 언제 | 증상 | 막은 것 |
|---|---|---|
| W1 | `Could not close incremental caches` — pub 캐시(`C:`)와 프로젝트(`D:`)가 다른 드라이브 | `kotlin.incremental=false` (flutter/flutter#173456) |
| W1 | 테스트 타임아웃 뒤 다음 빌드가 막힘 | 살아남은 `flutter_tester.exe` 가 `sqlite3.dll` 을 잡고 있다 → 프로세스 종료 + `build\native_assets` 삭제 |
| W1 | AGP 9.0.x 가 `android-37` 을 못 찾음 | API 37 은 `android-37.0` 이라는 부 버전 이름으로만 존재 → AGP 9.1.1 + Gradle 9.3.1 |
| W1 | 한 모듈에서 Java 11 / Kotlin 17 이 갈려 빌드 중단 | 루트 `build.gradle.kts` 의 JVM 17 통일 블록. `evaluationDependsOn(":app")` **앞**에 둘 것 |
| 2026-08-22 | `flutter create --platforms=windows` 가 테스트를 깨뜨림 | 생성된 `test/widget_test.dart` 삭제 + `git checkout -- .metadata` |

---

## 4. 확인은 됐지만 해결은 아닌 것

**"알아냈다"와 "고쳤다"를 섞지 않으려고 나눠 둔다.** 아래는 조사가 끝났을 뿐
아직 열려 있는 항목이라, 여기 있다고 해서 닫힌 것이 아니다.

| 항목 | 알아낸 것 | 어디로 갔나 |
|---|---|---|
| EasyOCR 라이선스 | **코드는 Apache-2.0 확인.** 학습 **가중치**의 배포 조건은 공개 자료 어디에도 없다 — 더 파도 안 나온다 | [C8](CLAUDE_TASKS.md) (Jaided AI 직접 문의) |
| 소수점 표기 | 입력은 안전하다(검증기가 쉼표를 점으로 바꾼다). **표시만** 항상 점을 찍는다 | [C5](CLAUDE_TASKS.md) |
| Supabase 리전 | `ap-southeast-1`(싱가포르). 사후 변경 불가 — 옮기려면 프로젝트를 새로 만들어야 한다. **EU 로 옮겨도 한국 사용자에 대한 국외 이전 의무는 사라지지 않는다** | [C1](CLAUDE_TASKS.md) |
| Windows 데스크톱 빌드 | 통과한다(≈120초, VS Community 2022 필요). **제품 타깃이 아니라 l10n·UI 미리보기 도구다** — 카메라·헬스·로그인 플러그인이 없다 | [G9](GLM_TASKS.md) 가 이걸로 글자 넘침을 본다 |
| `dart format` | 새 포매터가 **74개 파일**을 다시 쓴다. 기능 변화 없음, `git blame` 통째로 밀림 | [C7](CLAUDE_TASKS.md) (할지 말지가 결정) |

---

## 5. 이 문서를 쓰는 법

- 작업이 끝나면 `CLAUDE_TASKS.md` / `GLM_TASKS.md` 에서 **지우고** 여기에 한 줄
  더한다. 두 곳에 같은 항목을 두지 않는다.
- 버그는 **증상 · 원인 · 무엇이 다시 막는가** 셋을 적는다. 셋째 칸이 비어 있으면
  그 버그는 다시 난다.
- 여기에 문단을 쓰고 싶어지면 그건 §15 에 갈 내용이다. 링크만 남길 것.
