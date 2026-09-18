---
status: active
version_context: "sugarScan · 2026-09-17"
tags: [licensing, provenance, ml, anti-pattern]
aliases: [실촬 0장인데 가중치엔 있다, 계보를 데이터만 센다, 사전학습 계보,
  lineage counted only in data, pretrained weights carry provenance]
created: 2026-09-17
confidence: 5
---
# "X 를 쓰지 않는다"를 **학습 데이터만 세어** 확인하는 것

파생물의 계보는 학습 데이터에서 끝나지 않는다. **사전학습 가중치**와 **라벨의
출처**도 같은 계보에 들어간다. 데이터만 세고 통과시키면 나머지가 조용히
따라 들어온다.

## 실패 모드

sugarScan 마일스톤 문구: **"실촬은 전 구간에서 뺀다(학습도 검증도)."**

그 마일스톤의 검출기를 학습하고 결과마다 "실촬 0장"이라고 적었다. 학습 데이터는
정말 0장이었다. 그런데 계보를 그려 보니:

```text
yolox_nano.pth (COCO 사전학습)
  └ gmscreen          ← Roboflow 실촬 1,276장으로 학습된 체크포인트
      └ synthband_v0  ← "합성 900장, 실촬 0장" 이라고 보고한 모델
```

**데이터에는 실촬이 없지만 가중치에는 1,276장이 있었다.** 검출기 카드 Goal 이
"기존 gmscreen 체크포인트에서 출발해"라고 명시했고, 카드를 집을 때 상위
마일스톤 문구와 대조하지 않았다. 두 문장이 저장소 안에서 서로 어긋나 있었다.

라이선스로도 같은 구멍이었다 — Roboflow 데이터셋은 CC BY 4.0(저작자 표시)이고,
그 파생 가중치를 배포하면 의무가 따라온다. "우리 학습 데이터에 없다"는 면제
사유가 아니다.

## 점검 체크리스트

계보를 검산할 때 **세 가지를 각각** 센다:

- [ ] **학습 데이터** — 이번 런이 읽은 이미지·라벨
- [ ] **사전학습 가중치** — `-c` 로 넘긴 체크포인트가 무엇으로 학습됐는가.
      그 체크포인트의 학습 로그까지 거슬러 올라간다
- [ ] **라벨의 출처** — 사람이 찍은 라벨이 누구의 사진 위에 찍혔는가
- [ ] 카드·계획 문서가 여러 개면 **상위 문서의 제약과 대조**했는가

## 어떻게 세는가

주장하지 말고 파일을 센다. sugarScan 은 COCO 어노테이션의 `file_name` 접두사로
셌다 — `gmscreen` 에 datumo 유래 0장, `gmscreen_ft` 에 410장. 체크포인트의
출발점은 학습 로그의 `args: Namespace(... ckpt='...')` 한 줄에 박혀 있다.

## 왜 반복되는가

"실촬 0장"은 데이터를 세면 **참**이다. 가중치를 세야 거짓이 드러난다.
**세는 대상이 하나 빠져 있으면 검산이 통과한다.** 그리고 사전학습은 너무
당연해서 계보의 일부로 의식되지 않는다 — 누구나 COCO 에서 시작하니까.

## 처방

계보를 코드에 박는다. sugarScan 은 exp 파일 머리말에 시작점 규칙과 **이유**를
적었다 — 규칙만 적으면 다음 사람이 카드 Goal 을 보고 되돌린다.

## Related
- [[metric-provenance]]
- [[stale-baseline-quoted-as-current]]
- [[target-defined-by-the-label-not-the-generator]]

## Grounding (References)
- `doc/raw/2026-09-17.md` Case 2 — "실촬 0장"이 가중치를 안 셌다
- `doc/raw/2026-09-17.md` Case 3 — 사전학습 목표가 우리 목표와 달랐다(밴드는
  LCD 의 40%, 119/119 포함). 그 전이는 합성 4,100장으로 대체됐다
- `docs/LICENSES.md` §1.1 — 체크포인트별 계보와 의무
- `assets_dev/train/yolox_synthband_exp.py` — 시작점 규칙을 박아 둔 자리
