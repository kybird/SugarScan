---
title: YOLOX 를 혈당 숫자 상자로 파인튜닝한다
status: todo
ordinal: 53000
created: 2026-09-16
depends_on: ["합성을 YOLOX COCO 형식으로 내보낸다"]
milestone: 합성만으로 사진에서 값까지 한 번 통과시킨다
---

## Goal
<!-- kanban:goal:begin -->
기존 gmscreen 체크포인트(화면 검출, 2026-08-28)에서 출발해 클래스를 혈당 숫자 영역 하나로 바꿔 세트 A 로 파인튜닝한다. 출력은 축정렬 상자다 — YOLOX 가 원래 내는 형식이고 사람 밴드 라벨 277장과도 같은 형식이라 나중에 실촬로 재평가할 수 있다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 학습이 끝나고 체크포인트가 저장된다. 학습 시간과 에폭 수를 카드 Note 에 기록한다
- [ ] #2 세트 A 검증 분할에서 mAP 가 출력된다(수치는 판정이 아니라 기록)
- [ ] #3 세트 C 10장에 추론해 상자를 그려 눈으로 확인 — 숫자를 감싼다
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
