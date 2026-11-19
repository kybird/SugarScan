---
status: active
version_context: "llm-wiki (QMD 미설치 — grep 폴백)"
tags: [tooling, concept]
aliases: [검색 질의 모양, llm-wiki search, grep 폴백, retrieval]
created: 2026-09-02
confidence: 5
---
# Knowledge Retrieval Shape

지식 베이스의 가치는 **쓰여 있는가**가 아니라 **필요한 순간에 그 사람이 던지는 질의 모양으로 걸리는가**로 정해진다.

## First Principles

QMD 미설치 환경에서 `llm-wiki search` 는 공백 토큰화 + 대소문자 무시 **부분문자열 grep** 이다. 걸리고 안 걸리고는 딱 하나로 정해진다 — **질의 토큰이 문서에 문자 그대로 들어 있는가.**

그래서 "무엇을 썼는가"보다 "**누가 언제 무슨 단어로 찾는가**"가 설계 변수다.

## Details

실측(2026-09-02, 위키 28장):

| 질의 모양 | 결과 |
|---|---|
| 증상, 한국어 산문 ("통계에 안 보임") | 정확한 페이지가 1위 |
| 개념어 ("좌표계") | 잘 걸린다 |
| **코드 식별자 (`FrameThrottler`)** | **히트 0** — 페이지에 `frame_throttler.dart`(snake) 만 있어 문자열이 안 겹친다 |
| 조사가 붙은 긴 토큰 ("좌표계가") | 짧은 쪽이 긴 쪽에 걸린다. 질의가 길면 실패 |

**에이전트가 검색하는 시점은 파일을 열기 직전**이고, 그때 손에 있는 것은 개념어가 아니라 클래스·함수 이름이다. 가장 중요한 순간에 정확히 안 걸린다.

대책 둘:

1. **식별자를 `aliases` 에 넣는다.** CamelCase·snake_case·파일명·필드명을 다 적는다. 인덱스에도 나와 검색 없이 훑어도 보인다.
2. **검색에만 기대지 않는다.** → [[push-over-pull-for-prevention]]

## Related

- Patterns: [[push-over-pull-for-prevention]]
- Anti-Patterns: [[wiki-unreachable-by-identifier]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-11` (`hash:a8f0591`)
