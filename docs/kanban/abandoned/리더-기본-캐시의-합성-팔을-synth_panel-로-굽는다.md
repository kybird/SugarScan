---
title: 리더 기본 캐시의 합성 팔을 synth_panel 로 굽는다
status: abandoned
ordinal: 47000
created: 2026-09-13
depends_on: ["합성 생성이 같은 시드에서 같은 코퍼스를 내게 한다"]
discard_reason: 사람 승인 2026-09-24(권고 채택): 새 리더(reader_crnn)는 npz 캐시를 쓰지 않고 COCO 세트에서 직접 크롭해 학습 — 이 카드가 고치려는 기본 캐시의 소비자가 없다(아무도 안 쓰면 굽는 보람 없음). 디스크 1.3GB×7 벌 유지. 글리프 교체(58c12cc) 뒤 코퍼스 재생성은 새 경로(COCO/synth_panel gen)로 한다.
---

## Goal
<!-- kanban:goal:begin -->
build_cache_v2 가 만드는 기본 리더 캐시(data_cache_v2.npz)의 합성 배열은 아직 옛 synth_screens/*.png 를 단순 리사이즈한 것이다. 그 png 는 synth_lcd.render_screen 산출이라 기기 개념도 극성 선언도 단위 규칙도 없다. 2026-09-13 에 build_profiled_cache 는 synth_panel + reader_view 로 옮겼지만 기본 캐시는 그대로다 — 리더를 다시 구울 때 어느 캐시를 쓸지가 갈린다.
<!-- kanban:goal:end -->

## Acceptance Criteria
<!-- kanban:ac:begin -->
- [ ] #1 합성 배열이 synth_panel.render_panel + reader_view 산출이다 — 실사진 팔과 같은 프레이밍(build_cache_v2.framed_src_rect, BOX_MARGIN 10%)을 통과한다
- [ ] #2 실사진 배열·id 는 바이트 동일하다(md5 대조). 이 카드는 합성만 바꾼다
- [ ] #3 전환 전후 합성 표본 12장을 나란히 저장해 눈으로 비교한다
- [ ] #4 기존 train_device/data_cache_v2.npz 를 덮어쓰지 않는다 — 새 경로에 굽고 어느 것이 정본인지 문서에 적는다
<!-- kanban:ac:end -->

## Plan

## Notes
- 2026-09-17T01:16-07:00 — 근거 조회 2026-09-17 (review 세션, 조회 전용 — 굽지 않았다). handoff 의 질문 (2)'이 캐시를 앞으로 누가 쓰는가' 는 조회로 답이 나온다. **새 리더는 안 쓴다.**

[확인]
- 새 리더 reader_crnn.py(커밋 864ef28, 2026-09-16 'CRNN + CTC 리더를 torch 로 새로 만든다')는 COCO 세트에서 직접 읽는다. 사용법 주석 reader_crnn.py:15 'python reader_crnn.py train --set synth_coco/B', 기본값 reader_crnn.py:220 은 synth_coco/B, 로딩은 reader_crnn.py:87 의 annotations/*.json 이다. npz 를 여는 곳이 없다. handoff 의 서술이 맞다.
- data_cache_v2 를 문자열로 참조하는 파이썬 파일은 33개인데 전부 옛 경로다 — 옛 리더 ctc_reader_v2.py(마지막 변경 1c0bd70, 2026-09-09)와 그 진단 스크립트 diag_*, 그리고 분할 빌더들이다. 옛 리더는 2026-09-11 에 폐기됐다.
- 예외로 build_device_split.py 는 아직 살아 있는 쓰임이 있다 — 다만 이번 세션에 확인한 바로는 캐시를 읽는 쪽(분할 생성)이지 이 카드가 고치려는 **합성 배열**을 읽는 쪽이 아니다. 그리고 2026-09-17 에 신설된 build_band_device_split.py 는 build_device_split 에서 규칙(device_key·SEED·상한)만 import 하고 캐시는 band_boxes.jsonl 로 갈아탔다.

[디스크 비용 — handoff 수치를 정정한다]
handoff 는 '각 1.3GB, 일곱 벌' 이라 했는데 실제로는 **14개 15.0 GB** 다(assets_dev 아래 *cache_v2*.npz 전량). 내역: train/ 에 1,246MB 짜리 7벌 + _backup_20260904 · _backup_overnight · _diag/gmft 에 3벌, train_device·train_device_bal_cap·train_device_bal_eq·train_grouped 에 718~747MB 4벌. 한 벌 더 구우면 +1.2GB 다.
재현: find assets_dev -name '*cache_v2*.npz' 뒤 du.

[사람이 답할 것 — 순서를 뒤집으면 (1)이 사라진다]
handoff 는 (1) 새 경로 굽기 허용 여부와 (2) 누가 쓰는지 순으로 물었는데, (2)가 '아무도 안 쓴다' 로 나왔으므로 (1)은 답할 필요가 없어진다. 남는 질문은 하나다 — **이 카드를 접을 것인가.**
(가) 접는다(abandon). 되돌릴 수 있다 — 카드를 다시 세우면 된다. 근거: 목표물인 기본 캐시를 새 파이프라인의 어느 단계도 읽지 않는다. 마일스톤은 synth_coco -> YOLOX -> reader_crnn 이고 npz 가 들어가는 자리가 없다. 접으면 Goal 에 적힌 사실('기본 캐시의 합성 팔이 옛 synth_lcd 산출이라 기기·극성·단위 규칙이 없다')은 살려 옮겨야 한다 — 그 캐시를 나중에 누가 되살려 쓰면 그 결함이 그대로 따라온다.
(나) 남겨 둔다. 되돌릴 수 있다. 근거가 되려면 '옛 npz 경로를 다시 쓸 계획이 있다' 가 참이어야 하는데, 이 세션은 그런 계획을 보드나 문서에서 찾지 못했다. 찾지 못한 것이 없다는 증거는 아니다 — 사람이 아는 계획이 있으면 그것이 판정 근거다.
어느 쪽이든 굽기는 지금 하지 않는 것이 맞다. 15GB 가 이미 쌓여 있고 소비자가 확인되지 않은 상태에서 +1.2GB 를 더 굽는 것은 되돌리기 번거로운 쪽이다.

[재지 않은 것] 33개 소비자 파일 하나하나가 실제로 죽었는지 실행해 확인하지 않았다 — 파일 참조와 커밋 날짜로만 판단했다. 옛 npz 를 읽는 살아 있는 작업이 남아 있을 가능성을 배제하지 못한다.

## Handoff
- 2026-09-17T00:14-07:00 — QUESTION: 무인 루프의 실행 제약과 정면으로 부딪혀 손대지 않고 세운다. 이번 세션 킥오프의 '절대 하면 안 되는 것' 에 'build_cache_v2.py 로 기본 캐시 다시 굽기' 와 '공유 캐시 train_device/data_cache_v2.npz 에 쓰기' 가 명시돼 있는데, 이 카드의 AC#1 은 기본 캐시(data_cache_v2.npz)의 합성 배열을 synth_panel 산출로 바꾸라는 것이라 굽기가 작업의 전부다. AC#4 가 '새 경로에 굽는다' 를 요구하므로 공유 캐시를 덮어쓰지 않는 길은 열려 있지만, 그래도 build_cache_v2 를 돌려 캐시를 굽는 행위 자체가 금지 목록에 있다. 그래서 한 줄도 실행하지 않았다. 사람이 정할 것 둘: (1) 새 경로로 굽는 것은 허용인가 — 허용이면 다음 무인 세션이 바로 집을 수 있다. (2) 그 전에 순서를 다시 볼 필요가 있다 — 리더가 2026-09-11 에 폐기됐고 새 리더(reader_crnn.py)는 어젯밤 구현됐는데 npz 캐시가 아니라 COCO 세트에서 직접 크롭해 학습한다. 즉 새 리더는 data_cache_v2.npz 를 쓰지 않는다. 이 카드가 고치려는 '기본 캐시' 를 앞으로 누가 쓰는지가 먼저 정해져야 굽는 보람이 있다. 아무도 안 쓰면 이 카드는 접는 쪽이 맞다. 참고로 디스크 비용도 작지 않다 — 기존 캐시 파일이 각 1.3GB 이고 이미 일곱 벌이 있다.

## Result
