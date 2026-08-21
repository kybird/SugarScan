# G2 — 삭제 되돌리기에 확인 문구 붙이기

- 브랜치: `glm/G2-restore-confirmation`
- 커밋: `01d12b8` (코드) + 보고서 커밋 (이 파일)
- 상태: 완료

## 무엇을 했나

- `lib/features/history/history_screen.dart` — `_delete` 안 `SnackBarAction.onPressed` 를
  `async` 로 바꾸고, `repository.restore(...)` 를 `await` 한 뒤 `readingRestored`
  스낵바를 띄운다. 아웃박스 경유 주석과 동작은 그대로.
- `test/features/history_screen_test.dart` — 신규 위젯 테스트. 기록 1건 → 스와이프
  삭제 → "Undo" 탭 → 목록에 기록이 돌아오고 "Reading restored" 문구가 뜨는 것까지 확인.

## 왜 그렇게 했나

- `onPressed` 안에서 `context` 를 쓰지 않고, `_delete` 머리에서 이미 잡아 둔
  `l10n`·`messenger` 를 재사용했다. `await` 너머로 `BuildContext` 를 들고 가는
  문제를 원천적으로 피하는 방식이고, 같은 파일의 `_edit` 이 쓰는 패턴과 같다.
- 테스트에서 시계를 한 번에 크게 넘기면(pump(1200)) Dismissible 의 퇴장 → 수축 →
  onDismissed → 비동기 삭제 → 스낵바 등장의 연쇄가 중간에 끊겨 스낵바가 잡히지
  않았다. 300ms 씩 여러 프레임으로 넘기는 방식으로 통과시켰고, 그 이유를 코드
  주석에 적어 두었다.

## 검증

flutter analyze  → No issues found! (ran in 3.7s)
flutter test     → All tests passed! (327 tests)

## 건드리지 않고 남긴 것

- 첫 스낵바("Reading deleted")의 문구·지속시간은 그대로다.
- 되살리기가 아웃박스를 거치는 동작(`repository.restore` 내부)은 손대지 않았다.

## 막힌 것

없음
