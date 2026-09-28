---
title: BandNet 재학습 묶음 — 단위 네거티브 + 640 + width 1.5 + 3만장
status: todo
ordinal: 37000
created: 2026-09-27
depends_on: ["밴드 라벨 규약 순회 — 수선 8장 + 걸침 감사 235장"]
milestone: 검출기 실사진 성능 개선
---

## Goal
<!-- kanban:goal:begin -->
순수 합성 학습 안에서 atone_s0 실사진 홀드아웃(IoU 중앙 0.8532)을 끌어올린다. ft_bandnet_v1 실사진 파인튜닝은 폐기(사람 결정 2026-09-27). 처방 4종을 한 번에: ① 합성에 '단위 줄은 밴드 밖' 네거티브(높이 과대=단위 흡수 오인의 직접 치료, 진단 doc/raw/2026-09-27.md Case 3) ② 입력 416→640 ③ width 1.0→1.5 ④ 합성 1.6만→3만장. 채점: 순수 수동 라벨 홀드아웃(eval_band_real --exclude-coco --exclude-accepted). GPU: supertonic-studio 프로세스 종료 대기.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 #1 걸침 순회 완료 뒤 재생성한 깨끗한 라벨로 홀드아웃 채점 — #2 4종 변경을 묶어 1회 학습, atone_s0 대비 IoU 중앙·포함률1.0 개선 보고 — #3 변경별 기여를 분리해 볼 수 있는 근거(스텝 로그·평가 jsonl) 커밋
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
