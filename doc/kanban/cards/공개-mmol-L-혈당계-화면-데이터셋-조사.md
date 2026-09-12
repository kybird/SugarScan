---
title: 공개 mmol/L 혈당계 화면 데이터셋 조사
status: doing
ordinal: 15000
created: 2026-09-11
claimed_by: glm
claimed_at: 2026-09-11T20:08-07:00
---

## Goal
<!-- kanban:goal:begin -->
소수점을 포함한 mmol/L 표시 혈당계 사진을 공개 데이터셋에서 확보할 수 있는지 조사하고, 각 후보의 라이선스·장수·표시 형식을 표로 정리한다. 반입 여부 판정은 사람이 한다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 후보 데이터셋마다 출처 URL·라이선스 원문·총 장수·mmol/L 소수점 표시 장수 추정이 표로 정리된다
- [ ] #2 라이선스가 확인되지 않은 후보는 '미확인'으로 남고 확인된 것처럼 적히지 않는다
- [ ] #3 우리 파이프라인에 넣으려면 추가로 필요한 작업(GM 박스 quad 라벨링 등)과 그 대략 분량이 후보마다 적힌다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-11T11:29-07:00 — 이미 찾은 1순위 후보: Finnegan, Villarroel, Velardo, Tarassenko (2019) 'Automated method for detecting and reading seven-segment digits from images of blood glucose metres and blood pressure monitors', J Med Eng Technol 43(6) 341-355. Oxford CameraLab 이 실사진 데이터셋 + 7세그 합성 생성기를 공개했다고 적혀 있다. 영국 연구라 mmol/L 표시가 기본이고 논문에 12.8 mmol/L 예시가 있다. 페이지: cameralab.eng.ox.ac.uk/seven_segment.html · ORA: ora.ox.ac.uk/objects/uuid:72be1fdf-327d-4d30-ab66-8892e642fc68
- 2026-09-11T11:29-07:00 — 다운로드하지 말 것. 이 카드의 산출물은 조사표 하나다. 라이선스가 확인되고 사람이 반입을 결정하기 전에는 파일을 저장소나 assets_dev 에 들이지 않는다 — docs/LICENSES.md 가 반입 자산 라이선스의 정본이고, EasyOCR 가중치가 지금도 그 문서 §4 에 '미확인' 으로 남아 있는 이유가 이것이다. 논문이 CC-BY 라는 사실이 데이터셋도 CC-BY 라는 뜻은 아니다 — 데이터셋 페이지에 적힌 조건을 원문 그대로 인용할 것.
- 2026-09-11T11:29-07:00 — GPL-3.0 / AGPL-3.0 코드는 후보에서 즉시 탈락이고 그 자리에서 조사를 멈춘다(SSOCR·lcd-digit-recognition 계열). 알고리즘 아이디어를 보는 것과 코드를 들이는 것은 다르다 — SegmentRuleEngine 이 자체 구현인 것 자체가 이 프로젝트의 라이선스 방어선이다.
- 2026-09-11T11:29-07:00 — 확인할 것: (1) mmol/L 소수점 표시가 실제로 몇 장인지(정수만 있으면 이 카드의 목적에 무용하다) (2) 소수점 위치가 자리마다 다른 표본이 있는지(5.6 과 12.3 둘 다) (3) 기기 종류 수 (4) 해상도와 촬영 조건. 사진을 못 받으면 논문 본문의 표·그림에서 읽히는 만큼만 적고 '원본 미확인' 이라고 쓴다 — 추정치를 확정처럼 적지 말 것.

## Handoff

## Result
