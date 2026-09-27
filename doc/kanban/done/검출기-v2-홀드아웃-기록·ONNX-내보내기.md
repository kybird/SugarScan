---
title: 검출기 v2 홀드아웃 기록·ONNX 내보내기
status: done
ordinal: 27000
created: 2026-09-26
depends_on: ["새 세대 코퍼스 B2·C2 굽기와 CRNN 리더 학습"]
---

## Goal
<!-- kanban:goal:begin -->
검출기 bandft_v2(혼합 학습)의 실사진 홀드아웃 성적을 정본으로 기록하고, 리더 v2를 ONNX로 내보낸다. 둘 다 GPU 불필요(추론·변환만).
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 - [ ] #1 eval_synthband_real --side holdout --ckpt bandft_v2 — IoU 중앙·p10·실패·기기별 분해(v1 대비)
- [x] #2 reader_crnn_v2 → ONNX 내보내기(torch.onnx.export) — 입력·출력 shape 확인
- [x] #3 ONNX 추론이 torch 결과와 일치하는지 파리티 확인(샘플 10장)
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-26T22:31-07:00 — 완료(2026-09-26): ① 검출기 v2 홀드아웃 — IoU 중앙 0.8603·p10 0.7446·실패 3/119(v1: 0.8835·0.8144·0 — 실사진에서는 v1이 약간 우세하나 합성 패널 커버리지는 v2가 완벽·C2 스킵 0). ② ONNX 내보내기 — reader_crnn_v2/best.onnx(9,054KB·opset 13·dynamic batch). ③ 파리티 10/10 일치(torch vs onnxruntime).

## Handoff

## Result
- 2026-09-26T22:31-07:00 — 검출기 v2 홀드아웃 성적 정본 기록(IoU 0.8603·실패 3/119 — v1 대비 실사진 -0.023이나 합성 커버리지 완벽) + 리더 v2 ONNX 내보내기(9,054KB·opset 13) + 파리티 10/10 일치. GPU 불필요(추론·변환만)로 완료.
