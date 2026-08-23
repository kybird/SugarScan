# GLM 작업 지시서

이 문서는 **GLM 코딩 에이전트에게 넘길 단순 작업 목록**이다. 작업이 끝나면
여기에 새 작업이 추가되고 끝난 작업은 완료 표시된다. 계속 쓰는 문서다.

짝이 되는 문서가 [`CLAUDE_TASKS.md`](CLAUDE_TASKS.md)(위임하지 않는 작업)이고,
끝난 일은 [`DONE.md`](DONE.md) 에 쌓인다. 무엇을 어느 쪽에 두는지의 기준은
`CLAUDE_TASKS.md` §1 에 있다 — **정답이 이 저장소 문서에 이미 적혀 있으면 여기,
정하는 것이 작업이면 저기다.**

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

**상태**: 완료 (2026-08-21)

> 브랜치 `glm/G1-unused-l10n` · 코드 커밋 `cc8d02f` · main 병합 `96fac33`
> 결과: 지정 4키 삭제, en/ko 각 99키 동일 확인. 보고서 → [reports/G1-unused-l10n-keys.md](reports/G1-unused-l10n-keys.md)

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

**상태**: 완료 (2026-08-21)

> 브랜치 `glm/G2-restore-confirmation` · 코드 커밋 `01d12b8` · main 병합 `96fac33`
> 결과: 실행 취소 시 `readingRestored` 확인 스낵바 + 삭제→되돌리기 위젯 테스트.
> 보고서 → [reports/G2-restore-confirmation.md](reports/G2-restore-confirmation.md)

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

**상태**: 완료 (2026-08-21)

> 브랜치 `glm/G3-note-in-list` · 코드 커밋 `a3e2121` · main 병합 `96fac33`
> 결과: 부제 아래 메모 한 줄(없으면 높이 불변), 아이콘·색 없음.
> 보고서 → [reports/G3-note-in-list.md](reports/G3-note-in-list.md)

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

**상태**: 완료 (2026-08-21)

> 브랜치 `glm/G4-dead-todo` · 코드 커밋 `52fd501` · main 병합 `96fac33`
> 결과: 25줄 주석만 삭제, `flutter build apk --debug` 성공으로 검증.
> 보고서 → [reports/G4-dead-todo.md](reports/G4-dead-todo.md)

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

**상태**: 완료 (2026-08-21)

> 브랜치 `glm/G5-license-audit` · 코드 커밋 `75b6302` · main 병합 `96fac33`
> 결과: 7개 저장소 LICENSE 직접 확인해 표 갱신. CRAFT 는 연구용 한정 조항
> 없음(순수 MIT). EasyOCR **가중치**만 공식 명시가 없어 "확인 실패 — Jaided AI
> 문의 필요"로 잔여. 보고서 → [reports/G5-license-audit.md](reports/G5-license-audit.md)

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

**상태**: 완료 (2026-08-21)

> 브랜치 `glm/G6-accessibility-labels` · 코드 커밋 `cc4d32a` · main 병합 `96fac33`
> 결과: 기록 타일·통계 요약 카드에 Semantics 라벨(기존 l10n 조각으로만 구성,
> 판정어 없음, 차트 미수정). 보고서 → [reports/G6-accessibility-labels.md](reports/G6-accessibility-labels.md)

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

### G7 — 사용자에게 예외 원문을 보여 주지 않기

**상태**: 완료 (2026-08-21)

> 브랜치 `glm/G7-error-message` · 코드 커밋 `4d62001` · main 병합 `96fac33`
> 결과: `readingsLoadFailed` 추가, 원문은 debugPrint 로만 남김,
> `Text('$error` 검색 0건. 보고서 → [reports/G7-error-message-localization.md](reports/G7-error-message-localization.md)

앱 전체에서 번역되지 않은 문자열이 딱 두 군데 있는데, 둘 다 같은 문제다.

| 파일 | 줄 |
|---|---|
| `lib/features/dashboard/dashboard_screen.dart` | `child: Text('$error')` |
| `lib/features/history/history_screen.dart` | `child: Text('$error', ...)` |

기록을 못 읽었을 때 **Dart 예외 객체를 그대로 화면에 뿌린다.** 번역이 안 되는
것은 물론이고, 사용자에게 `SqliteException(11): database disk image is
malformed` 같은 문장이 보인다. 사용자가 할 수 있는 일이 없는 문구다.

할 일:
1. l10n 키를 하나 추가한다(en/ko 둘 다). 예: `readingsLoadFailed`
   - en: `Couldn't load your readings.`
   - ko: `기록을 불러오지 못했습니다.`
2. 두 화면에서 `Text('$error')` 를 그 문구로 바꾼다.
3. 예외 원문은 **버리지 말고** `debugPrint` 로 남긴다. 진단 정보가 사라지면
   나중에 이 오류를 추적할 방법이 없다.
4. 두 화면의 오류 상태 위젯 테스트를 추가한다.

주의:
- 원인이나 조치를 추측해 적지 말 것("네트워크를 확인하세요" 등). 이 경로는
  로컬 DB 읽기 실패이고 네트워크와 무관하다.
- 기록이 **0건인 상태**와 **읽기 실패**는 다른 화면이다. 지금 있는 빈 상태
  (`historyEmpty`)를 재사용해 둘을 뭉개지 말 것.

완료 기준: 두 화면에서 예외 원문이 사라지고, 로그에는 남는다. 테스트 통과.
`grep -rn "Text('\$error" lib/` 결과가 0건.

