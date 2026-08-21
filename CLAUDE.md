# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

SugarScan — 일반 혈당계(SMBG) LCD를 카메라로 읽어 기록하는 Flutter 앱.
상세 설계와 구현 이력은 `docs/IMPLEMENTATION_PLAN.md`, 특히 **§15 구현 로그**에 있다.

## 명령어

```bash
flutter analyze                              # 무경고가 기본. 경고 하나도 남기지 않는다
flutter test                                 # 전체
flutter test test/ocr/segment_patterns_test.dart
flutter test --plain-name "LO 를 10 으로 읽지 않는다"
dart run build_runner build                  # Drift 코드 생성 (lib/data/local/database.g.dart)
flutter gen-l10n                             # ARB → lib/l10n/generated/
```

`--delete-conflicting-outputs` 는 현재 build_runner 버전에서 제거된 옵션이라 무시된다.

**커밋 기준**: `flutter analyze` 무경고 + `flutter test` 전체 통과.

**Windows 함정 1**: 테스트가 타임아웃으로 죽으면 `flutter_tester.exe` 가 살아남아
`build/native_assets/windows/sqlite3.dll` 을 잡고 있어 다음 빌드가 막힌다.

```bash
# PowerShell
Get-Process -Name flutter_tester -EA SilentlyContinue | Stop-Process -Force
Remove-Item -Recurse -Force build\native_assets
```

