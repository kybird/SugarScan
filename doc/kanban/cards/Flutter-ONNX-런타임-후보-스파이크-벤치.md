---
title: Flutter ONNX 런타임 후보 스파이크 벤치
status: todo
ordinal: 14000
created: 2026-09-11
---

## Goal
<!-- kanban:goal:begin -->
온디바이스 CTC 리더를 올릴 Flutter ONNX 런타임 패키지를 고르기 위해, 후보들의 로드·추론 성능과 앱 크기 영향을 실기기에서 숫자로 잰다. 선택 자체는 사람이 한다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 후보 2~3개 각각에 대해 모델 로드 시간·추론 p50/p95·피크 메모리·APK 증가량이 표로 나온다
- [ ] #2 측정은 실기기(Redmi Note 11 / Android 14)에서 이뤄지고 기기·빌드 모드가 보고서에 적힌다
- [ ] #3 sugarScan 본체 pubspec.yaml 은 변경되지 않는다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-11T11:16-07:00 — 새 패키지 도입은 승인제다. 그래서 이 카드는 '도입'이 아니라 '측정'이다 — 별도의 임시 Flutter 프로젝트를 scratch 에 만들어 거기서만 의존성을 추가한다. sugarScan 의 pubspec.yaml·pubspec.lock·android/ 설정은 한 줄도 바꾸지 않는다. 특히 android/gradle.properties 의 kotlin.incremental=false 와 compileSdk 37 / minSdk 26 / AGP 9.1.1 조합은 전부 이유가 있는 값이다(CLAUDE.md).
- 2026-09-11T11:16-07:00 — 후보: onnxruntime_flutter, flutter_onnxruntime 등 pub.dev 에서 유지보수가 살아 있는 것 2~3개. 각 후보의 라이선스를 먼저 확인해 보고서에 적을 것 — GPL/AGPL 계열이면 그 자리에서 탈락이고 벤치를 돌릴 필요도 없다(docs/LICENSES.md 가 정본).
- 2026-09-11T11:16-07:00 — 모델은 docs/DONE.md G28·G31 이 가리키는 ONNX 내보내기 산출물을 쓴다. 없으면 거기서 멈추고 handoff — 임의로 새로 내보내지 말 것(내보내기 파라미터가 성능 수치를 바꾼다).
- 2026-09-11T11:16-07:00 — OCR 은 단말에서만 돈다는 규칙은 여기서도 그대로다. requiresNetwork 인 런타임·원격 추론 옵션은 후보에서 제외한다.

## Handoff

## Result
