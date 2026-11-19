---
title: 합성 대 실사진 차이표 D10 정정 — HI/LO 는 코퍼스에 0건
status: done
ordinal: 35000
created: 2026-09-11
---

## Goal
<!-- kanban:goal:begin -->
아틀라스 보고서 D10 이 '코퍼스 전체에 HI/LO 318건 존재'라고 적었는데 근거가 없다. 실측으로 정정한다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 docs/reports/synth-vs-real-atlas-2026-09-11.md 의 D10 행에 정정문이 붙는다 — 지우지 말고 취소선과 근거를 함께
- [x] #2 정정 근거가 명령과 출력으로 남는다
<!-- kanban:ac:end -->

## Plan

## Notes

## Handoff

## Result
- 2026-09-12T12:48-07:00 — 9535ae6(glm/detector). AC#1 아틀라스 D10 행에 취소선 정정문 부착(원문 유지): '코퍼스 전체에 HI/LO 318건 존재' 철회 — 실측 labels.jsonl 2,512행 reading 전부 정수(30~511, 비정수 0건), HI/LO 0건. 318 의 실체는 G20 감사의 리더 오독 집계(docs/reports/G20-exif-loader-unification.md SUMMARY 원문 hiLoReads=318) — 오독 집계를 코퍼스 보유 수치로 옮겨 적은 것이 근원. 같은 오류가 있는 요소 재고표 HI/LO 행도 함께 정정. AC#2 정정 근거 명령·출력 원문을 정정문 안에 남김.
