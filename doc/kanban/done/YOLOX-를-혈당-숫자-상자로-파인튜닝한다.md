---
title: YOLOX 를 혈당 숫자 상자로 파인튜닝한다
status: done
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
- [x] #1 학습이 끝나고 체크포인트가 저장된다. 학습 시간과 에폭 수를 카드 Note 에 기록한다
- [x] #2 세트 A 검증 분할에서 mAP 가 출력된다(수치는 판정이 아니라 기록)
- [x] #3 세트 C 10장에 추론해 상자를 그려 눈으로 확인 — 숫자를 감싼다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-16T23:09-07:00 — 학습: 25 에폭 · 벽시계 13분 36초(train_log.txt 22:55:22 -> 23:08:58) · RTX 4070 Laptop · 배치 16 · fp16 · 입력 640. exp 파일을 저장소 안에 뒀다(assets_dev/train/yolox_synthband_exp.py) — 기존 exp 는 D:/tmp/YOLOX 에 있어 런을 재현할 수 없었다. 해상도 640 은 gmscreen_ft4(G25)가 확정한 값을 그대로 쓰고 여기서 다시 스윕하지 않았다.
- 2026-09-16T23:09-07:00 — 막힘 하나: 2026-08-28 gmscreen 체크포인트가 지금 환경에서 안 읽힌다. 'ModuleNotFoundError: No module named numpy._core' — 그 체크포인트는 numpy 2.x 로 절였는데 2026-09-10 에 TF 2.10 을 살리려 numpy 를 1.23.5 로 내렸다(antipatterns/unpinned-pip-in-frozen-training-env 의 후속 피해). 가중치는 멀쩡하고 pickle 의 모듈 경로만 옛것이라, migrate_ckpt_numpy1.py 로 numpy._core -> numpy.core 별칭을 걸어 한 번 읽고 지금 numpy 로 다시 절였다. 원본은 그대로 둔다. 이 환경에서 2026-09-10 이전 체크포인트를 부르는 모든 스크립트가 같은 벽을 친다.
- 2026-09-16T23:09-07:00 — 추론 전처리는 YOLOX 의 ValTransform 을 그대로 부른다(레터박스). 직접 resize 를 짜면 학습 레터박스 / 추론 스트레치로 갈라지는데 그게 이미 열려 있는 카드다(GM 검출 추론 전처리를 학습과 맞춘다). 같은 벽을 두 번 치지 않으려고 기하를 재구현하지 않았다.
- 2026-09-16T23:09-07:00 — A 를 900/100 으로 나눈 것은 YOLOX 가 학습 중 mAP 를 재려면 val 분할이 필요해서다(prep_synth_yolox.py, 분할 시드 20260919). B·C 에서 잘라 오지 않았다 — 거기서 가져오면 검출기가 리더·평가 세트를 보게 된다.

## Handoff

## Result
- 2026-09-16T23:09-07:00 — yolox_out/synthband_v0/best_ckpt.pth 생성. gmscreen 체크포인트(2026-08-28, 화면 검출)에서 출발해 클래스를 glucose_band 하나로 바꾸고 세트 A 로 25 에폭 파인튜닝. 신설 파일 셋: yolox_synthband_exp.py(exp 를 저장소 안에 둬 런을 재현 가능하게) · prep_synth_yolox.py(A 를 900/100 train/val 로, 분할 시드 20260919) · infer_synthband.py(ValTransform 레터박스 추론) · migrate_ckpt_numpy1.py(옛 체크포인트 numpy 호환). AC#1 학습 13분 36초 / 25 에폭(yolox_out/synthband_v0/train_log.txt 22:55:22 -> 23:08:58, RTX 4070 Laptop, 배치 16, fp16). AC#2 세트 A 검증 분할 100장에서 COCO mAP — 최종(에폭 25) AP@[.50:.95] 0.818 · AP@.50 1.000 · AP@.75 0.949 · AR 0.862, 학습 전체 최고 83.87(같은 로그의 'Training of experiment is done and the best AP is 83.87'). 모집단: synth_coco/A_yolox/annotations/instances_val2017.json, n=100, 전부 합성. AC#3 세트 C 전량 추론(명령: python infer_synthband.py --set synth_coco/C --ckpt yolox_out/synthband_v0/best_ckpt.pth --out _diag/synthband_v0/C.jsonl --sheet _diag/synthband_v0/C_pred.png) — n=300, 검출 실패 0장, IoU 중앙 0.9144 · 평균 0.9060 · 최소 0.6501 · >=0.5 300장 · >=0.75 299장. 그 중 10장 오버레이판(_diag/synthband_v0/C_pred.png, 초록=예측 빨강=정답)을 눈으로 확인 — 10장 모두 예측 상자가 숫자를 감싼다. 한계 둘: (1) 학습·검증·평가가 전부 같은 생성기다. A 의 val 분할은 A 와 같은 시드(20260916)에서 잘랐으므로 같은 장면 분포이고, C 는 다른 시드지만 여전히 같은 생성기라 일반화를 증명하지 않는다. 실촬 0장. (2) mAP 수치는 기록이지 합격 판정이 아니다 — 이 마일스톤의 목적은 파이프라인 모양 확인이다.
