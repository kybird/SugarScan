# G4 — 죽은 TODO 주석 정리

- 브랜치: `glm/G4-dead-todo`
- 커밋: `52fd501` (코드) + 보고서 커밋 (이 파일)
- 상태: 완료

## 무엇을 했나

- `android/app/build.gradle.kts` — 25줄의 `TODO: Specify your own unique Application
  ID` 주석 한 줄만 삭제했다. `applicationId = "com.kybirdlabs.sugarscan"` 과 그
  아래 안내 주석, 39줄의 서명 TODO 는 그대로.

## 왜 그렇게 했나

- 지시서대로 해결된 TODO(애플리케이션 ID 확정)만 지웠다. 39줄의 release 서명
  TODO 는 아직 유효하므로 남겼다.
- §2.6 의 빌드 설정값(compileSdk 37, minSdk 26, desugaring, AGP/Gradle 버전)은
  전혀 건드리지 않았다.

## 검증

flutter build apk --debug → √ Built build\app\outputs\flutter-apk\app-debug.apk (Running Gradle task 'assembleDebug'... 23.4s)
flutter analyze        → No issues found! (ran in 3.8s)
flutter test           → All tests passed! (329 tests)

빌드 중 플러그인들의 "Built-in Kotlin" 관련 안내가 출력되지만 이는 수정 전에도
나오는 기존 경로의 안내문이며 빌드에는 영향이 없다.

## 건드리지 않고 남긴 것

- 39줄 release 서명 TODO — 아직 해야 할 일이라 유지.
- 빌드 출력의 플러그인 Kotlin 마이그레이션 안내 — §2.6 범위 밖이라 그대로 둠.

## 막힌 것

없음
