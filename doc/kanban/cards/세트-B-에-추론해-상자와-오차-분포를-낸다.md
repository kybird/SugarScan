---
title: 세트 B 에 추론해 상자와 오차 분포를 낸다
status: todo
ordinal: 54000
created: 2026-09-16
depends_on: ["YOLOX 를 혈당 숫자 상자로 파인튜닝한다"]
milestone: 합성만으로 사진에서 값까지 한 번 통과시킨다
---

## Goal
<!-- kanban:goal:begin -->
검출기가 처음 보는 세트 B 에 추론해 예측 상자를 jsonl 로 낸다. 같은 장의 정답 상자와 비교해 오차 분포(변별 치우침·크기비·포함률)를 낸다 — 이 분포가 리더 학습 재료이자, 나중에 검출기 사양을 정하는 근거다. 지어낸 흔들기 폭을 쓰지 않는 이유가 여기 있다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 B 1000장 전량에 상자가 나온다(건너뜀 0)
- [ ] #2 정답 대비 포함률·넓이비·변별 치우침의 분위수가 출력된다
- [ ] #3 포함률이 낮은 최악 10장을 시트로 그려 눈으로 확인한다
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
