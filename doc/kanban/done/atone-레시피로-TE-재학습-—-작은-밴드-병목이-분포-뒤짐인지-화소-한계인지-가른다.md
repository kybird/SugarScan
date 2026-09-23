---
title: atone 레시피로 TE 재학습 — 작은 밴드 병목이 분포 뒤짐인지 화소 한계인지 가른다
status: done
ordinal: 59000
created: 2026-09-22
milestone: 합성만으로 사진에서 값까지 한 번 통과시킨다
---

## Goal
<!-- kanban:goal:begin -->
합성 구도 선언(9/20) 분포로 검출기를 다시 학습해, VE 작음 3분위 실패(합격 90.99%, 오독 42% 집중)와 과대 상자(면적비 p90 2.99)가 학습 분포 뒤짐인지 화소 한계인지 사전등록 판정으로 가른다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 TE 재학습 4시드 완료 — atone 레시피 고정(--aug --under-w 3.0 --size 416 --steps 8000 --score-target bce), 산출 band_out/tone2te/
- [x] #2 VE 3분위 사전등록 판정 — atone s0~3 대비 같은 이미지 짝비교(합격률·검출실패·area_ratio) 표와 95% CI
- [x] #3 리더 배포 조건(B_pred) 끝단 정확도를 85.60% 대비 기록
- [x] #4 로보플로우 dev 586장 contains 비율 + 사람 라벨 50장 IoU 를 atone 대비 기록(50장은 봉인 — 학습 금지)
- [x] #5 /synth 다중 팔 오버레이 — VE 에서 atone/TE 재학습 상자를 나란히 보게 확장
- [x] #6 판정·수치를 낸 자가 저장소에 커밋됨
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-22T21:57-07:00 — 할 일 순서: (1) run_te_arms.sh 를 run_tone_scene.sh 구조로 작성해 band_out/tone2te/ 에 4시드 학습. TE 곡선 장 목록(instances_curve_07998.json, 15996장)이 TC 와 1:1 동일함은 2026-09-22 확인 완료 — 다시 검증하지 않는다. --mid-data 는 VE 를 명시적으로(run_tone_scene.sh 의 sed 치환은 TC/TD 용이라 TE 에 안 걸린다). (2) eval_band.py 로 atone s0~3 과 tone2te s0~3 을 같은 VE 자로 채점(--out jsonl). 짝비교 붓스트랩으로 작음 3분위 합격률 차이의 95% CI. 사전등록 판정: CI 하단이 0 초과면 분포 뒤짐(재학습이 처방), CI 가 0 을 포함하고 상승이 +2pt 미만이면 화소 한계(§24 — 해상도·접근 순서 문제), 그 사이면 판정보류로 구간만 적는다. (3) 새 검출기 상자로 reader_boxes 재생성해 배포 조건 리더 정확도 재기(§27 의 자를 그대로). (4) eval_band_roboflow.py 로 dev 586 contains. 사람 라벨 50장(rf_band_boxes.jsonl)은 봉인 시험 — 학습에 쓰지 않는다. (5) webtool /synth 에 팔 선택 확장.
건드리지 말 것: atone 체크포인트와 run_tone_scene.sh 는 레시피 정본 — 수정 금지. TC/TE/VE 코퍼스 재생성 금지(구도 선언 분포가 판정 대상). 판정 기준은 결과를 본 뒤 고치지 않는다.
어디서 틀리기 쉬운가: 3분위 경계는 VE frac 값 그대로(큼 0.297~0.625 / 중간 0.171~0.297 / 작음 0.031~0.171, 각 n=333) — 새 경계를 만들지 않는다. eval_band 의 pass 는 contains(숫자칸 포함)임을 그대로 쓴다. reader 비교는 §27 과 같은 GT/예측 상자 2x2 대칭으로.

## Handoff

## Result
- 2026-09-22T22:52-07:00 — 사전등록 판정: 분포 뒤짐 — VE 작음 3분위 합격 Δ+5.80pt(붓스트랩 95% CI +3.61~+8.21), 검출실패 전 시드 0건, 과대상자 p90 15.62→1.73, 리더 배포 끝단 85.60→96.90(+11.30pt — §27 의 11pt 갭 해소). 단 로보플로우 dev 586 통과 93.43→88.48(Δ−4.94pt 유의)이라 tone2te 는 배포 팔이 될 수 없다 — 남은 병목은 합성↔실사진 도메인 갭(§28.4). 자: run_te_arms.sh · tone2te_report.py · reader_dump.py --extra-boxes · /synth 팔 드롭다운(7a52e29 이후 커밋).
