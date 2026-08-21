# GLM 작업 지시서

이 문서는 **GLM 코딩 에이전트에게 넘길 단순 작업 목록**이다. 작업이 끝나면
여기에 새 작업이 추가되고 끝난 작업은 완료 표시된다. 계속 쓰는 문서다.

작업을 시작하기 전에 **§1~§3 을 먼저 끝까지 읽을 것.** 이 저장소에는 겉보기에는
사소해 보이지만 고치면 조용히 데이터가 깨지는 자리가 여럿 있다.

---

## 1. 이 프로젝트가 무엇인가

SugarScan — 일반 혈당계(SMBG) 화면을 카메라로 읽어 기록하는 Flutter 앱.
**의료 데이터를 다룬다.** 값이 틀리게 저장되면 사용자가 자기 건강 상태를 잘못
알게 된다. 화면이 깨지는 버그보다 값이 조용히 어긋나는 버그가 훨씬 위험하다.

전체 설계와 구현 이력은 [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md),
저장소 규약은 루트의 [`CLAUDE.md`](../CLAUDE.md) 에 있다. **둘 다 읽고 시작할 것.**

---

## 2. 절대 건드리지 말 것

아래는 전부 이유가 있어서 그렇게 되어 있다. 작업 중에 "이상해 보인다"고 고치지
말 것. 고쳐야 한다고 판단되면 **고치지 말고 보고서에 적을 것.**

### 2.1 OCR 모듈 경계

- `lib/ocr/src/` 아래를 앱 코드에서 직접 import 하면 경계를 넘은 것이다.
  앱이 볼 수 있는 것은 `lib/ocr/ocr.dart` 배럴이 export 하는 것뿐이다.
- 테스트는 `lib/ocr/testing.dart` 를 쓴다.
- OCR 엔진 등록은 `src/ocr_bootstrap.dart` 한 곳에서만 한다.
- 네트워크를 쓰는 OCR 엔진은 등록 자체가 거부된다. 우회로를 만들지 말 것.

### 2.2 단위와 값

- **정본은 mg/dL(`valueMgdl`) 이다.** 단위 변환은 표시 계층에서만 한다.
- 각 기록은 사용자가 입력한 원본(`enteredUnit`/`enteredValue`)을 함께 갖는다.
  이걸 표시 단위로 덮어쓰면 mmol/L 로 넣은 7.6 이 mg/dL 사용자에게 137 로 보이고
  저장하는 순간 원본이 사라진다.
- 목표 범위 비교는 언제나 mg/dL 로 한다. 단위별로 갈라지면 같은 기록이 사용자에
  따라 다르게 판정된다.
- **10~50 사이의 정수는 두 단위 모두에서 유효한 값이다.** mg/dL 로는 중증 저혈당,
  mmol/L 로는 중증 고혈당이다. 단위가 뒤집히면 의미가 정확히 반대가 된다.

### 2.3 시각

- **UTC 가 정본**이다. 태깅과 일별 집계는 `measuredAtLocalWallClock`(벽시계 시각)
  으로 계산한다.
- `measuredAtUtc` 는 기록 시점에 정해지고 그 뒤로 아무도 바꾸지 않는다.
  동기화가 밀렸다 올라가도 마찬가지다.
- 서버의 `updated_at` 은 **서버 트리거가 찍는다.** 클라이언트가 보내지 않는다.

### 2.4 문구

- **진단성 표현 금지.** "정상 / 높음 / 위험", 인슐린 용량, 행동 권고를 넣지 않는다.
  "목표 범위 안 / 밖" 같은 서술만 한다. 이 선을 넘으면 앱의 규제 분류가 바뀐다.
- 값에 색을 입혀 좋고 나쁨을 나타내지 않는다. 색도 판정이다.
- 통계 화면의 "건수 기준이지 시간 기준이 아니다" 문구는 CGM 의 TIR 과 혼동을
  막는 장치다. **지우지 말 것.**
- 목표 범위 화면의 "본인의 목표는 담당 의료진과 정하세요" 문구도 마찬가지다.

### 2.5 저장과 동기화

- enum 은 Dart 식별자가 아니라 **`wireName`** 으로 저장한다(`preMeal` 아니라
  `pre_meal`). 식별자를 바꿔도 저장된 데이터가 안 깨지게 하려는 것이다.
- 날짜는 ISO-8601 문자열로 저장한다(`storeDateTimeAsText: true`).
- 기록 저장과 아웃박스 등록은 반드시 같은 트랜잭션이다.
- 동기화는 **push 가 pull 보다 먼저**다. pull 은 `syncState == pending` 인 행을
  건너뛴다. 커서는 `gt` 가 아니라 `gte` 다. 오프라인은 실패가 아니다.
  이 판단들은 `test/data/sync_engine_test.dart` 가 고정한다.

