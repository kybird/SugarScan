---
title: 기기 편중 A/B 재실험 — 고유 사진 전량 유지
status: abandoned
ordinal: 11000
created: 2026-09-11
discard_reason: scratch 재구축 결정(2026-09-11, docs/OCR_REBUILD_PLAN.md)으로 무의미해졌다. 이 카드는 옛 리더(pre_best 체크포인트)와 옛 캐시 위에서 편중 재배분 효과를 재는 것인데, 그 모델과 수치를 전부 버리기로 했다. 기기 편중 문제 자체는 남아 있으므로 새 리더가 선 뒤 같은 질문을 다시 세운다.
---

## Goal
<!-- kanban:goal:begin -->
기기 편중 완화가 미학습 기기 성적을 올리는지를, 고유 사진 장수를 줄이지 않은 팔로 다시 잰다. 이전 A/B(2026-09-11)는 두 팔 모두 고유 다양성을 함께 줄여 가설을 깨끗이 시험하지 못했다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 고유 real_train 1,356장을 한 장도 버리지 않는 가중 샘플링 팔이 학습된다
- [ ] #2 대조군(train_device)과 동일한 홀드아웃 1,138장에서 짝비교 McNemar p 가 보고된다
- [ ] #3 이전 A/B 의 B·C 팔 수치와 나란히 놓은 표가 보고서에 있다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-11T11:16-07:00 — 설계(그대로 옮길 것, 정하지 말 것): 팔D = 고유 1,356장 전부 유지 + 기기별 가중 오버샘플. 기기 g 의 사진수 n_g 에 대해 목표 행수 = round(1356 * (1/|G|)) 를 상한 없이 '복제 추가'로만 맞춘다 — 즉 큰 기기의 사진을 빼지 않는다. 총 행수가 1,356 을 넘으므로 epoch 당 스텝이 늘어난다. 스텝 수 교란을 분리하려면 팔D2(총 행수를 1,356 으로 맞추되 큰 기기 사진을 빼는 대신 epoch 를 줄이는 방식)는 만들지 말고, 대신 보고서에 '스텝 수가 늘었다'를 교란으로 명시한다.
- 2026-09-11T11:16-07:00 — 건드리지 말 것: build_device_split.py 의 시드 20260911 과 홀드아웃 구성. 홀드아웃 배열은 train_device 캐시에서 그대로 복사한다(재계산 금지 — antipatterns/duplicated-geometry-implementation). device_labels.jsonl 은 읽기 전용.
- 2026-09-11T11:16-07:00 — 틀리기 쉬운 자리: 이전 빌더가 남길 사진을 sorted(ids)[:quota] 로 골랐는데 id 가 촬영 연번이라 이 prefix 는 사실상 연속 촬영 한두 세션이다(예: SD CHECK GOLD2 앞 28장이 1203~1729 구간). 장면 다양성이 통째로 무너진 표본이었다. 이번 팔은 사진을 '빼지' 않으므로 이 문제가 없지만, 복제 대상을 고를 때도 prefix 가 아니라 고정 시드 순열로 순환할 것.
- 2026-09-11T11:16-07:00 — 학습 예산: pre_best.weights.h5 에서 ft 60에폭, eval_reader.py TTA(crc32) — 대조군과 동일. 바꾸는 것은 real_train 의 행 구성뿐이다.

## Handoff

## Result
