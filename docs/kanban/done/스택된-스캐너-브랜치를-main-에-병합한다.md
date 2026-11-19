---
title: 스택된 스캐너 브랜치를 main 에 병합한다
status: done
ordinal: 13000
created: 2026-09-10
---

## Goal
<!-- kanban:goal:begin -->
glm/G33-error-code-guard 를 먼저, 그 위에 스택된 glm/G34-device-tagging 을 뒤이어 main 에 병합한다. 둘 다 main 대비 0 behind 라 리베이스 없이 순서만 지키면 된다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [x] #1 git branch --no-merged main 출력에서 glm/G33-error-code-guard 와 glm/G34-device-tagging 이 사라진다
- [x] #2 병합 후 main 에서 flutter analyze 무경고 · flutter test 전량 통과(2026-09-10 기준 397건)
- [x] #3 doc/kanban/activity.jsonl 이 양쪽 append 를 모두 보존한다 — 한쪽 블록만 남기고 끝내지 않는다(줄 수가 병합 전 두 브랜치 줄 수 이상)
- [x] #4 assets_dev/train/device_tags.jsonl 이 main 에서 git ls-files 에 잡힌다(.gitignore 예외가 함께 넘어왔는지 확인)
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-10T13:25-07:00 — 병합 순서가 전부다. G34 는 G33 위에 스택돼 있어 G33 을 먼저 넣지 않으면 reading_normalizer.dart 변경이 G34 커밋에 섞여 들어온다. 리베이스하지 말 것 — 둘 다 main 대비 0 behind 라 필요 없고, 리베이스하면 doc/kanban/activity.jsonl 이 재작성돼 append-only 규약이 깨진다. 충돌이 나면 자리는 doc/kanban/activity.jsonl 과 doc/kanban/cards/ 하나뿐이고, 정답은 '양쪽 다 남긴다'다.

## Handoff

## Result
- 2026-09-10T13:39-07:00 — G33 → G34 순서로 --no-ff 병합(28003f0, dc604b7). 충돌은 예상대로 doc/kanban/activity.jsonl 두 번뿐이었고 양쪽 append 를 ts 순으로 모두 보존(34줄). git branch --no-merged main 에서 두 브랜치 사라짐. flutter analyze 무경고 · flutter test 397건 전량 통과. device_tags.jsonl 이 git ls-files 에 잡히고 webtool.py 의 /devices 라우트가 main 에 들어옴.