### 2.6 빌드 설정

`android/` 아래 빌드 설정은 전부 특정 플러그인이 강제한 값이다. 되돌리면 빌드가
깨진다. 자세한 이유는 `CLAUDE.md` 참조.

- `compileSdk = 37`, `minSdk = 26`, core library desugaring
- AGP 9.1.1 + Gradle 9.3.1
- `android/gradle.properties` 의 `kotlin.incremental=false` — **지우지 말 것**
- 루트 `build.gradle.kts` 의 JVM 타깃 17 통일 블록은 `evaluationDependsOn(":app")`
  **보다 앞**에 있어야 한다

### 2.7 의존성

- `intl` 은 `0.20.2` 고정, `build_runner` 는 `^2.4.0`, `drift_dev` 는 `^2.34.0`.
  올리면 analyzer 충돌로 빌드가 깨진다.
- **Riverpod 코드 생성은 의도적으로 뺐다.** 프로바이더는 `lib/app/providers.dart`
  에 손으로 쓴다. "빠져 있네" 하고 다시 넣지 말 것.
- 새 패키지를 추가하지 말 것. 필요하면 보고서에 적고 멈출 것.

### 2.8 비밀

- `supabase.local.json` 은 접속 정보다. **절대 커밋하지 말고 내용을 보고서나
  커밋 메시지에 옮기지 말 것.** 이미 gitignore 되어 있다.
- `--dart-define` 으로 주입하지 않은 상태가 정상 상태다. 서버 없이도 앱이
  온전히 동작해야 한다.

---

## 3. 작업 방식

### 3.1 검증

커밋 전에 **둘 다** 통과해야 한다. 하나라도 실패하면 커밋하지 말 것.

```bash
flutter analyze          # 경고 하나도 남기지 않는다
flutter test             # 전체 통과
```

l10n(`lib/l10n/*.arb`)을 고쳤으면 생성 코드를 다시 만든다.

```bash
flutter gen-l10n
```

`lib/l10n/generated/` 는 생성물이다. 손으로 고치지 말 것.

### 3.2 테스트를 쓸 때 걸리는 함정

여기서 실제로 두 번 당했다. 둘 다 테스트가 **잘못된 이유로 통과**한다.

- **화면 밖 위젯은 존재하지 않는다.** `ListView` 뷰포트 밖 자식은 요소가 만들어지지
  않아 `find` 가 못 찾고, 화면 밖 버튼은 `tap` 이 빈 좌표를 친다.
  긴 화면에서는 `ensureVisible` / `scrollUntilVisible` 을 먼저 부를 것.
- **`pumpAndSettle` 을 쓰지 말 것.** 무한히 도는 진행 표시기 때문에 영원히
  정착하지 않는다. 정해진 만큼만 시계를 넘긴다.
- **인자 없는 `pump()` 는 시계를 전혀 진전시키지 않는다.** Drift 스트림이 남기는
  타이머가 실행되지 않아 "Timer is still pending" 으로 실패한다. 트리를 테스트
  본문 안에서 내리고 `pump(Duration(milliseconds: 100))`.
- 화면 테스트는 `databaseProvider` 를 `AppDatabase(NativeDatabase.memory())` 로
  덮어쓴다. 호스트에서 실제 SQLite 가 돈다.

### 3.3 Windows 함정

테스트가 타임아웃으로 죽으면 `flutter_tester.exe` 가 살아남아 다음 빌드를 막는다.

```powershell
Get-Process -Name flutter_tester -EA SilentlyContinue | Stop-Process -Force
Remove-Item -Recurse -Force build\native_assets
```

### 3.4 브랜치와 커밋

- **작업 하나당 브랜치 하나.** `glm/<작업ID>-<짧은-설명>` (예: `glm/G1-unused-l10n`)
- 커밋 메시지는 **영문**, 기존 이력과 같은 형식(`fix(scope): ...`).
- **`main` 에 직접 커밋하지 말 것.** 병합은 사람이 한다.
- 여러 작업을 한 브랜치에 섞지 말 것.

### 3.5 보고서

작업마다 보고서를 **반드시** 쓴다. 경로와 파일명은 각 작업에 지정되어 있다.
없는 폴더는 만들면 된다.

```
docs/reports/<보고서 파일명>
```

보고서 양식:

```markdown
# <작업 ID> — <제목>

- 브랜치: `glm/...`
- 커밋: `<해시>`
- 상태: 완료 / 부분 완료 / 중단

## 무엇을 했나
（바꾼 파일과 변경 내용을 한 줄씩）

## 왜 그렇게 했나
（판단이 갈릴 수 있었던 지점만. 자명한 것은 적지 않는다）

## 검증
（실행한 명령과 결과를 그대로 붙인다）

flutter analyze  → No issues found!
flutter test     → All tests passed! (NNN tests)

## 건드리지 않고 남긴 것
（이상해 보였지만 지시 범위 밖이라 두고 온 것. 없으면 "없음"）

## 막힌 것
（중단했다면 어디서 왜 막혔는지. 없으면 "없음"）
```

