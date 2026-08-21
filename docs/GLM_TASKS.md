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

## 5. 넘기기 전에 사람이 정해야 하는 것

아래는 GLM 에게 주지 않는다. 단순 작업처럼 보이지만 판단이 필요하다.

- **`dart format` 전면 적용** — Dart 3.12 의 새 포매터가 **74개 파일**을 다시
  쓴다. 기능 변화는 없지만 diff 가 거대해져 `git blame` 이 통째로 밀린다.
  할지 말지, 한다면 언제 할지를 먼저 정해야 한다.
- **OCR 관련 전부** — 값을 잘못 읽는 방향의 버그가 나오는 영역이다.
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
