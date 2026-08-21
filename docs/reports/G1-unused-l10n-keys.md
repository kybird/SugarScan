# G1 — 쓰이지 않는 l10n 키 정리

- 브랜치: `glm/G1-unused-l10n`
- 커밋: `cc8d02f` (코드) + 보고서 커밋 (이 파일)
- 상태: 완료

## 무엇을 했나

- `lib/l10n/app_en.arb` — `unitLabel`, `unitMgdl`, `unitMmoll`, `actionRetry` 4개 키 삭제
- `lib/l10n/app_ko.arb` — 같은 4개 키 삭제
- `lib/l10n/generated/` — `flutter gen-l10n` 재생성 (수동 수정 없음)
- `docs/reports/G1-unused-l10n-keys.md` — 이 보고서

## 왜 그렇게 했나

- 지시서가 지정한 4개 키만 지웠다. `readingRestored` 는 미사용으로 스캔에 걸리지만
  G2 에서 쓰기로 되어 있어 그대로 남겼다 (en 160행, ko 84행).
- 두 키 모두 `@` 메타데이터가 없는 것을 삭제 전에 확인했으므로 메타데이터 정리는
  필요하지 않았다.

## 검증

flutter gen-l10n  → 생성 성공. `grep -c "unitLabel|unitMgdl|unitMmoll|actionRetry" lib/l10n/generated/app_localizations.dart` → 0
키 수 검증          → python json 파싱: app_en.arb 99개, app_ko.arb 99개 (동일)
flutter analyze    → No issues found! (ran in 4.6s)
flutter test       → All tests passed! (326 tests)

## 건드리지 않고 남긴 것

- `readingRestored` — 미사용이지만 G2 에서 사용 예정이라 지시대로 유지.
- `readingRestored` 외에도 생성 코드에만 존재하는 키가 있는지는 조사 범위 밖이라
  확인하지 않았다.

## 막힌 것

없음