**"검증" 항목을 비워 두거나 실행하지 않고 채우지 말 것.** 통과했다고 적었는데
실제로 실패하는 것이 이 작업에서 가장 나쁜 결과다.

---

## 4. 작업 목록

### G1 — 쓰이지 않는 l10n 키 정리

**상태**: 대기

`lib/l10n/app_en.arb` / `app_ko.arb` 에 코드에서 참조되지 않는 키가 남아 있다.
W1 스캐폴드 시절에 만들어 놓고 실제 화면이 다른 키를 쓰게 된 것들이다.

지울 대상 — **아래 넷만**:

| 키 | 비고 |
|---|---|
| `unitLabel` | 단위 표기는 `GlucoseUnit.symbol` 을 직접 쓴다 |
| `unitMgdl` | 위와 같음 |
| `unitMmoll` | 위와 같음 |
| `actionRetry` | 동기화 배너는 `syncRetry` 를 쓴다 |

**`readingRestored` 는 지우지 말 것.** 미사용으로 잡히지만 G2 에서 쓴다.

할 일:
1. 두 ARB 파일에서 해당 키를 지운다. `@키` 메타데이터가 있으면 함께 지운다
   (지금은 넷 다 메타데이터가 없다).
2. `flutter gen-l10n` 을 돌린다.
3. `flutter analyze`, `flutter test` 통과 확인.

완료 기준: 위 넷이 두 ARB 와 생성 코드에서 사라지고, 남은 키 수가 en/ko 동일.

**보고서**: `docs/reports/G1-unused-l10n-keys.md`

---

### G2 — 삭제 되돌리기에 확인 문구 붙이기

**상태**: 대기

`lib/features/history/history_screen.dart` 에서 기록을 스와이프로 삭제하면
스낵바에 "실행 취소" 가 뜬다. 그런데 **되돌린 뒤에는 아무 반응이 없다.**
목록은 바뀌지만 사용자는 눌린 게 맞는지 확신하지 못한다.

문구는 이미 있다: `readingRestored` (en `Reading restored`, ko `기록을 되살렸습니다`).

할 일:
1. `_delete` 안의 `SnackBarAction.onPressed` 에서 `repository.restore(...)` 를
   `await` 한 뒤 `readingRestored` 스낵바를 띄운다.
2. 위젯 테스트를 추가한다 — 삭제 → 실행 취소 → 기록이 목록에 돌아오고 확인
   문구가 뜬다.

주의:
- `onPressed` 는 동기 콜백이다. `async` 로 바꿀 때 `BuildContext` 를 await 너머로
  들고 가지 말 것. `ScaffoldMessenger` 를 미리 잡아 두는 방식은 같은 파일의
  `_edit` 에 이미 쓰여 있으니 그대로 따를 것.
- 되살리기가 아웃박스를 거치는 동작은 그대로 둘 것.

완료 기준: 실행 취소를 누르면 기록이 돌아오고 확인 스낵바가 뜬다. 테스트 통과.

**보고서**: `docs/reports/G2-restore-confirmation.md`

---

### G3 — 기록 목록에 메모 표시

**상태**: 대기

기록에 메모를 남길 수 있는데(`GlucoseReading.note`) **목록에서는 안 보인다.**
편집 시트를 열어야만 확인할 수 있어서, 메모를 남겨도 다시 찾아보기 어렵다.

대상: `lib/features/shared/reading_tile.dart`

할 일:
1. `note` 가 있으면 기존 부제(시각 · 태그 · 출처) 아래에 한 줄로 보여 준다.
2. 길면 한 줄로 자른다(`maxLines: 1`, `overflow: TextOverflow.ellipsis`).
3. `note` 가 없으면 아무것도 그리지 않는다. 빈 줄을 남기지 말 것.
4. 위젯 테스트 추가 — 메모 있음 / 없음 두 경우.

주의:
- 이 타일은 판정하지 않는다. 메모에 아이콘이나 색을 붙여 강조하지 말 것.
- 값·시각·태그·출처의 기존 배치를 바꾸지 말 것. 메모 한 줄만 추가한다.

완료 기준: 메모가 있는 기록에서 목록에 메모가 보이고, 없는 기록의 높이가 지금과
같다. 테스트 통과.

**보고서**: `docs/reports/G3-note-in-list.md`

---

### G4 — 죽은 TODO 주석 정리

**상태**: 대기

`android/app/build.gradle.kts` 에 Flutter 템플릿이 남긴 TODO 두 개가 있다.
하나는 이미 해결됐고 하나는 아직 유효하다.

