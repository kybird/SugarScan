---
status: active
version_context: "sugarScan assets_dev/train"
tags: [data, pattern]
aliases: [복구 스크립트 규약, --apply, 백업 후 수정, repair_prevframe_labels.py, repair_unrotated_band_labels.py]
created: 2026-09-02
confidence: 5
---
# Dry Run Before Repair

사람이 만든 데이터를 되돌리는 스크립트는 **기본 동작이 "계산만"** 이어야 한다.

## The Rule

1. `--apply` 없이 돌리면 아무것도 쓰지 않고 무엇을 어떻게 바꿀지 출력한다.
2. 쓸 때는 타임스탬프 백업을 먼저 만든다.
3. **되돌린 결과가 유효 범위에 들어오지 않으면 그 행은 손대지 않는다.**
4. 고친 행에는 출처 표시를 남긴다(`"repaired": "prevframe-20260902"`).
5. **사고 종류마다 스크립트를 나눈다.** 한 스크립트에 두 가설을 섞으면 다음 사람이 어느 쪽이 적용됐는지 못 읽는다.

## Why it works

라벨 좌표는 사람 시간으로 만든 자산이다. 잘못된 보정을 적용하면 **원본보다 더 나쁜 상태**가 되고, 그 사실은 크롭해 보기 전까지 드러나지 않는다. 2026-09-02 에 실제로 두 가지 사고가 겹쳐 있었고(배율 밀림 / 회전), 한쪽 처방을 다른 쪽에 적용하면 경계 검사만 통과하고 좌표는 틀린다.

## Trade-offs

- 두 번 실행해야 한다. 그 대가로 되돌릴 수 없는 실수를 막는다.

## Anti-Pattern

[[bounds-check-as-correctness-proof]]

## Related

- Concepts: [[coordinate-frame]]

## Grounding (References)

- `assets_dev/train/repair_prevframe_labels.py`, `repair_unrotated_band_labels.py`
- `doc/raw/2026-09-02.md#case-6`, `#case-7`
