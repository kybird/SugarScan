---
status: active
version_context: "llm-wiki (QMD 미설치)"
tags: [tooling, anti-pattern]
aliases: [식별자로 안 걸리는 위키, aliases 누락, FrameThrottler, statsReadingsProvider]
created: 2026-09-02
confidence: 5
---
# 코드 식별자로는 찾히지 않는 위키

개념어와 산문으로만 쓰인 페이지. 사람이 검색해 보면 잘 걸려서 **다 됐다고 착각한다.**

## 실패 모드

에이전트가 검색하는 시점은 **파일을 열기 직전**이고, 그때 손에 있는 것은 "좌표계"가 아니라 `FrameThrottler` 다. grep 기반 검색에서 `FrameThrottler` 는 `frame_throttler.dart` 와 문자열이 겹치지 않아 **히트 0** 이다.

실측(2026-09-02): 안티패턴 14장을 써 두고도 `FrameThrottler` · `statsReadingsProvider` · `pendingSyncCount` · `_apply` 로는 위키가 한 장도 안 걸렸다. 지식 그래프가 있으나 마나였다.

## 점검 체크리스트

- [ ] 페이지 `aliases` 에 **클래스명(CamelCase)** 이 있는가
- [ ] **파일명(snake_case.dart)** 이 있는가 — CamelCase 와 문자열이 안 겹친다
- [ ] 함수·필드·프로바이더 이름이 있는가 (`_apply`, `valueMgdl`, `orElse`)
- [ ] 실제로 검색해 봤는가 — `llm-wiki search "<식별자>"` 로 **페이지가 걸리는지** 확인
- [ ] 검색으로 못 닿는 예방 지식은 push 경로가 있는가 → [[push-over-pull-for-prevention]]

## 도구 함정 (llm-wiki)

- 인덱서는 **하이픈 없는 `antipatterns/`** 만 스캔한다. `anti-patterns/` 로 만들면 조용히 0 개로 집계된다.
- 루트 loose `.md` 는 태그와 무관하게 Concepts 로 떨어져 개념 수를 부풀린다. 리포트류는 `reports/` 같은 하위 디렉터리에 둔다.

## Grounding (References)

- `doc/raw/2026-09-02.md#case-11` (`hash:a8f0591`)
