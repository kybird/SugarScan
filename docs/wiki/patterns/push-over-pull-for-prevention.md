---
status: active
version_context: "sugarScan CLAUDE.md · githooks"
tags: [tooling, pattern]
aliases: [푸시 우선, 트리거 표, CLAUDE.md 표, AGENTS.md, 예방은 검색으로 안 된다]
created: 2026-09-02
confidence: 4
---
# Push over Pull for Prevention

**검색은 pull 이다 — 물어볼 줄 알아야 걸린다.** 예방이 목적이라면 검색에 기대면 안 된다. 실수를 하려는 사람은 자기가 실수 중인 줄 모르므로 애초에 검색하지 않는다.

## The Rule

- **진단용 지식**(증상이 있고 원인을 찾는 중)은 검색으로 충분하다.
- **예방용 지식**(아직 아무 일도 안 일어났다)은 **밀어 넣어야** 한다.
  - 매 세션 로드되는 파일(`CLAUDE.md`)에 "이 파일·기호를 건드리기 전에 이 페이지를 읽어라" 표를 둔다.
  - 위임 지시서 양식에 "무엇을 건드리지 마라 / 어디서 틀리기 쉬운가"를 필수 칸으로 둔다.
  - 결정적인 것은 **테스트로 고정**한다 — 문서는 안 읽혀도 테스트는 CI 가 읽는다.

## Why it works

지식이 실제로 작동한 자리를 되짚어 보면 전부 push 였다. `CLAUDE.md` 의 "LO 를 10 으로 읽지 않는다", `kotlin.incremental=false` 주석, 회귀 테스트 — 아무도 검색해서 찾지 않았고, 눈앞에 있어서 지켜졌다.

반대로 잘 쓰인 안티패턴 14장은, 그것을 어기려는 에이전트가 검색하지 않으면 존재하지 않는 것과 같다.

## Trade-offs

- 매 세션 로드되는 파일이 길어진다 → 표는 **경로만** 적고 설명은 위키에 둔다.
- 표가 낡으면 오히려 해롭다 → `wiki-compile` 때 함께 본다.

## Anti-Pattern

[[wiki-unreachable-by-identifier]]

## Related

- Concepts: [[knowledge-retrieval-shape]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-11` (`hash:a8f0591`)
- `CLAUDE.md` — "지식 베이스 — 파일을 열기 전에 볼 것" 표
