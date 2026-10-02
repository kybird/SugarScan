---
title: BandNet 스케일 재정렬 2차 — TG 재굽기 재학습
status: todo
ordinal: 36000
created: 2026-10-02
milestone: 검출기 실사진 성능 개선
---

## Goal
<!-- kanban:goal:begin -->
TF 1차 학습의 두 병을 데이터 재정렬로 고친다(사람 승인 2026-09-28). ①줌 하한 0.25 복원 — TF의 초원경 밴드 라벨 673장(화면 0.2~3%, 실촬 정답 최소 5.1%)이 가르친 스케일 혼동으로 2319·2414 미세상자 오탐(score 0.9) 발생. ②mixed device 비중 0.7→0.5 — 클로즈업 면적 30%+가 1.9%뿐이어 2317(LCD 클로즈업) 미검출. 구조·스텝은 1차와 동일(640·width1.5·16,000스텝)해 데이터 축만 가른다. 스케일 게이트(면적 2% 미만 거부)는 이미 eval·predict에 적용.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 #1 TG 30,000장 굽기 완료 — 줌 하한 0.25 반영 확인(면적 2% 미만 라벨 급감)과 클로즈업 상위 증가(면적 30%+ 비중)를 COCO 주석으로 검증 — #2 학습 후 순수 수동 220장 홀드아웃에서 1차(atone_tf640w15·게이트 후 IoU 0.8865) 대비 성적 보고 — #3 1차 회귀 3종(2319·2414 오탐·2317 미검출·Performa Nano 열화)의 소멸/잔존을 각각 보고
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
