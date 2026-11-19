---
title: CRNN CTC 리더를 새로 만든다
status: done
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
- [x] #1 50장을 과적합시켜 완전일치 100% 가 나온다(구현이 학습되는지 확인. 성적이 아니다)
- [x] #2 입력 크기와 charset 이 코드 한 곳에 상수로 있고 주석에 이유가 있다
- [x] #3 flutter 와 무관한 assets_dev/train 안에만 있다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-16T23:16-07:00 — torch 로 썼다(옛 리더 ctc_reader_v2.py 는 TF 2.10). 이유 셋: ①검출기가 torch 라 한 환경에서 끝단까지 돈다 ②온디바이스 경로가 ONNX 로 정해졌고(G28 — tflite 불가) torch->ONNX 가 짧다 ③이 환경의 TF 2.10 은 numpy 1.23 에 묶여 있어 더 얹지 않는 편이 낫다. 옛 리더의 가중치·수치는 끌어오지 않는다 — 2026-09-11 에 폐기됐다.
- 2026-09-16T23:16-07:00 — 구조: conv 5단(높이만 32배로 접고 폭은 4배) -> Linear 768->256 -> BiLSTM 192x2 -> Linear 11. 시간축 36. blank 를 맨 뒤(10)에 둬서 0~9 의 인덱스가 곧 숫자 값이 된다 — argmax 를 그대로 읽을 수 있어 디코더에서 표가 하나 줄어든다.
- 2026-09-16T23:16-07:00 — BandCrops 가 상자 출처를 둘로 연다: 매니페스트 정답 상자(기본)와 infer_synthband.py 의 예측 상자 jsonl(--boxes). 다음 카드가 예측 상자로 학습하므로 갈래를 미리 열어 뒀다. 예측이 없는 장은 items 에서 빠지고 skipped 로 센다 — 조용히 사라지지 않게.
- 2026-09-16T23:16-07:00 — 과적합이 200 에폭에서 76% 로 끝나 한 번 '실패'를 봤는데 구현 문제가 아니었다. 손실이 계속 내려가는 중이었고(0.2592) CTC 특유의 초반 blank 평탄 구간(ep20~60 loss 2.2 정체)이 길었을 뿐이다. 상한을 800 으로 올리니 300 에폭에서 100% 가 나왔다. 과적합 확인의 상한은 넉넉해야 한다 — 짧게 잡으면 수렴 속도를 구현 결함으로 오진한다.
- 2026-09-16T23:16-07:00 — IN_H/IN_W 의 근거를 재는 자를 같은 파일에 뒀다(measure 서브커맨드). 상수를 바꾸려면 그걸 먼저 돌린다 — 즉석 한 줄로 잰 값을 주석에 남기지 않으려고.

## Handoff

## Result
- 2026-09-16T23:16-07:00 — assets_dev/train/reader_crnn.py 신설 — torch CRNN + CTC. conv 5단(높이 32배 축소·폭 4배) -> Linear 768->256 -> BiLSTM 192x2 -> Linear 11, 시간축 36. charset 0~9, blank=10(맨 뒤라 0~9 인덱스가 곧 숫자 값). 크롭을 펴지 않는다 — 상자 종횡비 그대로 IN_W x IN_H 로 늘린다. AC#1 과적합 확인(명령: python reader_crnn.py overfit --set synth_coco/B): 50장에서 완전일치 100%, 300 에폭, 손실 0.0113. 모집단은 세트 B 에서 시드 20260916 으로 뽑은 50장. AC#2 상수는 파일 상단 한 곳 — CHARSET·BLANK·NUM_CLASSES·MAX_LABEL·IN_H/IN_W·TIME_STEPS, 근거 주석 포함. 종횡비 1.5 는 실측 중앙값이고 재는 자를 같은 파일에 뒀다(명령: python reader_crnn.py measure --set synth_coco/A -> n=1000 p5 1.314 · p50 1.498 · p95 1.771; --set synth_coco/B --boxes _diag/synthband_v0/B.jsonl -> n=999 p5 1.348 · p50 1.496 · p95 1.710). AC#3 git diff 로 확인 — assets_dev/train/reader_crnn.py 한 파일뿐이고 lib/·pubspec 등 flutter 쪽 변경 0. 한계: 과적합 100% 는 구현이 학습된다는 확인이지 성적이 아니다. 일반화는 재지 않았고 본 학습은 다음 카드다. 옛 리더(2026-09-11 폐기)의 수치와 나란히 놓지 않는다.
