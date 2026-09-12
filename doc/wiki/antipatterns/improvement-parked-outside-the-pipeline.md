---
status: active
version_context: "sugarScan assets_dev/train (합성 생성기 · 2026-09-12)"
tags: [ml, process, anti-pattern]
aliases: [곁가지 개선, 병렬 구현, 반영 안 된 개선, A/B 전용 코드, 기본 경로]
created: 2026-09-12
confidence: 5
---
# 개선을 새 파일에 만들고 기본 경로는 옛 파일을 계속 부르는 것

기준선을 보존하려고 개선을 **별도 구현**으로 만드는 것은 옳다. 그런데 그
구현을 기본 경로에 올리는 단계가 어느 카드의 완료 조건에도 없으면, 개선은
A/B 전용으로만 살아 있고 제품이 쓰는 경로는 영영 옛 코드다.

## 실패 모드

기기 프로파일 카드와 DSEG 글리프 카드가 연달아 완료됐다. 두 보고서 모두
정확했고 `synth_lcd.py` 를 건드리지 않았다고 명시했다 — 기준선 팔 보존을 위한
올바른 판단이다.

그러나 기본 캐시를 만드는 `build_cache_v2.py` 는 여전히 `synth_lcd.py` 를
부른다. 프로파일 렌더러는 `build_profiled_cache.py` 의 A/B 캐시에서만 쓰인다.
**두 카드의 성과가 제품 경로에 한 번도 닿지 않았다.**

대비를 재니 기본 경로가 오히려 더 나빴다(숫자 영역 p95-p5, 300장):

| | 중앙 | 40 미만 |
|---|---|---|
| 실사진 | 117.5 | **0.0%** |
| 합성 profiled (곁가지) | 87.0 | 15.0% |
| 합성 synth_lcd (기본 경로) | 93.0 | **17.3%** |

## 왜 이게 반복되는가

AC 는 "만든다"와 "잰다"로 쓰기 쉽고 "**바꾼다**"로 쓰기 어렵다. 기본 경로를
바꾸는 것은 되돌리기 부담이 있어 자연스럽게 뒤로 밀린다. 그리고 A/B 가
성공적으로 돌면 "반영된 것 같은" 착시가 생긴다 — 수치가 나왔으니까.

두 카드가 각자 정직하게 끝났는데도 합이 0 이 되는 구조다.

## 점검 체크리스트

- [ ] 이 개선을 제품/기본 경로가 실제로 부르는가 — 호출 지점을 코드로 확인했는가
- [ ] 카드 AC 에 "기본 경로가 이것을 쓴다"가 있는가
- [ ] 병렬 구현을 남긴다면 **언제 합칠지**가 어딘가에 적혀 있는가
- [ ] 옛 구현과 새 구현을 같은 자로 재 봤는가 (옛 쪽이 더 나쁠 수 있다)

## 무엇을 해야 하나

병렬 구현은 A/B 동안만 허용하고, **일원화 카드를 A/B 카드와 같이 세운다.**
일원화가 뒤따르는 개선 카드들의 선행이 되어야 한다 — 그래야 이후 작업이
제품에 닿는다.

## Related

- [[metric-path-not-under-test]] — 계측 경로를 의심하지 않는 것
- [[measure-the-premise-not-just-the-claim]] — 전제를 재는 습관
- [[duplicated-geometry-implementation]] — 같은 계산이 두 곳에 사는 것

## Grounding (References)

- `doc/raw/2026-09-12.md#case-2`
- `assets_dev/train/synth_profiles.py` · `build_profiled_cache.py` · `build_cache_v2.py:146`
- `docs/reports/device-profile-generator-2026-09-11.md` · `dseg-renderer-swap-2026-09-11.md`