**보고서**: `docs/reports/G7-error-message-localization.md`

---

### G8 — 지원 언어 4개 추가 (es · pt · de · fr)

**상태**: 완료 (2026-08-21)

> 브랜치 `glm/G8-locales-es-pt-de-fr` · 코드 커밋 `44d4f74`(+영어 폴백 `359a5b7`) · main 병합 `96fac33`
> 결과: 4개 언어 각 100키(en/ko 와 일치, 플레이스홀더 보존), supportedLocales 6개.
> 의료 문구 21개는 DeepL 역번역 교차검증 84/84 의미 보존·판정어 0건
> ([reports/G8-backtranslate-input.md](reports/G8-backtranslate-input.md)).
> 미지원 언어 폴백은 사용자 결정으로 영어 구현(`resolveAppLocale`).
> 보고서 → [reports/G8-locales-es-pt-de-fr.md](reports/G8-locales-es-pt-de-fr.md)

지금은 영어와 한국어뿐이다(`app_en.arb`, `app_ko.arb`, 키 100개 — G1 이 4개를
지우고 G7 이 하나를 더한 뒤의 수다). 아래 넷을
추가한다. 시장 규모로 고른 것이고 규제·배포 범위와는 무관한 결정이다.

| 파일 | 언어 | 주요 시장 |
|---|---|---|
| `app_es.arb` | 스페인어 | 멕시코(당뇨 인구 7위) · 중남미 · 스페인 |
| `app_pt.arb` | 포르투갈어(브라질 어투) | 브라질(당뇨 6위, Play 매출도 상위) |
| `app_de.arb` | 독일어 | 독일 · 오스트리아 · 스위스 |
| `app_fr.arb` | 프랑스어 | 프랑스 · 벨기에 · 스위스 · 퀘벡 |

**작업을 두 단계로 나눈다. 한 번에 끝내려 하지 말 것.**

#### 1단계 — 일반 문구 번역

`app_en.arb` 를 원본으로 삼아 4개 파일을 만든다.

- `@@locale` 을 각 언어 코드로 설정한다.
- `@키` 메타데이터는 **번역본에 넣지 않는다.** 원본(`app_en.arb`)에만 둔다.
  `app_ko.arb` 가 이미 그렇게 되어 있으니 그 형태를 따를 것.
- `appTitle` 은 `SugarScan` 그대로 둔다. 제품명은 번역하지 않는다.
- 플레이스홀더(`{count}`, `{days}`, `{range}`, `{unit}`, `{email}` 등)를 **그대로
  유지**한다. 이름을 번역하거나 순서를 바꾸면 생성이 실패한다.
- 단위 기호 `mg/dL`, `mmol/L` 은 번역하지 않는다.

#### 2단계 — 의료 문구는 역번역을 붙여 보고만 한다

아래 **21개 키**는 잘못 번역되면 앱이 판정하는 것처럼 읽히거나 의미가 뒤집힌다.
번역은 하되, **보고서에 원문·번역문·한국어 역번역을 나란히 표로 적을 것.**
사람이 검토한 뒤에 병합한다.

```
medicalDisclaimer      statsInRange           statsInRangeNote
settingsTargetNote     settingsUnitNote       targetObservation
targetObservationNote  targetPreMeal          targetPreMealNote
targetTight            targetTightNote        onboardingUnitTitle
onboardingUnitBody     onboardingUnitWarning  editUnitWarning
meterShowsHigh         meterShowsLow          ea1cLabel
ea1cEstimateBadge      ea1cInsufficientData   invalidValueRange
```

번역할 때 반드시 지킬 것:

- **"정상 / 비정상 / 안전 / 위험 / 좋음 / 나쁨" 을 쓰지 말 것.** 원문이 서술로만
  쓰여 있다. `statsInRange` 는 "목표 범위 안"이지 "정상 범위"가 아니다.
  언어에 따라 자연스러운 표현이 곧 판정어인 경우가 있으니 주의할 것.
- `statsInRangeNote` 의 요지는 **"시간이 아니라 건수"** 다. 이 대비가 사라지면
  CGM 의 TIR 과 혼동되어 임상적으로 다른 의미가 된다.
- `editUnitWarning` 의 요지는 **"변환이 아니라 재해석"** 이다. "convert" 로
  번역하면 뜻이 정반대가 된다.
- `medicalDisclaimer` 는 법적 문구다. 의역하지 말고 직역에 가깝게.
- `ea1cLabel`/`ea1cEstimateBadge` 는 **추정치**임이 드러나야 한다. 실제 검사값과
  같은 말로 옮기면 안 된다.
- `meterShowsHigh`/`meterShowsLow` 는 혈당계 화면의 `HI`/`LO` 표시를 가리킨다.
  높다/낮다는 뜻이 아니라 **측정 범위를 벗어났다**는 뜻이다.

#### 마무리

1. `flutter gen-l10n` 을 돌린다. 생성된 `supportedLocales` 에 6개가 들어가야 한다.
2. `flutter analyze`, `flutter test` 통과 확인.
3. 각 언어로 앱을 띄워 **글자 넘침**을 확인한다. 독일어는 영어보다 30% 가까이
   길어져서 버튼과 칩이 자주 깨진다. 확인할 수 없으면 보고서에 적을 것.

