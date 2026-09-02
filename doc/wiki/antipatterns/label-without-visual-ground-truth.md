---
status: active
version_context: "sugarScan assets_dev/train"
tags: [data, anti-pattern]
aliases: [눈검증 없는 라벨링, 좌표만 저장]
created: 2026-09-02
confidence: 5
---
# 표시 정합 검증 없이 라벨을 대량 축적하는 것

좌표만 저장하고, 저장된 좌표를 **다시 이미지에 그려 확인하는 경로 없이** 계속 진행하는 것.

## 실패 모드

파손이 축적된 뒤에야 드러난다. LCD 라벨 122장 중 39장(32%)이 경계 초과로 확정돼 전면 재라벨링했고, 비-oob 라벨도 신뢰할 수 없어 전부 버렸다 — **경계 안에 들어온 것이 맞다는 증거가 아니기 때문이다.**

라벨은 사람 시간으로 만든 자산이라, 버리면 그 시간이 그대로 손실이다.

## 점검 체크리스트

- [ ] 저장 직후 그 좌표를 이미지에 그려 보는 경로가 있는가 (검수 단축키)
- [ ] 전수 점검을 버튼 하나로 돌릴 수 있는가 (`/api/selftest`)
- [ ] 저장된 행에 프레임 크기가 함께 있어 사후 검증이 가능한가
- [ ] 처음 N장(10~20)을 눈으로 확인한 뒤에 본작업을 시작했는가
- [ ] 라벨 파일이 버전 관리에 있는가

## 올바른 대안

[[frame-provenance-binding]] · [[server-side-write-verification]] · 검수 단축키(E) · 전수 자가검증(T)

## Grounding (References)

- `doc/raw/2026-09-02.md#case-3` — 39/122 파손, `screen_boxes_v1_invalid_20260902.jsonl`
- `doc/raw/2026-09-02.md#case-6`
