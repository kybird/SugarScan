---
status: active
version_context: "실촬 사진 감식(2026-10-05)"
tags: [vision, anti-pattern]
aliases: [단일 이미지 방향 판정]
created: 2026-10-05
confidence: 5
---
# Single-image orientation judgment
사진 한 장을 그대로 보고 "회전됐다/정방향이다"를 판정한다 — 어두운 노출·
낮은 대비에서는 사람도 모델도 틀린다.

## The Rule
방향 판정은 **원본·반시계 90°·시계 90° 세 방향을 나란히 놓은 A/B 병치판**으로
한다. "어느 쪽이 바로 선 기기인가"를 고르는 질문은 "회전됐나?"보다 훨씬
확실하다.

## Why it works
#283(어두운 노출): 1차 시각 검증이 "정방향"으로 판정 → 사람이 "구십도
돌아간 사진"이라 정정 → A/B판에서 시계 90° 회전본이 정방향으로 확정
(숫자 109가 바로 선다). 방향 감각은 콘텐츠가 흐리면 무너진다.

## Trade-offs
판 하나 만드는 비용(수 초) vs 오판이 평가 기준(회전 제외 목록)에 영구
들어가는 비용.

## Anti-Pattern
회전 의심 장 목록을 기억·실패 이력으로만 유지 — 항상 판으로 재확인.

## Related
- [[visual-comparison-sheet-conventions]]
- [[2026-10-05]] Case 4 · hash:24a0e14 · _diag/rot_ab_283_1709.png
