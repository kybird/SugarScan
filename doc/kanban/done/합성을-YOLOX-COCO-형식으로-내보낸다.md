---
title: 합성을 YOLOX COCO 형식으로 내보낸다
status: done
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
- [x] #1 gmscreen 과 같은 디렉터리 구조(annotations/instances_train2017.json + train2017/)로 세 벌이 생긴다
- [x] #2 어노테이션 수 = 이미지 수 (장당 상자 하나)
- [x] #3 상자를 원본에 그려 10장을 눈으로 확인 — 숫자가 상자 안에 전부 들어온다
- [x] #4 세 세트의 시드가 서로 다르고 파일에 기록돼 있다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-16T22:54-07:00 — 빌더는 assets_dev/train/build_synth_coco.py 한 파일. synth_panel.generate() 를 세트별로 다른 시드로 불러 굽고, images/ 를 train2017/ 로 옮긴 뒤 manifest.jsonl 의 quad(워프 후 밴드 쿼드)에서 축정렬 외접 상자를 만든다. 재구현 없음 — 쿼드는 synth_panel 이 준 것을 그대로 min/max 한다.
- 2026-09-16T22:54-07:00 — manifest.jsonl 을 세트 안에 같이 남겼다. COCO 에는 숫자 라벨이 없고 B(리더 학습)·C(끝단 평가)가 그 라벨을 필요로 한다. 카테고리는 glucose_band(id 1) — gmscreen 의 lcd_screen 과 대상이 다르므로 이름을 그대로 쓰지 않았다. 형식은 동일(annotations/instances_train2017.json + train2017/).
- 2026-09-16T22:54-07:00 — 숫자가 상자 안에 들어오는 것은 눈 10장보다 강한 근거가 있다: synth_panel 이 장마다 찍는 'band quad clipped digits' 가 세 세트 모두 0 이고(A 1000·B 1000·C 300), 상자는 그 쿼드의 외접 상자라 쿼드를 포함한다. 눈 확인판은 그 위에 얹은 것이다(<세트>_boxcheck.png, 초록=bbox 파랑=quad).
- 2026-09-16T22:54-07:00 — 세트 겹침은 파일명이 아니라 픽셀 md5 로 봤다. 파일명에 시드가 박혀 있어 이름 비교는 시드가 달랐다는 사실만 되풀이한다. --verify 가 그 자다.

## Handoff

## Result
- 2026-09-16T22:54-07:00 — assets_dev/train/build_synth_coco.py 신설(빌더+검사자 한 파일). synth_panel.generate() 를 세트별 다른 시드로 불러 A(1000·seed 20260916)·B(1000·seed 20260917)·C(300·seed 20260918)을 assets_dev/train/synth_coco/{A,B,C}/{annotations/instances_train2017.json, train2017/, manifest.jsonl} 로 굽고, seeds.json 에 시드를 남긴다. 상자는 매니페스트 quad(워프 후 밴드 쿼드)의 축정렬 외접 상자 하나, 클래스 하나(glucose_band id 1). 검증(명령: cd assets_dev/train && python build_synth_coco.py --verify -> VERIFY PASS, exit 0): 세 세트 모두 이미지 수 = 어노테이션 수 = train2017/ 파일 수(1000/1000/300), file_name 전부 실재, image_id 유일, 상자가 이미지 안. 시드 3개 서로 다름. 세트 간 동일 픽셀 0장(md5 비교, A∩B·A∩C·B∩C 전부 0 — 파일명이 아니라 픽셀로 쟀다). 숫자 포함(AC#3): 굽는 로그의 'band quad clipped digits' 가 A·B·C 모두 0 이고(모집단 = 각 세트 전량 1000/1000/300) 상자는 그 쿼드를 포함하므로 포함은 구성상 보장된다. 그 위에 세트당 10장 오버레이판(synth_coco/{A,B,C}_boxcheck.png, 초록=bbox 파랑=quad)을 눈으로 확인 — 30장 전부 숫자가 상자 안. 굽는 시간 2m53s(3회 합계 2,300장). 한계: 실촬 0장이다. 이 코퍼스는 전 구간 합성이고 검증도 같은 생성기라 일반화를 증명하지 않는다 — 마일스톤의 목적은 파이프라인 모양 확인이다.
