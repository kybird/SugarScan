---
status: active
version_context: "sugarScan · 2026-09-15"
tags: [simulation, reproducibility, experiment, pattern]
aliases: [난수열을 축마다 가른다, 촬영 변인 분리, 내용과 조명을 따로,
  split rng per axis]
created: 2026-09-15
confidence: 5
---
# 독립이어야 하는 축은 난수열도 갈라 둔다

한 난수열을 여러 축이 나눠 쓰면, 한 축이 난수를 하나 더 소비하는 것만으로
**다른 축이 통째로 달라진다.** 같은 시드로 A/B 를 해도 바꾼 것 말고 바뀌는
것이 생기고, 그러면 바꾼 것을 못 찾는다.

## The Rule

1. 무엇과 무엇이 **독립이어야 하는지** 먼저 적는다(합성기라면 화면 내용 vs
   촬영 변인, 학습이라면 데이터 순서 vs 가중치 초기화).
2. 시드 하나에서 파생시키되, **갈라지는 지점을 입력에 의존하지 않는 곳**에
   둔다 — 보통 함수 맨 앞이다.
3. 그 뒤로는 축마다 자기 난수열만 쓴다.

```python
def _render_once(value, rng, profile, ...):
    # 프로파일이 난수를 쓰기 **전**에 가른다. 여기서 갈라야 배치를 어떻게
    # 바꿔도 촬영 변인이 고정된다.
    _orng = random.Random(rng.getrandbits(63))
```

## Why it works

분기 지점이 입력보다 앞이면 파생 시드가 입력과 무관해진다. 내용 쪽에서
난수를 몇 개를 쓰든 촬영 쪽 열은 같은 자리에서 시작한다.

sugarScan 에서 확인(2026-09-15): 요소 하나(`avgrow`)를 켜고 끄며 같은 시드로
16장을 그렸다.

```
고치기 전   같은 시드에서 그림자가 뒤집힘 — 사람 눈에는 "켜면 100% 생김"
고친 뒤     달라진 장 0/16 · 카메라 각도도 20/20 동일
```

## Trade-offs

- 같은 시드가 **다른 코퍼스**를 낸다. 갈아끼우는 순간 옛 시드로 구운 데이터와
  재현이 끊긴다 — 재굽기를 전제로만 한다.
- 축을 잘못 가르면 오히려 상관이 사라져야 할 곳에서 사라진다. "독립이어야
  하는가" 를 먼저 적는 것이 1번인 이유다.

## Anti-Pattern

[[uncontrolled-budget-in-ab-comparison]] — 비교에서 통제 안 된 변인이 같이
움직인다. 난수열 공유는 그 변인이 **보이지 않는** 형태다.

## Related
- [[uncontrolled-budget-in-ab-comparison]]
- [[experiment-budget-parity]]
- [[silent-drop-on-placement-failure]]

## Grounding (References)
- `doc/raw/2026-09-15.md` Case 5 — `hash:b9aa317`
- `assets_dev/train/synth_panel.py` `_orng`