주의:
- **키를 추가하거나 지우지 말 것.** 이 작업은 번역만 한다.
- 번역이 애매한 키는 **비워 두지 말고** 영어 원문을 그대로 넣은 뒤 보고서에
  "미번역" 으로 적을 것. 키가 빠지면 그 언어에서 런타임에 영어로 떨어지는데,
  어디가 빠졌는지 추적이 안 된다.

완료 기준: 4개 파일이 생기고 en/ko 와 키 수(100)가 같다. 생성·분석·테스트 통과.
보고서에 의료 문구 21개의 역번역 표가 있다.

**보고서**: `docs/reports/G8-locales-es-pt-de-fr.md`

---

### G9 — 6개 언어 글자 넘침 점검

**상태**: 대기

G8 이 4개 언어를 넣었지만 **화면에서 본 적이 없다.** 독일어는 영어보다 30% 가까이
길어 버튼과 칩이 깨지기 쉽다. G8 시점에는 볼 방법이 없었는데 지금은 있다 —
Windows 데스크톱 빌드가 통과한다(2026-08-22 확인).

```bash
flutter config --enable-windows-desktop
flutter create --platforms=windows .
flutter build windows --debug
```

**`flutter create` 가 남기는 부작용 둘을 반드시 되돌릴 것:**
1. `test/widget_test.dart` 를 새로 만든다 — 존재하지 않는 `MyApp` 을 쓰는 카운터
   템플릿이라 그대로 두면 테스트가 깨진다. **지운다.**
2. `.metadata` 의 `migration.platforms` 를 windows 로 갈아치운다.
   **`git checkout -- .metadata` 로 되돌린다.**
3. `windows/` 는 **커밋하지 않는다**(`.gitignore` 에 이미 있다).

할 일
1. 6개 언어(en·ko·es·pt·de·fr)로 앱을 띄워 모든 화면을 돌아본다. 로케일은
   기기 언어를 바꾸거나 `MaterialApp` 의 `locale` 을 임시로 고정해서 본다
   (임시 변경은 커밋하지 않는다).
2. **넘침을 전부 표로 적는다** — 언어 / 화면 / 위젯 / 문구. 스크린샷을 붙이면 더 좋다.
3. 수정은 **아래 셋만** 한다. 그 밖의 레이아웃 변경은 하지 말고 보고서에 적을 것.
   - `Text` 에 `maxLines` + `overflow: TextOverflow.ellipsis` 추가
   - 넘치는 자식을 `Flexible` / `Expanded` 로 감싸기
   - `Row` 가 넘칠 때 `Wrap` 으로 교체

주의
- **번역문을 줄이지 말 것.** 의료 문구 21개는 역번역 교차검증을 거친 것이라
  단어 하나가 의미를 바꾼다. 문구가 길면 문구가 아니라 그릇을 고친다.
- 스캔·로그인 화면은 Windows 에서 플러그인이 없어 동작하지 않는다
  (`ScanUnavailable`, `RemoteDisabled`). 그 상태의 화면은 볼 수 있으니 그대로 본다.
- 잘림(ellipsis)이 **숫자나 단위**를 자르는 자리가 있으면 고치지 말고 **크게 적을 것.**
  `137 mg/dL` 이 `137 mg...` 로 잘리는 것은 레이아웃 문제가 아니라 안전 문제다.

완료 기준: 6개 언어 전 화면을 돌아본 표가 있고, 지정한 세 가지 방식으로 고칠 수
있는 넘침이 사라진다. `flutter analyze` · `flutter test` 통과.

**보고서**: `docs/reports/G9-locale-overflow.md`

---

### G10 — 접근성 라벨 나머지 화면 요소

**상태**: 대기

G6 이 기록 타일과 통계 요약 카드에 `Semantics` 를 붙였고, 범위 밖이라 남긴 것을
보고서에 적어 두었다. 그걸 마저 한다.

대상 (G6 이 남긴 것 그대로)
- `lib/features/stats/stats_screen.dart` 의 기간 선택 `SegmentedButton`,
  태그별 평균 목록(`_ByTagList`)
- `lib/features/settings/settings_screen.dart` 의 단위·목표 범위 선택
- `lib/features/history/history_screen.dart` 의 스와이프 삭제 동작

**차트(`_TrendChart`)에는 손대지 말 것.** 점 하나하나를 낭독하게 만드는 것은 별도
설계가 필요하고, 잘못 만들면 스크린리더 사용자가 화면을 빠져나가지 못한다.

주의
- **새 l10n 키를 만들지 말 것.** G6 이 기존 현지화 조각을 조합해 라벨을 구성했다.
  같은 문장이 두 벌이 되면 의료 문구 검토 대상이 그만큼 늘어난다. 조합으로 안 되면
  만들지 말고 보고서에 적을 것.
- **낭독문에도 판정어 금지 규칙(§2.4)이 그대로 적용된다.** "정상 범위" 같은 말을
  라벨에만 슬쩍 넣지 말 것.
- 라벨은 화면에 보이는 것과 **같은 내용**이어야 한다. 설명을 덧붙이지 않는다.

완료 기준: 위 요소에 라벨이 붙고, 중복 낭독이 없다. 테스트 통과.

**보고서**: `docs/reports/G10-accessibility-rest.md`

---

### G11 — 남은 미지역화 문자열 감사

**상태**: 대기

G7 이 대시보드·기록 화면의 예외 원문 노출을 고쳤고, "다른 화면의 오류 경로는
범위 밖"이라고 적어 두었다. 그 나머지를 **전수로** 훑는다.

**이 작업은 조사가 본체다.** 고치는 것보다 빠짐없이 찾는 것이 중요하다.

