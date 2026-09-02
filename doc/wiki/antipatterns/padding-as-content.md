---
status: active
version_context: "sugarScan assets_dev/train/ctc_reader_v2.py"
tags: [ml, anti-pattern]
aliases: [blank 조인, 패딩 직렬화]
created: 2026-09-02
confidence: 5
---
# 패딩 값이 유효 데이터와 구분 없이 직렬화되는 것

CTC 라벨 배열의 blank(클래스 10)를 필터하지 않고 문자열로 조인해 `"90" + "10"` → `"9010"` 이 된 것.

## 실패 모드

GT 가 조용히 오염되어 **기준선이 저평가**된다. hold-out exact match 3.8% 가 실제로는 5.1% 였다. 예측 쪽은 `greedy_decode` 가 blank 를 건너뛰어 깨끗했기 때문에, 비교 대상만 틀린 상태로 몇 번의 학습 판단이 이루어졌다.

패딩은 "값이 없음"인데 직렬화하면 "값 10"이 된다. 숫자 도메인에서는 그것이 유효값과 구분되지 않는다.

## 점검 체크리스트

- [ ] 패딩/blank 클래스가 직렬화 전에 걸러지는가
- [ ] GT 의 정본이 어디인지 한 곳으로 정해져 있는가 (여기서는 `labels.jsonl` 의 `reading`)
- [ ] 저장된 GT 와 정본 GT 를 대조해 본 적이 있는가
- [ ] 지표가 갑자기 낮으면 **모델이 아니라 비교 대상**을 먼저 의심했는가

## Grounding (References)

- `doc/raw/2026-09-02.md#case-2` (`hash:b2e10ab`) — `{"glucose_batch1/862": ["90", "9010"]}`
