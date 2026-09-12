---
title: 프로파일 확장 — ACCU-CHEK Active 와 화살표 다종
status: done
ordinal: 33000
created: 2026-09-11
depends_on: ["합성을 물리 패널 기준으로 재구성"]
---

## Goal
<!-- kanban:goal:begin -->
프로파일 10종 중 화살표가 1종에만 있고 ACCU-CHEK Active 는 프로파일 자체가 없다. 실사진 근거가 있는 기기를 더 넣는다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 ACCU-CHEK Active 프로파일이 실사진 근거 id 와 함께 추가된다
- [x] #2 화살표를 가진 프로파일이 2종 이상이 된다 — 실사진에서 화살표가 관찰되는 기기를 근거로
- [x] #3 프로파일마다 숫자 칸 수가 3으로 고정되지 않는다 — 코퍼스 2자리 비율 18%를 반영해 칸 수와 켜지는 자리를 흔든다
- [x] #4 추가한 프로파일마다 렌더 결과를 실사진과 나란히 놓은 대조 이미지를 남긴다
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
- 2026-09-12T12:48-07:00 — ff26cac 위 411c16f(glm/detector). AC#1 Active 프로파일 추가(근거 glucose_batch1/1329·batch2/2502·2513·2519 육안 4장 — 상단 시간·날짜 줄/중앙 대형 숫자/하단 mg/dL/베젤 Active). AC#2 화살표 프로파일 2종 달성: accuchek_instant(곡선·우측) + gluneo_plus 신설(tri-down 하단 좌측 — 1435/1438/1440/1449 4장 전 관찰). AC#3 slots 튜플 지원(generic_v1=(2,3))+값 샘플을 2자리 20.5% 실측 비율로(카드 본문 18%는 이번 전수 실측에서 20.5%). AC#4 대조 이미지 docs/reports/profile-expansion-compare-2026-09-12.png(실사진 3장 vs 합성 3장 나란히, Active 혼합 극성 반영). 회귀: 전 12 프로파일 렌더 통과·300장 재검증 하드 0. 보고서 docs/reports/profile-expansion-2026-09-12.md