할 일
1. `lib/` 전체에서 사용자에게 보이는 하드코딩 문자열을 찾는다. 최소한 이만큼:
   ```bash
   grep -rn "Text('" lib/ --include=*.dart | grep -v generated
   grep -rn "Text(\"" lib/ --include=*.dart | grep -v generated
   grep -rn "label:\|hintText:\|helperText:\|tooltip:\|semanticLabel:" lib/ --include=*.dart | grep -v generated
   grep -rn "SnackBar(" lib/ --include=*.dart | grep -v generated
   ```
2. 찾은 것을 **표로 정리한다** — 파일 / 줄 / 문자열 / 사용자에게 보이는가.
   제품명(`SugarScan`), 단위 기호(`mg/dL`·`mmol/L`), 디버그 로그는 지역화 대상이
   아니다. 표에는 넣되 "대상 아님"으로 적는다.
3. **지역화가 필요한데 안 된 것만** 고친다. 새 키는 **6개 ARB 전부**에 추가한다
   (`@` 메타데이터는 `app_en.arb` 에만).
4. `flutter gen-l10n` → `flutter analyze` → `flutter test`.

주의
- **의료 문구 21개(§G8 목록)에 해당하는 새 문구가 생기면 고치지 말고 멈출 것.**
  판정어가 될 수 있는 문구는 사람이 본다.
- 오류 문구에 **원인이나 조치를 추측해 적지 말 것**("네트워크를 확인하세요" 등).
- 6개 언어 키 수가 전부 같아야 한다. 지금 100 이다.

완료 기준: 감사 표가 있고, 지역화 대상이 0건으로 남는다. ARB 6개 파일 키 수 일치.

**보고서**: `docs/reports/G11-untranslated-audit.md`

---

### G12 — l10n 정합성을 테스트로 고정

**상태**: 대기 · **G11 뒤에 할 것**

G1·G7·G8·G11 이 전부 같은 종류의 실수를 손으로 막고 있다 — 키가 빠지거나, 파일마다
개수가 다르거나, 쓰이지 않는 키가 남는 것. **이걸 테스트로 내린다.**

만들 것: `test/l10n/arb_consistency_test.dart`

1. **6개 ARB 의 키 집합이 완전히 같다.** 다르면 어느 파일에 무엇이 빠졌는지 이름을
   찍어서 실패시킨다. "개수가 다르다"만 알려주면 찾는 데 시간이 걸린다.
2. **번역본에 `@` 메타데이터가 없다.** `app_en.arb` 에만 있어야 한다.
3. **플레이스홀더가 파일 간에 일치한다.** `{count}` 가 한 언어에서만 빠지면
   `gen-l10n` 이 통과해도 런타임에 그 언어만 깨진다.
4. **`lib/` 어디에서도 참조되지 않는 키가 없다.** 소스에서 `AppLocalizations` 의
   게터 이름을 grep 하는 방식으로 충분하다.

주의
- 테스트는 ARB 파일을 **파일에서 읽는다.** 생성 코드를 읽으면 생성 전 상태를
  못 잡는다.
- 4번이 오탐을 낼 수 있다(문자열로 조립해 호출하는 경우). 오탐이 나면 키를 지우지
  말고 **테스트에 예외 목록을 두고 이유를 주석으로 적을 것.** 지금 그런 키가
  있는지도 보고서에 적는다.
- 새 패키지를 넣지 말 것. `dart:io` + `dart:convert` 로 충분하다.

완료 기준: 네 검사가 전부 돌고 현재 저장소에서 통과한다. 일부러 키 하나를 지워
실패하는 것을 확인하고 그 출력을 보고서에 붙인다.

**보고서**: `docs/reports/G12-l10n-consistency-test.md`

---

### G13 — 위젯 테스트 함정 전수 감사

**상태**: 대기

이 저장소에서 **두 번** 당했다(W12 저장 버튼, W11 태그 목록). 둘 다 테스트가
**잘못된 이유로 통과**하고 있었다. 세 번째가 어디에 있는지 찾는다.

**이 작업은 고치는 것보다 찾는 것이 목적이다.** 통과하는 테스트를 건드리는
작업이라 특히 조심할 것.

할 일
1. `test/features/` 의 모든 위젯 테스트에서 아래를 찾아 표로 만든다.
   - `ensureVisible` / `scrollUntilVisible` 없이 하는 `tap`
   - "없음"을 단정하는 `findsNothing` — 정말 없는 것인지, 뷰포트 밖이라 없는 것인지
   - `pumpAndSettle` 사용(있으면 안 된다)
   - 인자 없는 `pump()` — 시계를 전혀 진전시키지 않는다
2. 의심 항목마다 **일부러 깨 본다.** 검증 대상을 반대로 바꿨을 때 테스트가 실패하면
   건강한 것이고, **그대로 통과하면 그 테스트는 아무것도 검증하지 않고 있다.**
   이 확인 결과를 표에 적는다.
3. 아무것도 검증하지 않는 것으로 드러난 테스트만 고친다. `ensureVisible` 을 앞에
   부르거나, `pump(Duration(milliseconds: 100))` 로 바꾼다.

주의
- **검증 내용 자체를 바꾸지 말 것.** 도달하지 못하던 곳에 도달하게만 한다.
  고친 뒤 실제로 실패하는 테스트가 나오면 **그것이 발견한 버그다** — 테스트를
  느슨하게 만들지 말고 멈춰서 보고할 것.
