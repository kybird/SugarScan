---
title: 합성기에 블러·잡음·JPEG 열화 사슬 축을 넣는다
status: done
ordinal: 72000
created: 2026-09-21
depends_on: ["로보플로우 완전 미검출을 구도·열화·이물로 3분할한다"]
milestone: 실패 사진과 닮은 합성기 — 열화·구도
---

## Goal
<!-- kanban:goal:begin -->
전체 이미지(패널 포함)에 걸리는 사실적 열화 사슬(블러→ISO 잡음→JPEG)을 합성기의 독립 축으로 넣어 갤러리 사진 품질을 학습 분포에 반영한다
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 열화 사슬이 이미지 전체(패널 포함)에 적용되는 축으로 synth_panel/프로파일 예산에 들어간다
- [x] #2 사슬 각 단계가 독립 토글·세기 조절이다(한 축 세기가 다른 축을 끌고 가지 않는다)
- [x] #3 열화 세기 스펙트럼 샘플 시트가 _diag/ 에 남는다
- [x] #4 세션 단위 분할을 유지한 채 굽는다(image-level split 아님)
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-21T15:21-07:00 — 사람 결정(2026-09-21, #10): 우리가 실패하는 이미지와 비슷하게 합성기를 개선한다. 설계 조건 세 가지 — (a) 사실적 열화 사슬(블러→ISO 잡음→JPEG, 가우시안 잡음 단일 축 아님), (b) 열화는 배경이 아니라 이미지 전체(패널 포함)에 적용 — 패널만 선명하면 모델이 배우는 건 '시끄러운 배경 무시'지 '열화된 기기 탐지'가 아님, (c) 축별 독립 예산(coupled-budget-loop-defeats-per-element-tuning 안티패턴 회피). 검증은 scene-component-split 패턴, 세션 단위 분할 유지(image-level-split-on-session-corpus 회피). 현재 합성 조건은 노이즈 없음·PNG(SPEC §9.7)이라 열화 축은 0에서 시작하는 새 축이다.
- 2026-09-21T22:56-07:00 — 검증(2026-09-21): 시드 99001·24장을 off/on 두 번 구워 — 열화 on/off 간 레이아웃·정답 box·id·profile 전부 동일(난수를 렌더 rng 와 별도 스트림에서 뽑아 기존 코퍼스 재현성 보존), on manifest 전 행에 degrade 세기 기록(blur/noise/jpeg), off manifest 에는 키 부재, 이미지 바이트는 6/6 전부 상이(실적용). 시트 _diag/degrade_spectrum.png — 원본+각 축 4단계+사슬 3단계 = 16타일, 눈검수는 사람 몫.

## Handoff

## Result
- 2026-09-21T22:56-07:00 — 무엇을 바꿨나: synth_panel.py 에 degrade(사슬: 가우시안 블러 → ISO 잡음 근사(밝기 의존 shot 0.65 + read 0.35 클립 가우시안) → JPEG 왕복)와 parse_degrade(축별 독립 토글·세기 범위)를 추가, generate()가 이미지 전체(패널 포함)에 적용하고 manifest rec['degrade'] 에 세기를 남긴다. 난수는 렌더 rng 와 별도 스트림(seed0*1000003+i) — 열화 off 시 기존 코퍼스 바이트 동일 재현, on 이어도 레이아웃·정답 box 불변. CLI: synth_panel.py gen --degrade · degrade-sheet 서브커맨드 · build_synth_coco.py --degrade(모든 세트 적용). 무엇으로 검증했나: 같은 시드 24장 off/on 이중 굽기 — 레이아웃·box 동일·degrade 키 기록·이미지 바이트 상이 전부 확인, 축별 토글 파서(blur만/전부/off) 확인, 스펙트럼 시트 16타일(_diag/degrade_spectrum.png) 생성. 눈검수는 사람이 시트로 한다.
