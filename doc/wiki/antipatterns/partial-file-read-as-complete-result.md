---
status: active
version_context: "와처/자동화 스크립트 일반"
tags: [automation, anti-pattern]
aliases: [부분 파일 판정]
created: 2026-10-05
confidence: 5
---
# Partial file read as complete result
증분 기록 파일(평가 jsonl, 로그)을 '존재'만 보고 완결로 읽어 판정하면
일부분으로 전체를 재게 된다.

## The Rule
다른 프로세스가 쓰는 파일을 판정에 쓸 때는 **완결 조건을 명시적으로**
정의하라 — 기대 행 수 이상, 또는 생성자의 '종료' 로그 라인. 파일 존재는
시작 신호일 뿐이다.

## Why it works
e2e 평가는 사진 한 장마다 한 행씩 쓴다. 447행(18%)만 쓴 파일에서 "오독 20"
을 읽으면 전량 결과(오독 93)와 결론이 달라질 수 있다 — 이 날은 우연히
결론이 같아 사고가 안 났지만 **근거가 무효인 판정은 다음에 틀린다**.

## Trade-offs
행 수 기다림(+분) vs 종료 로그 대기(생성자와 계약 필요) — 생성자 로그를
통제할 수 있으면 종료 라인이 더 근본이다.

## Anti-Pattern
```python
if P.exists():          # 잘못 — 쓰는 중일 수 있다
    judge(read(P))
```

## Related
- [[bounds-check-as-correctness-proof]] (존재 확인을 증명으로 착각하는 계열)
- [[2026-10-05]] Case 3 · hash:24a0e14 · _diag/ladder_switch_watcher.log
