---
title: 합성을 YOLOX COCO 형식으로 내보낸다
status: todo
ordinal: 52000
created: 2026-09-16
milestone: 합성만으로 사진에서 값까지 한 번 통과시킨다
---

## Goal
<!-- kanban:goal:begin -->
synth_panel 이 구운 코퍼스를 기존 gmscreen 학습 설정이 그대로 읽는 COCO 형식으로 내보낸다. 상자는 매니페스트의 quad(워프 후 밴드 쿼드)의 축정렬 외접 상자 하나, 클래스 하나. 세트 A(학습 1000) · B(리더용 1000) · C(평가 300)를 서로 다른 시드로 굽는다 — B 는 검출기가 처음 보는 장이어야 리더가 배포와 같은 상자를 본다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 gmscreen 과 같은 디렉터리 구조(annotations/instances_train2017.json + train2017/)로 세 벌이 생긴다
- [ ] #2 어노테이션 수 = 이미지 수 (장당 상자 하나)
- [ ] #3 상자를 원본에 그려 10장을 눈으로 확인 — 숫자가 상자 안에 전부 들어온다
- [ ] #4 세 세트의 시드가 서로 다르고 파일에 기록돼 있다
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
