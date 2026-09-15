---
status: active
version_context: "sugarScan · 2026-09-15"
tags: [synthetic-data, measurement, labeling, pattern]
aliases: [실사진에 자를 대지 않는다, 합성이 기준을 준다, 사람이 합성을 따라한다,
  no ruler on real photos]
created: 2026-09-15
confidence: 5
---
# 합성의 **설계**는 합성이 정한다 — 실사진에 자를 대지 않는다

합성 데이터의 설계값(요소 자리, 여백, 간격, 기기 속성)을 실촬 사진을 재서
정하지 않는다. **합성이 기준을 주고 사람이 그걸 따라 라벨링한다.**

## The Rule

- 설계값은 **선언한다**. 코드 상수와 프로파일에 박고 시험으로 고정한다.
- 사람 라벨 지침은 그 선언을 **받아 적는다**(「숫자 높이의 10% 여백」).
- 실사진은 **눈으로만 본다** — 나란히 놓고 사람이 보고 값을 정한다. 재지 않는다.

## Why it works

**사람은 기계적으로 동일한 여백을 못 만든다**(사람 지침 2026-09-15:
「니가 기준을 주고 사람이 따라해야지」). 실촬 라벨에는 촬영 변인과 손의 떨림이
얹혀 있어, 거기서 뽑은 통계는 설계값이 아니라 **잡음의 중앙값**이다.

그 값을 설계에 되먹이면 두 번 진다. sugarScan 에서 실물 잉크가 밴드의 0.99 를
채운다고 재서 숫자를 키웠더니 521장이 잘리고 34건이 겹쳤다 — 잉크 두께는
조명과 노출의 함수지 셀 크기가 아니었다([[lighting-dependent-metric-as-content-target]]).
실제 획 두께에 맞춰 팽창을 넣었더니 세그먼트가 붙어 7-seg 이 아니게 됐다.

선언이 먼저 있으면 사람 라벨과 합성이 **같은 규약**을 공유한다. 어긋나면 어느
쪽이 규약을 안 지켰는지가 바로 나온다 — 두 잡음의 평균을 쫓는 대신.

## Trade-offs

- 선언값이 실물과 체계적으로 다르면 그만큼 도메인 격차로 남는다. 그래서
  **사람이 보고 정한다** — 재는 것과 보는 것은 다르다. 기기별 `hug`(단위가
  숫자에 붙는 정도)는 실사진과 합성을 나란히 인쇄해
  (`assets_dev/train/make_unit_gap_sheet.py`) 사람이 값을 불렀다.
- 값의 근거가 측정이 아니라 판단이므로 **누가 언제 정했는지**를 코드에 남겨야
  한다. 안 남기면 다음 사람이 「근거 없는 상수」로 보고 재려 든다.

## 경계 — 설계이지 목표가 아니다

이 규칙은 **무엇을 그릴 것인가**(설계)에만 적용된다.
**무엇을 검출할 것인가**(학습 목표의 정의)까지 확장하면 반대로 뒤집힌다:
목표의 정의는 실촬 라벨이 정하고 합성이 따라가야 한다
([[target-defined-by-the-label-not-the-generator]]).

둘을 구분하지 않은 것이 2026-09-15 사고의 뿌리였다. 합성이 「딱 맞는 기운
쿼드」를 목표로 선언하고, 사람 라벨은 「기운 숫자를 감싼 축정렬 상자」를
가리켜, 게이트가 그 차이를 모델 성적이라고 쟀다
([[synthetic-target-differs-from-label-definition]]).

## Anti-Pattern

실촬 라벨의 통계를 합성 설계값으로 되먹인다. 잡음을 설계로 승격시키고,
그 설계로 만든 데이터로 다시 그 잡음을 학습한다 —
[[measured-result-used-as-input]].

## Related
- [[target-defined-by-the-label-not-the-generator]]
- [[synthetic-target-differs-from-label-definition]]
- [[lighting-dependent-metric-as-content-target]]
- [[measured-result-used-as-input]]
- [[declare-what-the-human-knows]]

## Grounding (References)
- `doc/raw/2026-09-15.md` Case 2 — `hash:56d8e65`
- `assets_dev/train/lcd_layout.py` `BAND_MARGIN = 0.10` · `test_lcd_layout.py`
- `assets_dev/train/make_unit_gap_sheet.py` — 재지 않고 나란히 보여 준다