**Windows 함정 2**: pub 캐시(`C:`)와 프로젝트(`D:`)가 다른 드라이브라 Kotlin 증분
컴파일이 드라이브를 넘는 상대 경로를 계산하지 못하고 `Could not close incremental
caches` 로 죽는다(flutter/flutter#173456). `android/gradle.properties` 의
`kotlin.incremental=false` 가 이걸 막고 있다 — **지우지 말 것.**

**안드로이드 빌드 설정은 손대기 전에 이유를 볼 것.** 전부 특정 플러그인이 강제한
값이라 되돌리면 빌드가 깨진다:
- `compileSdk = 37` — `flutter_secure_storage`, `permission_handler_android`.
  API 37 은 SDK 저장소에 `android-37.0` 이라는 부(minor) 버전 이름으로만 존재하고,
  해석하려면 **AGP 9.1.1 이상**이 필요하다(그래서 AGP 9.1.1 + Gradle 9.3.1).
  AGP 9.0.x 는 `android-37` 을 찾다가 실패한다.
- `minSdk = 26` — `health`. Android 8.0 미만을 버리는 **제품 결정**이다.
- core library desugaring — `flutter_local_notifications`.
- 루트 `build.gradle.kts` 의 JVM 타깃 17 통일 — AGP 9 는 한 모듈에서 Java 와
  Kotlin 타깃이 다르면 빌드를 멈추는데 일부 플러그인이 Java 만 11 로 못박는다.
  `evaluationDependsOn(":app")` **보다 앞**에 있어야 한다 — 뒤에 두면 이미 평가가
  끝나 `afterEvaluate` 를 걸 수 없다.

## 아키텍처

```
features/ (UI)  →  ocr/ (격리 모듈)     domain/ (순수 Dart, Flutter 의존 0)
      ↓                                       ↑
   data/  →  Drift(정본) + sync_outbox  →  Supabase(복제본, W10 예정)
```

**OCR 모듈이 이 프로젝트의 중심이자 가장 엄격한 경계다.**

- 앱이 볼 수 있는 것은 `lib/ocr/ocr.dart` 배럴이 export 하는 것뿐이다:
  `GlucoseScanner`, `ScanOutcome`, `OcrFrame`. `lib/ocr/src/` 를 앱에서 import 하면
  경계를 넘은 것이다. 테스트는 `lib/ocr/testing.dart` 를 쓴다.
- **앱은 OCR 결과를 재검증하지 않는다.** 글자 보정(`ReadingNormalizer`), 값 검증,
  프레임 간 합의(`ReadingStabilizer`)가 모두 모듈 안에서 끝난다. `ScanConfirmed` 가
  나왔다는 것은 곧 "쓸 수 있는 값"이라는 뜻이다.
- 엔진(`OcrEngine` 구현)은 모듈 내부 부품이다. 등록은 `src/ocr_bootstrap.dart`
  **한 곳에서만** 한다.
- `GlucoseScanner.offer()` 는 절대 예외를 던지지 않는다. 라이브 프레임 루프에서
  예외가 새면 스캔 화면 전체가 죽는다.

데이터 흐름: 카메라 프레임 → `CameraFrameConverter`(Y 평면 추출·회전) →
`scanner.offer()` → `ScanConfirmed` → 확인 시트 → `ScanEntry` →
`GlucoseRepository.add()` → Drift + 아웃박스(한 트랜잭션).

## 절대 어기면 안 되는 규칙

- **OCR 은 단말에서만 돈다.** 레지스트리가 `requiresNetwork` 엔진 등록을 항상
  거부한다. 조건부 허용 플래그를 만들지 말 것 — 플래그가 있으면 언젠가 켜진다.
- **저장 전 사용자 확인 1탭.** 인식은 자동이지만 저장은 아니다. UX 취향이 아니라
  안전·규제 요구다.
- **수동 입력 경로는 항상 열려 있어야 한다.** 카메라 권한 거부, 모델 없음, 저사양
  기기 어느 경우에도 사용자가 기록을 남기지 못하는 상태를 만들지 않는다.
- **진단성 문구 금지.** "정상/위험", 인슐린 용량 계산, 액션 권고를 넣지 않는다.
  "목표 범위 내/밖" 같은 서술만 한다. 일반 건강관리 도구 분류를 지키는 선이다.
- **표시 단위는 반드시 사용자 확인을 거친다.** `UnitGate` 가 확인 전에는 앱 전체를
  막는다. 검증기 범위상 **10~50 정수는 두 단위 모두 통과**하는데, mg/dL 로는 중증
  저혈당이고 mmol/L 로는 중증 고혈당이라 의미가 정확히 뒤집힌다. 로케일 추정값을
  확정으로 쓰지 말 것.
- **UTC 가 정본**이고 `value_mgdl` 이 정본이다. 단위 변환은 표시 계층에서만.
  사용자가 입력한 원본(`enteredUnit`/`enteredValue`)도 함께 남겨 왕복 오차를 막는다.
- 태깅과 일별 집계는 `measuredAtLocalWallClock`(벽시계 시각) 기준으로 계산한다.

## 시간을 잡아먹었던 함정들

**위젯 테스트**
- **화면 밖 위젯은 존재하지 않는다.** `ListView` 뷰포트 밖 자식은 요소가 만들어지지
  않아 `find` 가 못 찾고, 화면 밖 버튼은 `tap` 이 빈 좌표를 친다. 둘 다 테스트를
  **잘못된 이유로 통과**시킨다(W12 저장 버튼, W11 태그 목록에서 실제로 겪었다).
  긴 화면에서는 `ensureVisible` / `scrollUntilVisible` 을 먼저 부를 것.
- `pumpAndSettle` 을 쓰지 말 것. 무한히 도는 진행 표시기(카메라 준비, 스트림 첫
  방출) 때문에 영원히 정착하지 않는다. 정해진 만큼만 시계를 넘긴다.
- 인자 없는 `pump()` 는 시계를 **전혀** 진전시키지 않는다. Drift 스트림이 구독
  해제 시 남기는 `Duration.zero` 타이머가 실행되지 않아 "Timer is still pending"
  으로 실패한다. 트리를 테스트 본문 안에서 내리고 `pump(Duration(milliseconds: 100))`.
- 화면 테스트는 `databaseProvider` 를 `AppDatabase(NativeDatabase.memory())` 로
  덮어쓴다. 호스트에서 실제 SQLite 가 돈다.

**의존성 (Flutter 3.44 SDK 가 meta/test_api/matcher 를 고정하는 데서 파생)**
- `intl` 은 `0.20.2` 정확히 고정. `build_runner` 는 `^2.4.0`(2.15.2+ 불가),
  `drift_dev` 는 `^2.34.0`(2.34.1+1 부터 analyzer 13 요구).
- **Riverpod 코드 생성은 의도적으로 뺐다.** `riverpod_generator` 가 `drift_dev` 와
  analyzer 버전이 공존하지 못한다. 프로바이더는 `lib/app/providers.dart` 에 수동
  작성한다. "빠져 있네" 하고 다시 넣지 말 것.

**저장 (Drift 기본값을 두 군데 바꿨다)**
- enum 은 `textEnum` 이 아니라 `TypeConverter` 로 **`wireName`** 을 저장한다.
  기본 방식은 Dart 식별자를 쓰는데, 그러면 Dart enum 이름을 바꾸는 순간 저장된
  데이터가 깨지고 서버(`pre_meal`)와도 갈라진다.
- 날짜는 `storeDateTimeAsText: true` 로 ISO-8601 문자열 저장. 유닉스 정수 기본값은
  읽을 때 **로컬 시각** `DateTime` 을 돌려줘 UTC 정본 규칙이 조용히 깨진다.
- 기록 저장과 아웃박스 등록은 반드시 같은 트랜잭션.

**7-세그먼트 판독**
- 비트 순서는 최상위부터 `A B C D E F G`. 어긋나면 `2` 와 `5` 처럼 좌우 대칭인
  숫자가 조용히 뒤바뀐다.
- `ReadingNormalizer` 의 처리 순서가 안전 장치다: ① 단위 표기 제거 → ② `HI`/`LO`
  판정 → ③ 글자 교정. 순서를 바꾸면 저혈당 표시 `LO` 가 L→1, O→0 을 거쳐 **`10`
  이라는 정상 범위 값으로 둔갑**한다.
- 해밍 거리는 1 로 묶여 있다. 두 획이 손상되면 다른 글자로 **정확히** 떨어지는
  경우가 흔하다(`8` 에서 A·D 가 꺼지면 정확히 `H`). 거리 2 는 복구가 아니라 오독이다.
- `O`/`I` 는 `0`/`1` 과 패턴이 같다. `L`/`H` 만 어떤 숫자와도 겹치지 않아
  `LO`/`HI` 판정의 닻 역할을 한다.

**카메라**
- YUV420 의 Y 평면이 곧 휘도다. 색 변환이 필요 없고 UV 는 읽지도 않는다.
- 로우 스트라이드 패딩을 반드시 걷어내야 한다. 무시하면 행이 밀려 이미지가
  전단(shear)되고 세그먼트 샘플 영역이 통째로 어긋난다.
- 가이드 박스와 ROI 정렬은 **실기기에서 눈으로 맞춰야 한다.** 인식이 전혀 안 되면
  알고리즘보다 이 정렬을 먼저 의심할 것.

## 현재 상태

W1~W2, W8, W11-a, W9-a, W10, W12, W11 완료(스캐폴드, OCR 모듈, 규칙 기반
판독기, 카메라 연결, 로컬 저장, 표시 단위 확인 온보딩 + 설정, Supabase 연결,
동기화 엔진, 기록 편집·삭제 되돌리기, 통계 화면). **placeholder 화면은 없다.**
다음 후보는 OCR 실기기 튜닝, 주기 실행(WorkManager)+ 지수 백오프, 목표 범위 설정.

**통계 화면은 판정하지 않는다.** 점을 선으로 잇지 않고(시점 표본이라 사이를
이으면 없는 정보를 그린다), 목표 범위는 중립 띠 하나이며, 비율에 색을 입히지
않는다. "건수 기준이지 시간 기준이 아니다" 문구는 CGM 의 TIR 과 혼동을 막는
장치라 지우면 안 된다.

**기록 편집 시트는 값을 표시 단위가 아니라 그 기록의 `enteredUnit` 으로
보여 준다.** 표시 단위로 보여 주면 mmol/L 로 넣은 7.6 이 mg/dL 사용자에게
137 로 보이고, 저장하는 순간 원본이 사라진다. 측정 시각은 고칠 수 없게 두었다 —
태깅과 일별 집계가 벽시계 시각 위에 서 있어서 날짜와 구간이 통째로 움직인다.
`update(note:)` 는 null 이 "바꾸지 않음", 빈 문자열이 "지움"이다.

**W9·W10 은 실기기에서 검증됐다**(2026-08-20, Redmi Note 11 / Android 14).
구글 로그인 → `auth.users` 생성 → 직접 입력 저장 → 3.6초 뒤 서버 반영까지 확인.
서버의 `updated_at` 이 `created_at` 보다 늦게 찍힌 것으로 트리거 동작도 확인했다.
아직 안 해본 것: 다기기 pull, 충돌, 오프라인 후 복귀.

**Supabase 접속 정보는 저장소에 없다.** `--dart-define` 으로 주입하고, 주입하지
않은 상태(`RemoteDisabled`)가 정상 상태다 — 서버 없이도 앱이 온전히 동작해야
한다. 설정 방법은 `README.md`.

**인증은 Google 로그인 하나뿐이다. 익명 로그인은 쓰지 않는다.** 로그인 전
상태는 완전 로컬이다 — `user_id` 를 로컬에 저장하지 않고 push 하는 순간에
찍기 때문에, 로그인 전 아웃박스가 로그인 직후 그대로 올라간다. 익명을 다시
넣지 말 것: 설치마다 `auth.users` 행이 쌓이고 identity 병합 로직이 따라온다.

**로그인 게이트가 막는 경우는 하나뿐이다** — 서버 설정된 빌드 + 세션 없음 +
이 기기에서 로그인한 적 없음. 세션 만료로는 막지 않는다. 막으면 리프레시
토큰이 끊긴 오프라인 사용자가 기록을 남길 방법이 없어져 "기록을 남기지 못하는
상태를 만들지 않는다" 규칙을 깬다. `test/app/auth_gate_test.dart` 가 고정한다.

**동기화(W10)에서 뒤집기 쉬운 결정들** — 전부 `test/data/sync_engine_test.dart`
가 고정한다:
- **push 가 pull 보다 먼저다.** 반대로 하면 안 보낸 로컬 변경 위에 서버의 옛
  값이 덮이고, 다음 push 가 그 옛 값을 서버로 되돌려 보낸다.
- **pull 은 `syncState == pending` 행을 건너뛴다.** `updated_at` 크기 비교로
  LWW 를 하지 않는다 — 서버 시계와 단말 시계를 비교하는 셈이라 틀어진 만큼 틀린다.
- 서버 스키마는 로컬의 **부분집합**이다(`ocr_raw_text`·`photo_path`·
  `adjusted_by_user` 없음). companion 에서 그 열을 빼야 로컬 값이 보존된다.
- `updated_at` 은 **서버 트리거가 찍는다.** 클라이언트는 보내지 않는다.
- 커서는 `gt` 가 아니라 **`gte`**. 한 배치가 같은 `updated_at` 을 가져서,
  `gt` 로 자르면 페이지 경계 행이 영영 안 넘어온다.
- **오프라인은 실패가 아니다.** 시도 횟수를 태우면 지하철을 여섯 번 타는
  것만으로 아웃박스가 영구히 막힌다.
- 한도에 닿은 항목도 **행은 남긴다.** 보낼 것을 버리지 않는다. 다시 집히게
  하려면 `retryBlocked()` 로 시도 횟수를 되돌려야 한다 — **사용자가 버튼을
  누를 때만.** 자동으로 풀면 한도가 무의미해진다.
- 동기화 상태 판정은 `syncStatusProvider` 한곳에서만 한다(막힘 > 로그아웃 >
  대기). 화면이 각자 조합하면 막힌 상태를 놓치는 조합이 생긴다.

**출시 전 반드시 막아야 할 구멍: 동의와 개인정보처리방침이 아예 없다.**
지금은 로그인하면 곧바로 혈당 기록이 서버로 올라간다. 사용자에게 아무것도 묻지
않는다. 혈당은 한국 개인정보보호법에서도 **민감정보**이고, 서버가
`ap-southeast-1`(싱가포르)이라 **국외 이전**에 해당한다 — PIPA 제28조의8 은
정보주체의 **별도 동의**(이전받는 자의 명칭·연락처, 이용 목적, 보유 기간을 미리
고지)를 포함한 요건을 요구한다. EU 사용자를 받으면 GDPR Art.9 가 더해진다.

**이건 "EU 를 안 받으면 되는" 문제가 아니다.** 한국 사용자만 받아도 걸린다.
Play 스토어 등록에도 개인정보처리방침 URL 과 Data safety 양식이 필수다.
언어를 늘리는 것과는 무관한, 출시의 전제 조건이다. 자세한 내용은
`docs/IMPLEMENTATION_PLAN.md` 의 해당 절 참조.

`assets/models/7seg_classifier.tflite` 는 아직 저장소에 없다. 없어도 앱은 정상
동작하며(`ScanUnavailable` → 수동 입력), 받는 방법은 `assets/models/README.md` 참조.
