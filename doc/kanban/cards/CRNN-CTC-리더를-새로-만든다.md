---
title: CRNN CTC 리더를 새로 만든다
status: todo
ordinal: 55000
created: 2026-09-16
milestone: 합성만으로 사진에서 값까지 한 번 통과시킨다
---

## Goal
<!-- kanban:goal:begin -->
리더는 2026-09-11 재구축에서 폐기됐고 지금 없다. 작은 CRNN + CTC 로 새로 만든다. charset 은 0~9 만 — HI/LO·소수점은 이 마일스톤 밖이다. 크롭을 펴지 않는다: 기울어진 숫자를 그대로 읽게 학습한다. 구현만 하는 카드이고 본 학습은 다음 카드다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 50장을 과적합시켜 완전일치 100% 가 나온다(구현이 학습되는지 확인. 성적이 아니다)
- [ ] #2 입력 크기와 charset 이 코드 한 곳에 상수로 있고 주석에 이유가 있다
- [ ] #3 flutter 와 무관한 assets_dev/train 안에만 있다
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