| 줄 | 내용 | 처리 |
|---|---|---|
| 25 | `TODO: Specify your own unique Application ID` | **지운다** — `com.kybirdlabs.sugarscan` 으로 확정됨 |
| 39 | `TODO: Add your own signing config for the release build` | **남긴다** — 아직 안 했다 |

할 일: 25번 줄 주석만 지운다. 그 아래 `applicationId` 는 손대지 말 것.

주의: 이 파일의 다른 값(`compileSdk`, `minSdk`, desugaring)은 §2.6 대상이다.
건드리면 빌드가 깨진다.

완료 기준: 주석 한 줄만 사라지고 `flutter build apk --debug` 가 그대로 성공.
(빌드를 돌릴 수 없는 환경이면 `flutter analyze` 만 하고 보고서에 적을 것.)

**보고서**: `docs/reports/G4-dead-todo.md`

---

### G5 — 라이선스 문서의 "확인 필요" 채우기

**상태**: 대기

`docs/LICENSES.md` 는 초안이다. 표의 여러 항목이 "확인 필요" 로 남아 있다.
**코드를 고치는 작업이 아니라 조사 작업이다.**

할 일: 아래 각 프로젝트의 저장소에서 **LICENSE 파일을 직접 열어** 확인하고 표를
채운다.

- JaidedAI/EasyOCR — 특히 **학습된 가중치**의 라이선스가 코드와 같은지
- clovaai/CRAFT-pytorch — 연구용 한정 조항이 있는지
- clovaai/deep-text-recognition-benchmark
- microsoft/onnxruntime
- tflite_flutter 가 끌어오는 TensorFlow Lite
- scottmudge/SegoDec
- suyashkumar/seven-segment-ocr

각 항목에 **확인한 URL과 확인 날짜**를 함께 적을 것. "Apache-2.0 인 것 같다"
같은 추정은 적지 말고, 확인이 안 되면 "확인 실패 — 이유" 로 남길 것.

주의:
- 라이선스는 법적 문제다. **추측해서 채우지 말 것.** 모르면 모른다고 적는 편이
  훨씬 낫다.
- 문서만 고친다. 코드나 의존성은 건드리지 않는다.

완료 기준: 표의 "확인 필요" 가 확인된 값 또는 "확인 실패 — 이유" 로 바뀌고,
각 행에 출처 URL 과 날짜가 있다.

**보고서**: `docs/reports/G5-license-audit.md`

---

### G6 — 접근성 라벨 (스크린리더)

**상태**: 대기

앱 전체에 `Semantics` 사용이 **0건**이다. 스크린리더 사용자에게 대시보드의
기록이 "137" 처럼 숫자만 읽히고, 단위·시각·태그가 따로 읽히거나 안 읽힌다.
혈당 앱에서 단위가 안 읽히는 것은 그냥 불편한 정도가 아니다.

대상: `lib/features/shared/reading_tile.dart`, `lib/features/stats/stats_screen.dart`

할 일:
1. 기록 타일에 `Semantics(label: ...)` 로 "137 mg/dL, 3월 14일 오전 10시 30분,
   공복, 직접 입력" 처럼 한 문장으로 읽히게 한다. 안쪽 개별 `Text` 는
   `excludeSemantics` 로 중복 낭독을 막는다.
2. 통계 화면의 요약 카드에도 라벨을 붙인다("평균 102 mg/dL" 등).
3. 차트에는 손대지 말 것. 별도 작업이다.

주의:
- 라벨은 화면에 보이는 것과 **같은 내용**이어야 한다. 여기서 "정상 범위" 같은
  말을 덧붙이면 §2.4 위반이다.
- 문구는 반드시 l10n 을 거친다. 하드코딩하지 말 것. 새 키가 필요하면 en/ko 둘 다
  추가한다.

완료 기준: 두 화면의 주요 요소에 라벨이 붙고, 테스트가 통과한다.

**보고서**: `docs/reports/G6-accessibility-labels.md`

---

## 5. 넘기기 전에 사람이 정해야 하는 것

아래는 GLM 에게 주지 않는다. 단순 작업처럼 보이지만 판단이 필요하다.

- **`dart format` 전면 적용** — Dart 3.12 의 새 포매터가 **74개 파일**을 다시
  쓴다. 기능 변화는 없지만 diff 가 거대해져 `git blame` 이 통째로 밀린다.
  할지 말지, 한다면 언제 할지를 먼저 정해야 한다.
- **OCR 관련 전부** — 값을 잘못 읽는 방향의 버그가 나오는 영역이다.
- **동기화 엔진** — `test/data/sync_engine_test.dart` 가 고정한 판단들이
  하나씩 다 이유가 있다.
- **인증·보안** — 세션 저장, 로그인 게이트.
