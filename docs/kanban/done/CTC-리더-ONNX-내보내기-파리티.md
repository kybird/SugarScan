---
title: CTC 리더 ONNX 내보내기 파리티
status: done
ordinal: 6000
created: 2026-09-09
---

## Goal
<!-- kanban:goal:begin -->
CTC 리더(Keras)를 ONNX 로 내보내고 PC 의 ONNX Runtime 추론이 기존 TF 추론과 같은 판독을 내는지 검증해, 온디바이스 전환의 모델 측 준비를 끝낸다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 assets_dev/train 에 내보내기 스크립트가 생기고 reader_model 체크포인트에서 .onnx 가 생성된다
- [x] #2 홀드아웃 표본(최소 300장)에서 TF 대 ONNX 판독 완전일치율이 보고된다(전처리·디코딩 동일)
- [x] #3 모델 입력 전처리 규격(정규화·리사이즈·채널 순서)이 문서 한 곳에 명시된다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-09T23:51-07:00 — 런타임 패키지 선택은 handoff 「온디바이스 ONNX 런타임 선택」 — 이 카드는 PC 파리티까지(방향 확정 86d3dbe). TF 실행은 conda run 필수. §36 전처리 규격 명시 포함

## Handoff

## Result
- 2026-09-10T00:31-07:00 — export_reader_onnx.py 로 logits 그래프를 ONNX(opset 13, 2.4MB) 변환, 캐시 홀드아웃 1,122장 전량 TF 대비 디코드 100% 완전일치·logits 최대차 0.006. 전처리 규격 정본 reader_onnx_spec.md 작성(EXIF→GM쿼드→BOX_MARGIN→320×160 워프→float32 0~255). 부수: sugartrain 환경 tf2onnx 설치 사고(numpy2·protobuf7 로 TF 임포트 사망)를 numpy 1.23.5·protobuf 3.20.3·onnx 1.13.0 조합으로 복구, 미니 fit 으로 훈련 경로 검증. 모바일 벤치는 런타임 판정 대기
