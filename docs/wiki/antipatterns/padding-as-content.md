---
status: active
version_context: "sugarScan assets_dev/train/ctc_reader_v2.py"
tags: [ml, anti-pattern]
aliases: [blank 조인, 패딩 직렬화, greedy_decode, NUM_CLASSES, ctc_reader_v2.py, blank]
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

## 그 수정은 2026-09-04 까지 no-op 이었다

2026-09-02 에 이 페이지를 만들면서 적은 "Fix Code" 가 **틀렸다.**

```python
gt_strs = [... for v in row if int(v) != NUM_CLASSES]      # 11 — 아무것도 안 거른다
gt_strs = [... for v in row if int(v) != NUM_CLASSES - 1]  # 10 — 이게 blank 다
```

`BLANK = NUM_CLASSES - 1 = 10` 인데 `NUM_CLASSES`(11)와 비교했다. 라벨 배열에 11 은 존재하지 않으므로 필터가 **항등식**이 된다. 그런데 당시 기록은 "이미 반영돼 다음 실행부터 자동 정상"이라고 적었고 **재실행으로 확인하지 않았다.** 분석 스크립트가 `labels.jsonl` 을 우회 GT 로 쓰고 있어 증상도 안 보였다.

그래서 이 버그는 3일 더 살아남아, 2자리 표본(전체의 20%)을 계속 전부 오답으로 집계했다 — **18.3pp**(92.9% → 74.6%). 그동안 이 페이지는 "해결됨"으로 보였다.

**패딩 필터를 고쳤으면 고친 뒤의 숫자를 한 번 찍어 볼 것.** 필터가 실제로 무언가를 걸렀는지는 걸러진 개수를 세면 바로 안다.

## Related

- [[metric-path-not-under-test]] — 이 버그가 EXIF 버그와 겹쳐 "모델이 못 읽는다"는 그림을 만들었다
- [[verification-record-without-subject]] — 재실행 없이 완료로 기록한 것

## Grounding (References)

- `doc/raw/2026-09-02.md#case-2` (`hash:b2e10ab`) — `{"glucose_batch1/862": ["90", "9010"]}`
- `doc/raw/2026-09-04.md#case-2` (`hash:b015830`) — 위 수정이 no-op 이었음. 올바른 GT 1042/1122(92.9%) vs 스크립트 GT 837/1122(74.6%)
