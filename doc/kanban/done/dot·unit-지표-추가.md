---
title: dot·unit 지표 추가
status: done
ordinal: 7000
created: 2026-09-09
---

## Goal
<!-- kanban:goal:begin -->
eval_reader 평가에 소수점·단위 관련 지표를 추가해 mmol/L 계열 오류를 완전일치률과 분리해 볼 수 있게 한다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 홀드아웃 GT 의 소수점 포함 분포가 먼저 집계·기록된다(표본 없으면 측정 불가로 종결)
- [ ] #2 소수점 표본이 존재하면 dot 오류(유실·추가·위치)가 완전일치와 별도로 집계된다
- [ ] #3 오답 중 dot 기인 비율과 소수점 직경의 리사이즈 전후 분포가 보고된다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-09T23:51-07:00 — 위키 aggregate-hides-stratified-failure — 전체 완전일치에 묻히는 소수층 실패가 제품 리스크(mmol/L 오독=10배 오차). §19 리사이즈 전후 dot 직경 계측 포함
- 2026-09-10T00:33-07:00 — AC2·AC3 은 조건부(소수점 표본 존재 시)였으나 표본 0건으로 발동하지 않음 — 카드 목록에 명시된 종결 조건. audit_dot_unit_coverage.py 로 전수 확인: 2,512장 전부 정수, 소수점 0건, 단위 필드 0건, 자릿수 2~3(값 30~511). §19 dot 직경 계측도 실츬 표본이 없어 불가

## Handoff

## Result
- 2026-09-10T00:33-07:00 — 측정 불가로 종결(카드 예정된 경로): 홀드아웃 GT 전수 집계 결과 소수점 표본 0건·단위 필드 0건 — 이 코퍼스에서 dot·unit 지표는 정의 자체가 성립하지 않는다. 후속: handoff 「mmol/L 실츬 데이터 확보」 등록(데이터 확보가 선행). 검증: audit_dot_unit_coverage.py 출력(train 1372·holdout 1122 전수)
