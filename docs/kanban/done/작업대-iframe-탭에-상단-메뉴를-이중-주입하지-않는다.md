---
title: 작업대 iframe 탭에 상단 메뉴를 이중 주입하지 않는다
status: done
ordinal: 66000
created: 2026-09-21
milestone: 웹툴을 한 서버·한 메뉴로 정비한다
---

## Goal
<!-- kanban:goal:begin -->
_send_page 가 iframe 요청(Sec-Fetch-Dest: iframe)에는 _topnav 를 주입하지 않게 해 작업대 기종·아틀라스 탭에서 메뉴가 한 겹만 보이게 한다
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 작업대 기종 탭과 아틀라스 탭의 iframe 문서에 #topnav 가 존재하지 않는다
- [x] #2 직접 연 독립 화면(/devices 등)에는 상단 메뉴가 그대로 주입된다
- [x] #3 Sec-Fetch-Dest 미지원 환경 폴백(쿼리 파라미터 등)이 있고 그 이유가 주석으로 남는다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-21T15:21-07:00 — 조사(2026-09-21): 작업대 기종·아틀라스 탭은 iframe 으로 /devices·/atlas 를 싣는다(webtool.html:312,326). _send_page(webtool.py:2296)가 iframe 안 문서에도 _topnav 를 주입해 작업대 탭 머리글과 두 겹이 된다. 판별은 Sec-Fetch-Dest: iframe 요청 헤더. /photo·/synthimg 등 이진 라우트는 무관하고 HTML 페이지 송출만 해당.

## Handoff

## Result
- 2026-09-21T22:15-07:00 — 무엇을 바꿨나: _send_page 가 iframe 요청에는 _topnav 를 주입하지 않게 했다. 판별 정본은 Sec-Fetch-Dest: iframe 헤더, 폴백은 ?embed=1 쿼리(작업대 기종 탭 iframe src 에 붙임) — 둘 중 하나만으로도 주입이 멈는다. 무엇으로 검증했나: 웹툴 8778 기동 후 curl 로 — 직접 접속 /devices·/synth 는 id=topnav 1회(AC#2), Sec-Fetch-Dest: iframe 헤더·?embed=1 폴백 모두 0회(AC#1·#3), /atlas 도 0회(_send_page 를 안 거치는 아틀라스 페이지 — 처음부터 topnav 없음).