- 2번의 "일부러 깨 보기"는 확인용이다. 커밋에 남기지 않는다.

완료 기준: 감사 표에 모든 위젯 테스트가 있고 각각 "검증됨 / 무의미했음"이 적혀
있다. 무의미했던 것이 고쳐지고 전체 테스트가 통과한다.

**보고서**: `docs/reports/G13-widget-test-audit.md`

---

### G14 — 테스트 없는 화면 셋 채우기

**상태**: 대기

위젯 테스트가 있는 화면은 대시보드·기록·통계·편집 시트·기록 타일뿐이다.
아래 셋은 하나도 없다.

| 화면 | 최소한 고정할 것 |
|---|---|
| `features/settings/settings_screen.dart` | 단위 변경 시 경고가 뜬다 · 목표 범위 선택이 저장된다 · 서버 미설정 빌드에서 동기화 영역이 숨는다 |
| `features/scan/manual_entry_sheet.dart` | 범위 밖 값이 저장되지 않는다 · 쉼표 입력(`7,6`)이 받아들여진다 · 태그 선택이 반영된다 |
| `features/scan/confirm_sheet.dart` | 인식값이 그대로 보인다 · 고치면 `adjustedByUser` 가 선다 · **확인 없이는 저장되지 않는다** |

주의
- 화면 테스트는 `databaseProvider` 를 `AppDatabase(NativeDatabase.memory())` 로
  덮어쓴다. 기존 `test/features/*_test.dart` 의 설정을 그대로 따를 것.
- §3.2 의 함정 넷을 전부 피할 것. 특히 시트는 기본 뷰포트보다 길다 —
  **`ensureVisible` 없이 저장 버튼을 탭하지 말 것.** W12 에서 정확히 이걸로 당했다.
- **화면 코드를 고치지 말 것.** 테스트를 붙이다 버그가 나오면 고치지 말고 보고한다.
  테스트를 통과시키려고 프로덕션 코드를 바꾸는 순간 이 작업의 의미가 없어진다.
- 확인 시트의 "저장 전 사용자 확인 1탭" 은 UX 취향이 아니라 안전·규제 요구다.
  이걸 검증하는 테스트를 반드시 넣을 것.

완료 기준: 세 화면에 테스트가 생기고 위 표의 항목이 전부 고정된다. 전체 통과.

**보고서**: `docs/reports/G14-untested-screens.md`

---

### G15 — 셀 단위 판독 벤치 전량 실행

**상태**: 완료 (2026-08-22)

> 브랜치 `glm/G15-cell-bench` · 보고서 커밋 `a9a8259` (코드 변경 0줄)
> 결과: 전량 41,990장 30초. 치명적 오독 8.71% · 표시 없음 값 생성 86/1992(4.32%)
> · blank 39.71%. 재실행 판정 수치 완전 일치(p95 지연만 측정 오차).
> 보고서 → [reports/G15-cell-bench-run.md](reports/G15-cell-bench-run.md)

하네스는 만들어져 있다([`tools/ocr_bench/`](../tools/ocr_bench/README.md)).
**돌려서 표를 채우는 것이 이 작업의 전부다.** 41,990장이라 시간이 걸리는 것 말고는
기계적이다.

데이터는 이미 `assets_dev/upstream/` 에 받아 두었다(Apache-2.0). 없으면:

```bash
git clone --depth 1 https://github.com/Kazuhito00/7segment-display-reader.git \
  assets_dev/upstream/7segment-display-reader
```

할 일

1. **전량 실행.** 시간이 걸리므로 중간에 끊지 말 것.
   ```bash
   dart run tools/ocr_bench/bin/cell_bench.dart \
     --dataset assets_dev/upstream/7segment-display-reader/01.dataset \
     --dump-failures 100 \
     --out docs/reports/G15-cell-bench-result.md
   ```
2. **걸린 시간(벽시계)을 잰다.** 나중에 CI 에 넣을지 판단할 근거가 된다.
3. **같은 명령을 한 번 더 돌려 숫자가 완전히 같은지 확인한다.** 다르면 어딘가에
   순서 의존이나 난수가 있다는 뜻이라 **멈추고 보고할 것.**
4. 참고용 간격 표본도 함께 남긴다 — `--limit 100` 으로 한 번 더 돌려 전량 결과와
   나란히 적는다. 두 숫자가 크게 다르면 표본 크기가 부족하다는 뜻이다.
5. 보고서에 **실행 환경**을 적는다: `dart --version`, OS, CPU.

**절대 하지 말 것**

- **OCR 코드를 한 줄도 고치지 말 것.** `lib/ocr/` 전체가 §5 대상이다.
  숫자가 나쁘게 나오는 것이 **이 작업의 결과물**이지 고칠 버그가 아니다.
  임계값(`SegmentSampler.onRatio`, `maxHammingDistance`)을 만지면 무엇을 재고
  있었는지가 사라진다.
- **하네스도 고치지 말 것.** import 를 바꾸면 `dart run` 으로 안 돈다
  (README 의 마지막 절 참조).
- 결과를 요약하거나 좋게 정리하지 말 것. **출력을 그대로 붙인다.**

**보고서에 반드시 답할 것** — 표만 붙이고 끝내지 말 것:

