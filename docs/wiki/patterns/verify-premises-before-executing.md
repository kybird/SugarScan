---
status: active
version_context: "sugarScan docs/GLM_TASKS.md · 위임 절차"
tags: [process, pattern]
aliases: [전제 실측, 지시서 검증, 요약 먼저, 위임 안전장치]
created: 2026-09-02
confidence: 5
---
# Verify Premises Before Executing

지시서를 받으면 **적힌 대로 하기 전에 전제가 사실인지 먼저 잰다.** 지시서를 쓴
사람도 틀린다.

## The Rule

1. 지시서가 "이 코드는 X 를 하지 않는다" 라고 주장하면 **그 코드를 열어 확인**한다.
2. 확인 비용이 큰 주장은 **가장 싼 실험**으로 가른다 — 20장 A/B, 크롭 한 장.
3. 틀렸으면 **실행하지 말고 멈춰서 보고**한다. 고쳐서 진행하지 않는다.
4. 착수 전에 **무엇을 할 것인지 3~5줄 요약**을 먼저 내놓는다. 잘못 읽었으면
   코드를 건드리기 전에 드러난다.

## Why it works

2026-09-02 에 실증됐다. G20 지시서가 세 파일을 "EXIF 무처리"로 지목했는데
**둘이 무죄**였다. 위임받은 에이전트가 그대로 실행했다면:

- `golden_bench` 에 no-op 코드가 들어가고, 그걸 "고쳤다"고 기록했을 것이다
- 진짜 결함(`build_cache_v2`) 하나가 셋 속에 묻혔을 것이다
- 그 오진이 가리고 있던 **GM 힌트 이중 회전**은 계속 발견되지 않았을 것이다

**지시서가 틀렸을 때 그것을 잡아낸 것은 사람이 아니라 위임 절차였다.**

## Trade-offs

- 착수가 느려진다. 대신 잘못된 방향으로 반나절 가는 것을 막는다.
- 에이전트가 "지시가 틀렸다"고 말할 수 있어야 한다 — 지시서에 그 권한을 명시해야
  실제로 작동한다("판단이 필요해지면 멈춘다", "검증을 실행하지 않고 통과했다고
  적지 않는다").

## Anti-Pattern

[[unnamed-coordinate-frame]] 의 상위 형태 — **확인 없이 이름표를 믿는 것.**
주석, 파일명, 이전 로그의 결론 전부 이름표다.

## Related

- Concepts: [[coordinate-frame]]
- Patterns: [[dry-run-before-repair]], [[push-over-pull-for-prevention]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-13` (`hash:dad9b25`)
- `docs/GLM_PROMPT.md` — "먼저 3~5줄 요약" 항목
