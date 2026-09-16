---
status: active
version_context: "sugarScan · 2026-09-15"
tags: [rendering, layout, anti-pattern]
aliases: [자리가 없으면 조용히 사라진다, 예약이 내용보다 좁다,
  요소가 그림에서 빠진다, silent drop]
created: 2026-09-15
confidence: 4
---
# 자리를 못 잡은 요소가 아무 말 없이 사라진다

배치기가 자리를 못 찾으면 그 요소를 **그리지 않고 넘어간다.** 산출물에는
그것이 없다는 사실만 남고, 왜 없는지는 남지 않는다. 보는 쪽은 "선언이
안 먹는다" 로 읽는다 — [[declaration-not-read-by-the-consumer]] 와 증상이
똑같아서 엉뚱한 곳을 파게 된다.

## 실패 모드

가장 흔한 원인은 **예약과 렌더가 다른 공식**을 쓰는 것이다.

- 예약이 넉넉하면 빈 면이 남는다(눈에 보인다, 덜 나쁘다).
- 예약이 좁으면 배치가 실패해 요소가 사라진다(안 보인다, 나쁘다).

sugarScan(2026-09-15):

```
하단 행을 균등 3등분   시각 폭 188px > 칸 폭 168px  -> 시각이 통째로 빠짐
dot_text 폭 예약       len(txt)*glyph*1.2 이라는 어림 -> 실제 폭과 무관
```

가변 길이 내용에서 특히 자주 난다. 실제 값으로 예약하면 렌더마다 자리가
움직이고, 어림으로 예약하면 여기 걸린다.

## 예방 체크리스트

- [ ] **예약 폭과 렌더 폭을 같은 함수에서 낸다.** 두 공식이 있으면
      언젠가 갈라진다([[duplicated-geometry-implementation]])
- [ ] 가변 길이 자리는 **그 형식이 낼 수 있는 가장 넓은 값**으로 예약한다
      ([[reserve-by-the-widest-value]])
- [ ] 빠진 요소를 **산출물에 기록하고 화면에 보여 준다.** sugarScan 은
      manifest 의 `dropped` 를 미리보기에 빨간 글씨로 인쇄하게 했다 —
      "고쳐도 안 바뀐다" 의 상당수가 이것이었다
- [ ] 코퍼스 단위로 **요소별 출현 수를 센다.** 46장 중 32장에만 있는 요소는
      확률이 그렇든가 자리가 모자라든가 둘 중 하나다

## Related
- [[declaration-not-read-by-the-consumer]]
- [[reserve-by-the-widest-value]]
- [[duplicated-geometry-implementation]]
- [[aggregate-hides-stratified-failure]]

## Grounding (References)
- `doc/raw/2026-09-15.md` Case 6 — `hash:b9aa317`
- `assets_dev/train/synth_check.py` · 웹툴 `/api/prof/preview` 의 `dropped`
