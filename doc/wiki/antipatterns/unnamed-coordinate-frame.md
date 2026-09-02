---
status: active
version_context: "sugarScan assets_dev/train · lib/features/scan"
tags: [geometry, anti-pattern]
aliases: [이름 없는 좌표계, 프레임 미기록]
created: 2026-09-02
confidence: 5
---
# 이름 없는 좌표계

좌표 배열만 저장하고, **그 좌표가 어느 프레임에서 만들어졌는지**는 저장하지 않는 것.

## 실패 모드

프레임이 어긋나도 저장된 데이터만으로는 알 수 없다. 그래서 파손이 **몇 시간·몇백 장 뒤에, 학습 결과가 이상할 때** 드러난다. 2026-09-02 에는 세 건이 저장되고 나서야 발견됐고, 그때도 "직전 장 크기와 정확히 일치한다"는 우연한 관찰이 없었으면 못 찾았다.

증상이 "배율 오차"로 보이기 때문에 진단이 **dpr·브라우저 배율 가설로 잘못 수렴한다.** 개발자 환경에서 재현되지 않으면 그 가설이 더 그럴듯해 보여 더 깊이 빠진다.

## 점검 체크리스트

- [ ] 저장하는 행에 프레임 크기(또는 프레임 id)가 함께 들어가는가
- [ ] 캔버스 상태에 "이 좌표계는 누구 것인가"를 나타내는 필드가 있는가
- [ ] 대상이 바뀔 때 좌표계가 **먼저 무효화**되는가
- [ ] 저장 직전에 프레임과 대상이 같은지 검문하는가
- [ ] 저장된 전체를 원본과 대조하는 전수 점검 경로가 있는가

## 올바른 대안

[[frame-provenance-binding]] + [[server-side-write-verification]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-3`, `#case-6`
- `docs/reports/20260902-labeler-coordinate-frame.md`
