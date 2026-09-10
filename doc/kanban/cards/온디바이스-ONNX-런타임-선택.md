---
title: 온디바이스 ONNX 런타임 선택
status: review
ordinal: 3000
created: 2026-09-09
---

## Goal
<!-- kanban:goal:begin -->
CTC 리더의 온디바이스 추론을 위한 Flutter ONNX 런타임 패키지를 확정하고 모바일 벤치마크 계획을 세운다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 패키지 선택과 벤치마크 시점이 사람 결정으로 확정된다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-10T11:06-07:00 — 사람 판정 2026-09-10 (Claude): flutter_onnxruntime 유지. 근거 — 이미 pubspec.yaml:21 에 ^1.8.3 으로 있고 docs/LICENSES.md 에서 ONNX Runtime MIT 실사가 2026-08-21 에 끝나 있다(flutter_onnxruntime 경유로 명시). onnxruntime_flutter 로 바꾸면 닫힌 라이선스 실사를 다시 열어야 하는데 바꿀 이유가 제시된 바 없다. 성능 근거 없이 의존성을 갈아타지 않는다. 벤치 시점: 통합 직후 실기기 1대에서 재고, 벤치 전에는 패키지를 바꾸지 않는다 — 바꾼 뒤 재면 무엇이 달라졌는지 갈리지 않는다. 벤치가 실제로 문제를 보이면 그때 대안을 연다.

## Handoff
- 2026-09-09T23:43-07:00 — QUESTION: ONNX 방향은 확정됨(86d3dbe, tflite 불가 — docs/DONE.md G28). Flutter ONNX 런타임 패키지를 무엇으로 할지(onnxruntime_flutter · flutter_onnxruntime 등), 모바일 벤치마크(p50/p95·메모리, 강화 프롬프트 §34)를 언제 돌릴지 결정이 필요하다. 새 패키지 도입은 승인제다.

## Result
