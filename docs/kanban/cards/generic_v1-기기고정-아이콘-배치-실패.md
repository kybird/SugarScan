---
title: generic_v1 기기고정 아이콘 배치 실패
status: todo
ordinal: 47000
created: 2026-11-15
milestone: 무소속
---

## Goal
<!-- kanban:goal:begin -->
generic_v1 이 선언한 기기고정 아이콘 battery·mem-flag·triangle 이 배치에 실패해 빠지는 비율을 줄인다
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 500장 재현에서 기기고정 아이콘 드롭이 0 에 가깝거나 근거 있는 상한 안으로 들어간다
- [ ] #2 배치 수정이 다른 프로파일의 요소 배치를 바꾸지 않음을 같은 시드 비교로 보인다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-11-15T00:23+09:00 — 무엇을 할 것: synth_panel Placer 의 generic_v1 아이콘 배치 실패 원인을 밝히고 고친다 / 건드리지 말 것: 검출기·리더 학습과 무관하게 이 수정은 양성 픽셀을 바꾼다 — 굽기 전에만 넣을 것 이미 구운 코퍼스와 섞지 말 것 / 어디서 틀리기 쉬운가: 드롭을 검증기 문턱으로 덮는 것은 금지 실제 배치를 고친다 2026-11-15 실측 battery 31 50 mem-flag 23 50 triangle 14 50

## Handoff

## Result
