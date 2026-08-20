# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

sugarScan — 일반 혈당계(SMBG) LCD를 카메라로 읽어 기록하는 Flutter 앱.
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

**Windows 함정**: 테스트가 타임아웃으로 죽으면 `flutter_tester.exe` 가 살아남아
`build/native_assets/windows/sqlite3.dll` 을 잡고 있어 다음 빌드가 막힌다.

```bash
# PowerShell
Get-Process -Name flutter_tester -EA SilentlyContinue | Stop-Process -Force
Remove-Item -Recurse -Force build\native_assets
```

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
- **UTC 가 정본**이고 `value_mgdl` 이 정본이다. 단위 변환은 표시 계층에서만.
  사용자가 입력한 원본(`enteredUnit`/`enteredValue`)도 함께 남겨 왕복 오차를 막는다.
- 태깅과 일별 집계는 `measuredAtLocalWallClock`(벽시계 시각) 기준으로 계산한다.

## 시간을 잡아먹었던 함정들

**위젯 테스트**
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

W1~W2, W8 완료(스캐폴드, OCR 모듈, 규칙 기반 판독기, 카메라 연결, 로컬 저장).
다음 후보는 W9(Supabase) 또는 W11 온보딩의 표시 단위 확인 — 지금은 로케일
추정값을 그대로 쓰고 있는데, 단위 오설정은 이 앱에서 가장 위험한 UX 버그다.

`assets/models/7seg_classifier.tflite` 는 아직 저장소에 없다. 없어도 앱은 정상
동작하며(`ScanUnavailable` → 수동 입력), 받는 방법은 `assets/models/README.md` 참조.
