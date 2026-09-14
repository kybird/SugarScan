---
title: 리더 기본 캐시의 합성 팔을 synth_panel 로 굽는다
status: todo
ordinal: 47000
created: 2026-09-13
depends_on: ["합성 생성이 같은 시드에서 같은 코퍼스를 내게 한다"]
---

## Goal
<!-- kanban:goal:begin -->
build_cache_v2 가 만드는 기본 리더 캐시(data_cache_v2.npz)의 합성 배열은 아직 옛 synth_screens/*.png 를 단순 리사이즈한 것이다. 그 png 는 synth_lcd.render_screen 산출이라 기기 개념도 극성 선언도 단위 규칙도 없다. 2026-09-13 에 build_profiled_cache 는 synth_panel + reader_view 로 옮겼지만 기본 캐시는 그대로다 — 리더를 다시 구울 때 어느 캐시를 쓸지가 갈린다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 합성 배열이 synth_panel.render_panel + reader_view 산출이다 — 실사진 팔과 같은 프레이밍(build_cache_v2.framed_src_rect, BOX_MARGIN 10%)을 통과한다
- [ ] #2 실사진 배열·id 는 바이트 동일하다(md5 대조). 이 카드는 합성만 바꾼다
- [ ] #3 전환 전후 합성 표본 12장을 나란히 저장해 눈으로 비교한다
- [ ] #4 기존 train_device/data_cache_v2.npz 를 덮어쓰지 않는다 — 새 경로에 굽고 어느 것이 정본인지 문서에 적는다
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
