---
title: CTC 리더 ONNX 내보내기 파리티
status: todo
ordinal: 6000
created: 2026-09-09
---

## Goal
<!-- kanban:goal:begin -->
CTC 리더(Keras)를 ONNX 로 내보내고 PC 의 ONNX Runtime 추론이 기존 TF 추론과 같은 판독을 내는지 검증해, 온디바이스 전환의 모델 측 준비를 끝낸다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 assets_dev/train 에 내보내기 스크립트가 생기고 reader_model 체크포인트에서 .onnx 가 생성된다
- [ ] #2 홀드아웃 표본(최소 300장)에서 TF 대 ONNX 판독 완전일치율이 보고된다(전처리·디코딩 동일)
- [ ] #3 모델 입력 전처리 규격(정규화·리사이즈·채널 순서)이 문서 한 곳에 명시된다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-09T23:51-07:00 — 런타임 패키지 선택은 handoff 「온디바이스 ONNX 런타임 선택」 — 이 카드는 PC 파리티까지(방향 확정 86d3dbe). TF 실행은 conda run 필수. §36 전처리 규격 명시 포함

## Handoff

## Result