| 질문 | 왜 묻나 |
|---|---|
| 꺼진 화면(`11`)에서 숫자를 몇 건 만들어 냈나 | 재지도 않은 값이 기록될 수 있다. **가장 나쁜 결과다** |
| 치명적 오독률은 몇 %인가 | 미판독과 절대 합치지 말 것 |
| 가장 못 읽는 숫자 셋은 무엇인가 | 튜닝의 출발점이 된다 |
| `2`↔`5` 가 서로 섞여 나오나 | 섞이면 비트 순서 문제다(최상위부터 `A B C D E F G`) |
| `blank`(`0000000`)로 떨어진 비율 | 이진화가 아무것도 못 잡았다는 뜻이다 |

완료 기준: 전량 리포트가 `docs/reports/G15-cell-bench-result.md` 에 있고, 위 다섯
질문에 답이 있으며, 두 번 돌린 결과가 같음이 확인된다. **코드 변경 0줄.**

**보고서**: `docs/reports/G15-cell-bench-run.md`

---

## 4.1 OCR 작업군 (G16~G19) — 예외적으로 위임한다

**원래 §5 는 "OCR 관련 전부"를 위임 대상에서 뺐다.** 값을 잘못 읽는 방향의 버그가
나오는 영역이라서다. 아래 넷은 그 예외인데, 조건이 붙어 있다.

**판단은 이미 이 지시서 안에 다 들어 있다.** 숫자와 규칙이 전부 명시되어 있으므로
GLM 은 정하지 말고 그대로 옮기기만 하면 된다. 그리고 **판독 동작을 바꾸는 것은
전부 플래그 뒤에 넣고 기본값을 끈 채로 둔다** — 켜는 결정은 사람이 한다.

읽고 시작할 것: [`tools/ocr_bench/README.md`](../tools/ocr_bench/README.md) ·
[`reports/G15-cell-bench-run.md`](reports/G15-cell-bench-run.md)

**왜 이 작업들이 필요한가** — G15 가 셀 단위(숫자 한 개) 데이터로 코어 3단계만
쟀는데, 실제 엔진은 그것 말고도 많은 일을 한다. 가로 자릿수 분할, 표시 전체
이진화, `HI`/`LO` 판정, 소수점, 자릿수 결합이 **하나도 검증되지 않았다.**
**장면 단위(여러 자릿수가 있는 화면 한 장) 데이터가 세상에 없어서** 그렇다.
그래서 만든다.

순서가 있다: **G16 → G17 → G19.** G18 은 독립이라 아무 때나.

---

### G16 — 장면 단위 합성 데이터 생성기

**상태**: 완료 (2026-08-23)

> 브랜치 `glm/G16-scene-synth` · 커밋 `88e5ef6` (`lib/` 변경 0줄)
> 결과: `tools/synth7seg/bin/synth.dart`. 같은 시드 바이트 동일 확인,
> 눈 검증 20/20(소수점 미렌더 버그를 이 검증에서 발견·수정).
> 기본 2000장 `assets_dev/synth` 생성(HI/LO 7.8%·반사 14.2%·극성 반반).
> 보고서 → [reports/G16-scene-synth.md](reports/G16-scene-synth.md)

`tools/synth7seg/bin/synth.dart` 를 새로 만든다. **`lib/` 는 건드리지 않는다.**

Dart 로 쓴다(Python 포크가 아니다). `image: ^4.9.2` 가 이미 의존성에 있고, 세그먼트는
사각형 7개라 그리는 데 라이브러리가 더 필요 없다. 새 패키지를 추가하지 말 것.

#### 출력

```
assets_dev/synth/
  images/000001.png …
  labels.jsonl
```

`labels.jsonl` 한 줄의 형식 — **이 키 이름을 그대로 쓸 것**(계획서 §2.6 형식):

```json
{"file":"000001.png","value":"137","unit":"mgdl","digits":3,
 "margin":0.12,"rotation":-3.5,"perspective":0.02,"contrast":140,
 "blur":0.4,"glare":false}
```

`value` 는 **화면에 보이는 문자열 그대로**다. `HI`/`LO` 인 경우 그 문자열을 넣고
`unit` 은 그대로 둔다.

#### 그릴 것

7-세그먼트 글리프는 `lib/ocr/src/engines/segment_rule/segment_patterns.dart` 의
`kDigitPatterns` / `kLetterPatterns` 를 **그대로 읽어서** 쓴다. 비트가 켜진
세그먼트만 그린다. **표를 손으로 옮겨 적지 말 것** — 두 벌이 되면 언젠가 갈라진다.

세그먼트 위치는 `SegmentGeometry.standard` 를 참고하되, 생성기는 **판독기와 독립적이어야
한다.** 판독기의 기하를 그대로 쓰면 "자기가 그린 걸 자기가 읽는" 시험이 되어
아무것도 검증하지 못한다. 생성기는 일반적인 7-세그먼트 비율로 **따로** 그린다.

#### 변화 축과 범위 — 이 숫자를 그대로 쓸 것

| 축 | 범위 | 왜 |
|---|---|---|
| 자릿수 | 3 또는 4 | 혈당계 표시 자릿수 |
| 값 | mg/dL 20~600 정수 / mmol/L 1.1~33.3 (소수 1자리) | 검증기 범위 |
| `HI`/`LO` | 전체의 **8%** | 세상 어느 데이터셋에도 없다. 반드시 넣는다 |
| 여백(margin) | 표시 둘레 **0~25%** | ROI 가 베젤·여백을 포함하는 상황 |
| 회전 | **−8° ~ +8°** | 손으로 들고 찍는 각도 |
| 원근 | 네 모서리를 폭의 **0~6%** 만큼 흔든다 | 비스듬히 본 화면 |
| 대비 | 전경·배경 휘도 차 **30~200** | 30 근처가 저대비 LCD |
| 흐림 | 가우시안 **0~1.5px** | |
| 반사 | **15%** 확률로 밝은 타원 하나 | |
| 극성 | 어두운 글자/밝은 배경과 그 반대를 **반반** | 반사형 LCD 와 백라이트 |

