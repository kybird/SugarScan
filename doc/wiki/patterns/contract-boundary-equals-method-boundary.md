---
status: active
version_context: "sugarScan lib/ocr"
tags: [architecture, pattern]
aliases: [계약 경계, never-throws, GlucoseScanner.offer, _recognizeSafely, ScanUnavailable]
created: 2026-09-02
confidence: 5
---
# Contract Boundary Equals Method Boundary

"이 메서드는 예외를 던지지 않는다"는 계약을 걸었으면, `try` 는 **메서드 전체**를 감싸야 한다. 위험해 보이는 호출만 감싸는 것은 계약이 아니라 희망이다.

## The Rule

```dart
Future<ScanOutcome> offer(OcrFrame frame) async {
  try { return await _offer(frame); }
  on Object { return _emit(const ScanUnavailable(...)); }
}
```

계약을 문장으로 적었다면 **그 문장을 테스트로 고정한다.** 계약을 깨는 부품을 주입해 통과하는지 본다(예: 던지는 `GlucoseValidator`).

## Why it works

`GlucoseScanner.offer()` 는 엔진 호출만 감싸고 있었다. 정규화·검증·안정화도 같은 메서드에서 도는데, 그중 하나가 던지면 라이브 프레임 루프가 죽어 **스캔 화면 전체가 멈춘다.** "엔진만 위험하다"는 판단은 그때는 맞았지만 계약은 그 판단을 담고 있지 않았다.

## Trade-offs

- 넓은 `catch` 는 진짜 버그를 숨긴다. 그래서 삼키지 말고 **실패 상태로 승격**하고(`ScanUnavailable`), 진단은 로그로 남긴다.

## Anti-Pattern

[[contract-guard-too-narrow]]

## Related

- Concepts: [[canonical-value]]
- Patterns: [[generation-token]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-9` (`hash:5ed3f06`)
- `test/ocr/glucose_scanner_contract_test.dart`
- `CLAUDE.md` — "`GlucoseScanner.offer()` 는 절대 예외를 던지지 않는다"
