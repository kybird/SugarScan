---
title: Flutter ONNX 런타임 후보 스파이크 벤치
status: review
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
- 2026-09-11T23:58-07:00 — 판정 2026-09-12 — 새 리더가 선 뒤로 미룬다. Notes 가 지시하는 G28·G31 ONNX 내보내기 산출물은 폐기된 옛 리더의 것이라 지금 벤치를 돌리면 버릴 숫자를 만든다. 실기기(Redmi Note 11) 측정은 사람 손이 필요하므로 무인 에이전트는 이 카드를 잡지 마라. 새 리더의 ONNX 내보내기가 나온 뒤 AC 를 다시 쓴다.

## Handoff
- 2026-09-11T20:08-07:00 — QUESTION: 두 가지를 사람이 정해야 한다: (1) AC#2 가 실기기(Redmi Note 11) 측정을 요구하는데 무인 에이전트는 물리 기기가 없어 수행 불가 — 벤치를 사람이 직접 돌리는 시점/방법을 정해야 한다. (2) Notes 가 지시하는 G28·G31 ONNX 내보내기 산출물은 폐기된 옛 리더의 것인데, 런타임 스파이크를 그 파일로 지금 돌릴지 새 리더 내보내기가 나올 뒤로 미룰지. 참고: 2026-09-11 무인 세션의 오풀(pick --help 실행)로 클레임이 찍혀 반납한다.

## Result
