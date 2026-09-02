---
status: active
version_context: "sugarScan lib/ocr"
tags: [architecture, anti-pattern]
aliases: [좁은 try, 계약보다 좁은 방어]
created: 2026-09-02
confidence: 5
---
# 계약보다 좁은 방어

"이 메서드는 예외를 던지지 않는다"고 문서에 적어 두고, `try` 는 **위험해 보이는 호출 하나만** 감싸는 것.

## 실패 모드

`GlucoseScanner.offer()` 는 엔진 호출만 감쌌다. 정규화·검증·안정화도 같은 메서드에서 도는데, 그중 하나가 던지면 라이브 프레임 루프가 죽어 **스캔 화면 전체가 멈춘다.**

"엔진만 위험하다"는 판단은 작성 시점에는 맞았다. 문제는 **계약이 그 판단을 담고 있지 않았다**는 것이다. 나중에 정규화기에 정규식 하나가 추가되면 계약이 조용히 깨진다.

## 점검 체크리스트

- [ ] 문서에 "던지지 않는다 / 실패하지 않는다"고 적힌 메서드가 있는가
- [ ] 그 `try` 가 **메서드 전체**를 감싸는가
- [ ] 계약을 깨는 부품을 주입해 통과하는지 보는 테스트가 있는가
- [ ] 넓은 `catch` 가 오류를 **삼키지 않고** 실패 상태로 승격하는가
- [ ] `reset()`/`clear()` 류가 진행 중인 작업의 잠금까지 건드리지 않는가 → [[reset-clears-in-flight-lock]]

## 올바른 대안

[[contract-boundary-equals-method-boundary]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-9` (`hash:5ed3f06`)
- `test/ocr/glucose_scanner_contract_test.dart`
