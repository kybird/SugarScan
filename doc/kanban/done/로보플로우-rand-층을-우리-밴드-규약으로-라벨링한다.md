---
title: 로보플로우 rand 층을 우리 밴드 규약으로 라벨링한다
status: done
ordinal: 74000
created: 2026-09-21
---

## Goal
<!-- kanban:goal:begin -->
규약 차이 측정의 핵심층(무작위 50장)을 사람이 우리 밴드 규약으로 라벨링해 새 검출기 평가에 쓸 정본을 만든다
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 rf_band_boxes.jsonl 에 rand 층 50장 각각 quad 또는 skip 기록이 존재한다
- [x] #2 라벨링이 사람 손으로 됐다 — 무인 루프가 이 카드를 집지 않는다(REVIEW 대기)
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-22T13:05-07:00 — RESUMED: 조건 충족: 사람이 2026-09-22 /rfband 화면에서 rand 50장 전량 라벨링 완료(본인 확인). 검증: rf_band_boxes.jsonl 50행 — rand 50장 전부 quad 기록·skip 0·fail 층 오염 0, 상자 가로세로비 중앙 1.61(기존 라벨 1.64~1.70 분포와 일관).

## Handoff
- 2026-09-21T15:20-07:00 — QUESTION: 사람 전용 카드입니다. 웹툴 Roboflow 라벨 화면(/rfband)에서 rand 층 50장을 여유 있을 때 라벨링해 주세요. fail 층은 새 검출기의 실패 장으로 재구성한 뒤에 열 예정이라 지금 하지 않습니다.

## Result
- 2026-09-22T13:05-07:00 — 사람이 웹툴 /rfband 화면에서 rand 층 50장을 우리 밴드 규약(숫자 칸+사방 0.10x숫자높이, 축정렬)으로 직접 라벨링했다(2026-09-22). 검증: rf_band_boxes.jsonl 에 rand 50장 전부 quad 기록(skip 0), fail 층 29장 무오염(층 숨김 스위치로 차단), 가로세로비 중앙 1.61로 기존 band_boxes 277개 분포와 일관. 라벨 파일은 사람 노동 정본으로 git 추적(.gitignore 예외 추가). 이 50장은 로보플로우 분포에서 우리 규약 기준 절대 성적을 재는 정본 표본이 된다 — §20.5(규약 차이 vs 모델 결함)를 가르는 측정의 재료.
