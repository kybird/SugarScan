---
status: active
version_context: "sugarScan assets_dev/train (device_labels.jsonl 등 사람 산출물)"
tags: [data, ops, anti-pattern]
aliases: [이력 없는 덮어쓰기, 원자적 저장의 함정, tmp rename, untracked 라벨, 백업 없는 사람 라벨, 재생 불가 자산]
created: 2026-09-10
confidence: 5
---
# 사람이 만든 자산을 이력 없이 덮어쓴다

원자적 저장(`.tmp` → `rename`)은 **쓰다 만 파일**을 막을 뿐, **틀린 내용으로 온전히
덮이는 것**은 막지 못한다. 사람의 노동으로만 만들어지는 파일에 이력이 없으면,
버그 한 번이 곧 그 노동의 영구 손실이다.

## 실패 모드

`device_labels.jsonl` 은 사람이 사진 2,494장을 한 장씩 보고 붙인 라벨이었다.
저장은 원자적이었고, 그래서 안전하다고 여겨졌다. 실제로는

- 이전 상태를 남기지 않았고,
- 코드가 아니라는 이유로 git 추적에서도 빠져 있었다(`?? device_labels.jsonl`).

선택 버그([[display-and-selection-from-different-sources]])로 782행이 한 번에
덮였을 때 **되살릴 원본이 어디에도 없었다.** 남은 단서는 각 행의 `ts` 뿐이라,
"덮인 행이 무엇인가"는 알 수 있었지만 **"덮이기 전 값이 무엇이었나"는 알 수
없었다.** 782장을 사람이 다시 보는 수밖에 없었다.

## 왜 생기나 (First Principles)

- "데이터 파일은 코드가 아니다"라는 분류가 백업 여부를 정해 버린다. 판단 기준은
  종류가 아니라 **재생 비용**이어야 한다 — 다시 만들 수 없거나, 만드는 데 사람
  시간이 드는 파일은 코드보다 귀하다.
- 산출물(derived)과 원본(source)의 구분이 흐려진다. 파생 요약은 언제든 다시
  계산되지만, 그 요약의 입력이 된 사람 판정은 재계산이 불가능하다.
- 원자적 쓰기가 주는 안전감이 이력의 부재를 가린다. 둘은 다른 실패를 막는다.

## 막는 법

1. **덮어쓰기 직전에 직전 상태를 남긴다.** 회전 백업 한 줄이면 된다 —
   `backup_device_labels()` 는 저장 직전 복사 + 오래된 것 정리로 끝난다.
   파일이 수백 KB면 수백 개를 남겨도 비용이 없다.
2. **사람 산출물은 무조건 버전 관리에 넣는다.** 크기·형식이 아니라 재생 비용으로
   판단한다. gitignore 에 예외를 파는 것이 정상이다.
3. 되돌릴 수 있게 **누가 썼는지 표시한다**(`by: human` / `by: agent` /
   `by: claude-recovery`). 사고 후 어디까지가 사람 판정인지 가려낼 수 있다.
4. 행마다 **타임스탬프**를 남긴다. 사고 범위를 배치 단위로 특정할 수 있는
   유일한 수단이었다.

## Related
- [[display-and-selection-from-different-sources]] — 이번 사고의 원인 쪽.
- [[backup-list-by-importance-not-by-what-writes]] — 무엇을 백업 목록에 넣을지
  정하는 기준이 어긋나는 같은 계열의 실패.
- [[dry-run-before-repair]] — 대량 변경 전에 무엇이 바뀌는지 먼저 찍어 본다.

## Grounding (References)
- `doc/raw/2026-09-10.md#case-6` — `hash:3ebec36` 에서 회전 백업과 git 추적을 함께 넣었다.
