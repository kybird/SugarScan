---
title: mmol/L 실츬 데이터 확보
status: review
ordinal: 10000
created: 2026-09-10
---

## Goal
<!-- kanban:goal:begin -->
소수점 표시를 포함한 mmol/L 실츬 사진 데이터를 확보해 dot 지표·소수점 판독의 측정·학습을 가능하게 한다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 mmol/L 표시 기기의 촬영 장수·기기 기준이 사람 결정으로 확정되고 데이터가 수집된다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-10T00:33-07:00 — audit_dot_unit_coverage.py 실측(2026-09-10): 라벨 2,512장 전부 정수(값 30~511·2~3자리), 소수점 0건·단위 필드 0건 — 현재 코퍼스에서 dot 지표는 측정 불가. 리더 charset 도 0~9 전용이라 소수점 클래스 추가 시 재학습 필요. 강화 프롬프트 §21(실데이터>포토메트릭 증강>복붙>완전합성)

## Handoff
- 2026-09-10T00:33-07:00 — QUESTION: mmol/L 소수점 판독은 현재 측정도 학습도 불가능하다(코퍼스에 소수점 표본 0건·리더 charset 0~9 전용). mmol/L 표시 기기 실츬 사진을 어떤 기기·몇 장 기준으로 확보할지 결정이 필요하다. 확보 전까지 mmol/L 경로는 앱의 규칙 엔진(소수점 채널 직접 검출)만이 유일한 경로다.

## Result
