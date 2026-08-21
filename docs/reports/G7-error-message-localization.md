# G7 — 사용자에게 예외 원문을 보여 주지 않기

- 브랜치: `glm/G7-error-message`
- 커밋: `4d62001` (코드) + 보고서 커밋 (이 파일)
- 상태: 완료

## 무엇을 했나

- `lib/l10n/app_en.arb` / `app_ko.arb` — `readingsLoadFailed` 키 추가
  (en "Couldn't load your readings." / ko "기록을 불러오지 못했습니다.",
  지시서가 지정한 문구 그대로).
- `lib/features/dashboard/dashboard_screen.dart` — `_RecentList` 오류 분기의
  `Text('$error')` 를 `readingsLoadFailed` 문구로 교체. 원문은 `debugPrint` 로
  로그에 남긴다.
- `lib/features/history/history_screen.dart` — 같은 교체. `debugPrint` 로그 추가.
- `lib/l10n/generated/` — `flutter gen-l10n` 재생성.
- `test/features/history_screen_test.dart` — 오류 상태 테스트 추가(안내 문구
  표시 · 예외 원문 미표시 · 로그에 원문 남음 · 빈 상태 문구와 미혼동).
- `test/features/dashboard_screen_test.dart` — 신규. 오류 상태에서 번역된
  안내 문구만 보이는지 확인.

## 왜 그렇게 했나

- 원인·조치를 추측하는 문구("네트워크를 확인하세요" 등)는 넣지 않았다. 이
  경로는 로컬 DB 읽기 실패이고 네트워크와 무관하다(지시서 주의사항).
- 로그 검증을 위해 `debugPrint` 를 테스트에서 잠시 바꿨는데, flutter_test 는
  테스트 종료 시점에 foundation 디버그 변수 불변성을 검사하고 `addTearDown`
  복원은 그보다 늦게 돌아 실패했다. 본문 안 `try/finally` 로 복원하는 방식으로
  고쳤고, 이유를 코드 주석에 적었다.
- `debugPrint` 는 `material.dart` import 로 그대로 쓸 수 있어 별도 import 는
  붙이지 않았다(analyzer 가 unnecessary_import 로 지적).

## 검증

flutter gen-l10n → 생성 성공
flutter analyze   → No issues found! (ran in 3.8s)
flutter test      → All tests passed! (333 tests)
grep -rn "Text('\$error" lib/ → 0건

## 건드리지 않고 남긴 것

- 빈 상태(`historyEmpty`) 화면은 그대로다 — 0건과 읽기 실패가 다른 화면인
  점을 테스트로 고정했다.
- 다른 화면의 오류 경로(스캔·동기화 등) — 지시 범위가 두 화면뿐이라 건드리지
  않았다. 스캔 화면에는 이미 번역된 오류 문구가 있다.

## 막힌 것

없음
