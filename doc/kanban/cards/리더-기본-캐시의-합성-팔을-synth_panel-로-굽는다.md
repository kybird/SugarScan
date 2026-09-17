---
title: 리더 기본 캐시의 합성 팔을 synth_panel 로 굽는다
status: review
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
- 2026-09-17T00:14-07:00 — QUESTION: 무인 루프의 실행 제약과 정면으로 부딪혀 손대지 않고 세운다. 이번 세션 킥오프의 '절대 하면 안 되는 것' 에 'build_cache_v2.py 로 기본 캐시 다시 굽기' 와 '공유 캐시 train_device/data_cache_v2.npz 에 쓰기' 가 명시돼 있는데, 이 카드의 AC#1 은 기본 캐시(data_cache_v2.npz)의 합성 배열을 synth_panel 산출로 바꾸라는 것이라 굽기가 작업의 전부다. AC#4 가 '새 경로에 굽는다' 를 요구하므로 공유 캐시를 덮어쓰지 않는 길은 열려 있지만, 그래도 build_cache_v2 를 돌려 캐시를 굽는 행위 자체가 금지 목록에 있다. 그래서 한 줄도 실행하지 않았다. 사람이 정할 것 둘: (1) 새 경로로 굽는 것은 허용인가 — 허용이면 다음 무인 세션이 바로 집을 수 있다. (2) 그 전에 순서를 다시 볼 필요가 있다 — 리더가 2026-09-11 에 폐기됐고 새 리더(reader_crnn.py)는 어젯밤 구현됐는데 npz 캐시가 아니라 COCO 세트에서 직접 크롭해 학습한다. 즉 새 리더는 data_cache_v2.npz 를 쓰지 않는다. 이 카드가 고치려는 '기본 캐시' 를 앞으로 누가 쓰는지가 먼저 정해져야 굽는 보람이 있다. 아무도 안 쓰면 이 카드는 접는 쪽이 맞다. 참고로 디스크 비용도 작지 않다 — 기존 캐시 파일이 각 1.3GB 이고 이미 일곱 벌이 있다.

## Result
