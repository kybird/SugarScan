---
title: 검증기가 합성 캔버스를 실측 GM 쿼드와 비교한다 — 기준이 다르다
status: todo
ordinal: 48000
created: 2026-09-13
---

## Goal
<!-- kanban:goal:begin -->
validate_synth_panel 의 종횡비 줄은 합성 '캔버스' w/h 를 실측 'GM 쿼드' w/h(measure_panel_stats.collect_aspect, 화면 쿼드)와 나란히 찍는다. 합성에서 GM 쿼드에 해당하는 것은 캔버스가 아니라 유리다 — 캔버스는 유리 + 몸체 마진이다. seed 31000 n=300 에서 캔버스 0.734 vs 유리 0.800, 실측은 0.792 다. 즉 기하는 맞는데 검증기가 다른 물건을 재서 '합성이 실측보다 좁다'는 결론이 계속 나왔고, 그 위에 '프로파일 세트가 모집단을 대표하지 못한다'는 진단까지 얹혔다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 종횡비 비교가 manifest 의 glass_quad 를 쓴다 — 실측과 같은 물건(화면 쿼드)이다
- [ ] #2 밴드 기하 비교도 같은 분모를 쓰는지 확인하고, 다르면 고치거나 무엇에 대한 비율인지 출력에 적는다
- [ ] #3 고친 뒤 seed 31000 n=300 의 종횡비·밴드 4축을 실측과 나란히 다시 인쇄한다
- [ ] #4 캔버스 w/h 도 함께 인쇄한다 — 그 축의 실측 대응물이 무엇인지(또는 없는지) 출력에 적는다
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
