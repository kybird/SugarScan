---
status: active
version_context: "ZCode 세션 압축·백그라운드 작업(2026-10-05)"
tags: [ops, anti-pattern]
aliases: [작업 핸들=프로세스 사망 착각]
created: 2026-10-05
confidence: 5
---
# Task handle death ≠ process death
세션 재개·압축 후 작업 핸들이 사라져도 OS 프로세스는 살아 있을 수 있다.
핸들 상태로 프로세스 생존을 판정하지 않는다.

## The Rule
세션 재개 후에는 `Get-CimInstance Win32_Process`(명령줄 포함)로 프로세스
목록을 대조한다. 특히 **같은 출력 경로를 쓰는 무인 체인이 둘 이상이면
즉시 정리**한다.

## Why it works
이 날 실제로: 컨텍스트 압축 전 세션의 체인 프로세스가 살아남아 새 체인과
나란히 굽기 완료를 기다리고 있었다 — 방치하면 같은
`band_out/tone/gen2_v1`에 **두 학습이 동시에** 시작된다.

## Trade-offs
대조 비용(1명령) vs 체크포인트 오염(하루치 무효).

## Anti-Pattern
`TaskOutput '찾을 수 없음'`을 프로세스 사망으로 읽음 — 핸들은 세션 소유,
프로세스는 OS 소유.

## Related
- [[initializer-scoped-helper-called-by-global-render]] (세션 경계에서
  남는 것 계열)
- [[2026-10-05]] Case 8 · hash:24a0e14
