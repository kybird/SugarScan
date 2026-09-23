---
title: TC+TE 혼합 코퍼스로 검출기를 재학습해 합성 이득과 실사진 회귀를 함께 잰다
status: doing
ordinal: 60000
created: 2026-09-22
milestone: 검출기와 인식기를 독립 축으로 끌어올린다
claimed_by: zcode-0922
claimed_at: 2026-09-23T00:01-07:00
---

## Goal
<!-- kanban:goal:begin -->
atone 레시피를 그대로 TC+TE 혼합 코퍼스로 여러 시드 학습해, VE 작음 3분위 이득(시드 평균 97% 이상)과 로보플로우 dev 586 통과 무회귀(atone 대비 유의차 없음 또는 양)를 동시에 충족하는지 사전등록 판정으로 가른다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 혼합 코퍼스 구축 — TC/TE 이미지를 tc_/te_ 접두로 복사해 한 디렉토리로, 곡선 장 목록 병합 검증, 기존 TC/TE/VE 코퍼스 불변
- [ ] #2 8시드(디스크·시간 여유에 따라 4) 학습 + VE 3분위·로보플로우 dev 586 채점 — atone/tone2te 와 같은 자
- [ ] #3 사전등록 판정 기록 — VE 작음 97% 이상 유지 && 로보플로우 통과 차이의 95% CI 가 0 을 포함하거나 양 → 채택 후보. VE 만 충족 → '구도 축 단독으로 실사진 회귀를 못 막는다'로 기록
- [ ] #4 자(구축·판정 스크립트)와 BAND_EXP_PLAN 신규 절 커밋
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-22T23:29-07:00 — 할 일: (1) 디스크 여유 확인(이미지 약 3.2만 장 복사). (2) 혼합 코퍼스 구축 — TC/TE train2017 을 새 디렉토리 train2017 에 tc_/te_ 접두 복사, 곡선 annotation 두 개를 접두 붙여 병합(image_id 재부여 — 두 COCO 의 id 공간이 겹친다), manifest 는 학습에 안 쓰니 건너뛴다. TC/TE 곡선 장 목록이 1:1 동일함은 2026-09-22 확인 완료. (3) 학습은 train_band.py --data 를 혼합 디렉토리로 주는 것만(스크립트 본체 수정 금지), run_te_arms.sh 구조의 실행 스크립트. (4) 채점·판정은 tone2te_report.py·report_fail_mix.py 재사용·확장(3팔 비교).
건드리지 말 것: TC/TE/VE 코퍼스 재생성 금지(기존 분포가 대조군). atone 체크포인트·run_tone_scene.sh·train_band.py·eval_band.py 불변 — 혼합은 데이터 준비로만 이룬다. 판정 기준은 결과를 본 뒤 고치지 않는다.
어디서 틀리기 쉬운가: annotation 병합에서 image_id 충돌(재부여 없이 합치면 라벨-이미지 짝이 조용히 어긋난다). 3분위 경계(0.171/0.297)와 로보플로우 dev 586 자는 기존 값 그대로 — 새 경계를 만들지 않는다. 시드 하나의 값으로 판정하지 않는다(atone 로보플로우 시드 폭 15pt 교훈, 2026-09-20 §16).

## Handoff

## Result