**시드를 받는다**(`--seed`, 기본 0). 같은 시드는 같은 데이터를 낳아야 한다.
재현이 안 되면 벤치 결과를 비교할 수 없다.

#### 인자

```
--out <디렉터리>   기본 assets_dev/synth
--count N          생성 장수, 기본 2000
--seed N           기본 0
```

#### 완료 기준

- `dart run tools/synth7seg/bin/synth.dart --count 50` 이 50장 + 50줄을 만든다
- 같은 시드로 두 번 돌리면 **파일 바이트가 동일**하다(확인하고 보고서에 적을 것)
- 눈으로 20장을 열어 라벨과 화면이 일치하는지 확인한다. **하나라도 어긋나면 멈출 것**
- `flutter analyze` 무경고

**주의**: `assets_dev/` 는 gitignore 되어 있다. **생성된 이미지를 커밋하지 말 것.**
커밋하는 것은 생성기 코드뿐이다.

**보고서**: `docs/reports/G16-scene-synth.md`

---

### G17 — 장면 단위 벤치와 기준선 측정

**상태**: 대기 · **G16 뒤에 할 것**

`tools/ocr_bench/bin/scene_bench.dart` 를 만든다. G15 의 셀 벤치와 달리
**`SegmentRuleEngine.recognize()` 를 통째로 태운다** — 품질 게이트, 이진화,
자릿수 분할, 결합까지 전부 거치는 진짜 경로다.

#### 먼저 할 한 줄

`lib/ocr/testing.dart` 의 export 한 줄을 이렇게 **바꾼다**(추가가 아니라 교체):

```dart
export 'src/engine/ocr_frame.dart' show NormalizedRect, OcrFrame, OcrImageFormat;
```

벤치가 `OcrFrame` 을 만들어야 하는데 지금은 `NormalizedRect` 만 나가 있다.
**이 한 줄 말고 `lib/` 에서 고칠 것은 없다.**

#### 재는 것

계획서 §2.6 의 항목을 따른다.

| 지표 | 정의 |
|---|---|
| 완전일치 | 판독 문자열 == 라벨 |
| **치명적 오독** | 값을 냈는데 라벨과 다름. **자릿수가 달라진 경우를 따로 센다**(`95`→`195` 유형) |
| 미인식 | 값을 내지 않음(게이트 거부 포함). 거부 사유별로 쪼갠다 |
| HI/LO 정확도 | `HI`/`LO` 라벨을 맞혔는지. **숫자로 읽은 경우는 치명적 오독에도 넣는다** |
| p50 / p95 지연 | |

**오독과 미인식을 절대 합치지 말 것.** 이유는 셀 벤치 README 에 있다.

#### 가장 중요한 출력 — 축별 분해

전체 정확도 한 줄은 쓸모가 적다. **변화 축마다 구간을 나눠 정확도를 뽑는다.**

- 여백 0~5% / 5~15% / 15~25%
- 회전 0~3° / 3~6° / 6~8°
- 대비 30~80 / 80~140 / 140~200

**어디서 무너지는지가 이 작업의 결과물이다.**

#### 완료 기준

- 기준선 리포트가 `docs/reports/G17-scene-bench-baseline.md` 에 있다
- 축별 분해 표 세 개가 있다
- 같은 데이터로 두 번 돌려 판정 숫자가 같다
- **`lib/` 변경은 위의 export 한 줄뿐**이다

**절대 하지 말 것**: 결과가 나쁘다고 임계값(`onRatio`, `minSeparability`,
`minBlurScore`, `maxHammingDistance`)이나 기하를 만지지 말 것. 나쁜 숫자가 결과물이다.

**보고서**: `docs/reports/G17-scene-bench-baseline.md`

---

### G18 — 셀 벤치 실패 표본 층화

**상태**: 대기 · 독립. 아무 때나

G15 에서 드러난 하네스 결함이다. `--dump-failures 100` 이 클래스 순서대로 채워져
**100건이 전부 클래스 `00` 에서 소진된다.** 실패 표가 튜닝에 쓸모가 없다.

대상: `tools/ocr_bench/bin/cell_bench.dart` 의 `_Report.render`

할 일: 실패 사례를 **클래스별로 고르게** 뽑는다. `--dump-failures N` 이면 클래스마다
`N / 클래스수` 건씩. 부족한 클래스가 있으면 남는 몫을 다른 클래스가 채운다.

같은 파일의 `--limit` 이 이미 간격 표본을 쓴다(`stride`). 그 주석에 이유가 적혀
있으니 같은 방식으로 맞출 것.

완료 기준: `--dump-failures 110` 이 11개 클래스 전부에서 사례를 보여준다.
`flutter analyze` 무경고.

**보고서**: `docs/reports/G18-failure-stratification.md`

---

### G19 — 셀 정규화를 플래그 뒤에 구현하고 A/B 측정

**상태**: 대기 · **G17 뒤에 할 것**

