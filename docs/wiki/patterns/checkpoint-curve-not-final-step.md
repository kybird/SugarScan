---
status: active
version_context: "BandNet·CRNN 학습(2026-10-05)"
tags: [training, pattern]
aliases: [구간 체크포인트 곡선]
created: 2026-10-05
confidence: 5
---
# Checkpoint curve, not final step
학습이 끝난 지점의 모델이 아니라 **구간 체크포인트의 곡선**으로 채택 지점을
고른다. 후반부 퇴화는 드물지 않다.

## The Rule
대량 학습에는 중간 체크포인트를 남기고(--save-every), 각 지점을 같은 자로
재서 정점을 찾는다. 스텝 수는 예산 패리티(비교 공정성)를 위한 것이지
'끝까지 돌리라'는 뜻이 아니다.

## Why it works
GEN2 검출기(동일 코퍼스 29,878장): step8000 실패 1 · step16000 실패 4 —
후반 4장 전부 **상자 위치는 맞는데 score만 게이트를 못 넘는 '확신 사망'**
(같은 사진이 8k에서 0.81 → 16k에서 0.00). 위치 회귀는 유지되고 확신 보정만
퇴화하는 과적합 형태가 있어, 마지막 체크포인트를 쓰면 이를 걷어낼 수 없다.

## Trade-offs
체크포인트 저장(2.1MB/개)과 구간별 재평가 비용 vs 퇴화 검출 — 곡선 없이는
"더 학습했다"와 "나빠졌다"를 구분 못 한다.

## Anti-Pattern
- 마지막 체크포인트 = 최선 가정.
- 스텝(학습량)과 코퍼스 장 수(데이터 양)를 같은 'k'로 섞어 보고 —
  8k채택(스텝)과 30k 코퍼스(장 수)는 다른 축이다.

## Related
- [[experiment-budget-parity]] 근거 문서(docs/SPEC.md)
- [[single-point-trend-claim]]
- [[2026-10-05]] Case 5 · hash:24a0e14
