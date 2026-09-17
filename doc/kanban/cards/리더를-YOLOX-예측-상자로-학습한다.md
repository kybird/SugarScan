---
title: 리더를 YOLOX 예측 상자로 학습한다
status: todo
ordinal: 56000
created: 2026-09-16
depends_on: ["세트 B 에 추론해 상자와 오차 분포를 낸다","CRNN CTC 리더를 새로 만든다"]
milestone: 합성만으로 사진에서 값까지 한 번 통과시킨다
---

## Goal
<!-- kanban:goal:begin -->
세트 B 의 **예측 상자**로 자른 크롭과 값 라벨로 리더를 학습한다. 정답 상자로 자르지 않는다 — 배포 때 리더가 받는 것은 검출기 출력이고, 그 오차는 무작위가 아니라 구조적이라 정답 크롭으로 배우면 그 구조를 못 배운다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 학습이 끝나고 체크포인트가 저장된다. 학습 시간을 카드 Note 에 기록한다
- [ ] #2 세트 B 의 분리된 검증 몫에서 완전일치율이 출력된다
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