G15 가 찾은 것: `0`→`H` 683건, `8`→`H` 555건. 전부 **A(위 가로)와 D(아래 가로)를
놓쳐서** 생긴다. 원인은 셀의 세로 범위가 숫자의 경계가 아니라 **ROI 전체 높이**라는
것이다(`MeterProfile.uniform` 이 `top: 0, height: 1` 로 자른다). 숫자가 ROI 상단
3~15% 에 닿지 않으면 A 박스는 여백을 잰다.

#### 무엇을 만드나

`SegmentSampler` 에 **셀 안에서 전경 경계 상자를 구해 기하를 거기에 맞추는** 경로를
추가한다.

규칙 — **이 숫자를 그대로 쓸 것**:

1. 셀 안에서 전경 픽셀의 경계 상자를 구한다.
2. 경계 상자 높이가 셀 높이의 **40% 미만**이면 정규화하지 않고 **기존 경로로**
   떨어진다(숫자가 아닐 가능성이 높다).
3. 경계 상자 폭이 셀 폭의 **95% 초과**면 이웃 자릿수가 걸쳐 든 것으로 보고
   정규화하지 않는다.
4. 그 외에는 `SegmentGeometry` 의 비율을 **셀이 아니라 경계 상자에** 적용한다.
   경계 상자 둘레에 **2%** 여유를 준다.

#### 반드시 지킬 것 — 이 작업의 핵심

- **플래그 뒤에 넣고 기본값을 `false` 로 둔다.** `SegmentSampler.sample()` 에
  `bool normalizeToInk = false` 인자를 더하는 방식이면 된다.
- **기본값을 바꾸지 말 것.** 켜는 결정은 사람이 한다. 숫자가 아무리 좋아도
  기본값을 건드리면 이 작업은 실패다.
- 기존 테스트가 **하나도 안 바뀌고** 통과해야 한다. 바뀌면 기본 경로를 건드린 것이다.

#### 측정

셀 벤치와 장면 벤치 **양쪽에** `--normalize-ink` 플래그를 붙이고, 켠 것과 끈 것을
**나란히** 표로 낸다. 최소한 이 네 줄:

| | 끔 | 켬 |
|---|---|---|
| 완전일치 | | |
| 치명적 오독 | | |
| 미판독 | | |
| `0`→`H` · `8`→`H` 건수 | | |

#### 완료 기준

- 새 경로에 유닛 테스트가 붙는다(정규화 됨 / 40% 미만이라 안 됨 / 95% 초과라 안 됨)
- 기본값 `false` 유지, 기존 테스트 전부 그대로 통과
- A/B 표가 보고서에 있다
- `flutter analyze` 무경고

**보고서**: `docs/reports/G19-ink-normalization.md`

---

## 5. 넘기기 전에 사람이 정해야 하는 것

아래는 GLM 에게 주지 않는다. 단순 작업처럼 보이지만 판단이 필요하다.
**정식 목록과 이유는 [`CLAUDE_TASKS.md`](CLAUDE_TASKS.md) 로 옮겼다** — 여기 남긴
것은 "왜 이게 GLM 작업이 아닌가"의 요약이다. 결정이 끝나서 위임 가능해지는 조건은
`CLAUDE_TASKS.md` §4 에 있다.

- **`dart format` 전면 적용** — Dart 3.12 의 새 포매터가 **74개 파일**을 다시
  쓴다. 기능 변화는 없지만 diff 가 거대해져 `git blame` 이 통째로 밀린다.
  할지 말지, 한다면 언제 할지를 먼저 정해야 한다.
- **OCR 관련 전부** — 값을 잘못 읽는 방향의 버그가 나오는 영역이다.
  - **§4.1(G16~G19)이 예외다.** 판단을 지시서 안에 미리 박아 넣고(숫자·규칙 명시),
    판독 동작을 바꾸는 것은 플래그 뒤에 기본값 꺼짐으로 두는 조건으로 위임했다.
    **플래그를 켜는 결정과 임계값·기하를 정하는 것은 여전히 사람 몫이다.**
- **동기화 엔진** — `test/data/sync_engine_test.dart` 가 고정한 판단들이
  하나씩 다 이유가 있다.
- **인증·보안** — 세션 저장, 로그인 게이트.
- **소수점 표기** — `GlucoseUnit.format()` 이 `toStringAsFixed` 를 써서 항상
  점을 찍는다. 독일어·프랑스어·스페인어권은 쉼표를 쓰므로 스위스 사용자가
  `7,6` 을 입력하고 `7.6` 을 보게 된다. 입력은 안전하다(검증기가 쉼표를 점으로
  바꾼다). 고치려면 `intl` 의 `NumberFormat` 을 표시 계층에서 써야 하는데,
  단위 표기는 이 앱에서 가장 위험한 자리라 사람이 볼 일이다.
- **지원 언어를 더 늘릴지** — 기반은 갖춰져 있다(6개 언어, 각 100키). 새 언어는
  ARB 파일 하나를 채우면 된다. 다만 이 앱의 문구에는 의료 면책, "목표 범위 안/밖",
  "건수 기준이지 시간 기준이 아니다" 처럼 **잘못 번역되면 의미가 달라지는
  문장**이 섞여 있다. 기계 번역을 그대로 넣을 수 없고, 언어마다 검토자가
  필요하다. **어느 언어를 추가할지는 정해졌고(G8), 남은 것은 의료 문구 검토다** —
  G8 보고서의 역번역 표를 사람이 읽고 승인해야 병합할 수 있다.
  - 2026-08-21: DeepL 역번역 교차검증 84/84 통과 후 병합 완료. 시장 노출 전
    원어민 스팟 검토(어감)는 남아 있다.
