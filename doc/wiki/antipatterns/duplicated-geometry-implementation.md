---
status: active
version_context: "sugarScan lib/features/scan/photo_preprocessor.dart"
tags: [geometry, anti-pattern]
aliases: [좌표 변환 중복, 워프 두 벌]
created: 2026-09-02
confidence: 5
---
# 좌표 변환 구현을 두 벌로 두는 것

거의 같은 100줄(디코드 → 회색 변환 → 호모그래피 역샘플링)이 두 함수에 복사돼 있는 것.

## 실패 모드

경계 클램프나 역샘플링 식을 **한쪽만 고치면 두 경로가 조용히 갈라진다.** 좌표를 다루는 코드는 갈라진 것을 눈으로 알아채기 가장 어려운 종류다 — 결과가 그럴듯한 이미지로 나오기 때문이다.

실제로 이 저장소에서는 **문서가 먼저 갈라졌다.** `warpQuadToRect` 주석은 "퍼센타일 대비 스케일 포함"이라고 적혀 있었지만 코드는 하지 않았다. 그 주석을 믿고 "빠진 걸 채우면" 밴드 검출 임계값이 벤치 로그에 남은 수치와 다른 것을 보게 된다.

## 점검 체크리스트

- [ ] 같은 기하 변환이 두 곳 이상에 있는가
- [ ] 두 곳의 차이가 **매개변수로 표현 가능한가** (출력 크기 · 후처리 여부)
- [ ] 각 공개 함수의 주석이 실제 동작과 일치하는가
- [ ] 차이(대비를 거는가/안 거는가)가 **테스트로 고정**돼 있는가

## 올바른 대안

구현 한 벌 + 플래그. 공개 함수 둘은 출력 크기와 후처리만 다르게 감싼다.

```dart
OcrFrame? _warpQuad(bytes, quad, outW, outH, {required bool stretchContrast})
```

## Grounding (References)

- `doc/raw/2026-09-02.md#case-10` (`hash:d7042da`)
- `test/features/scan_photo_perspective_warp_test.dart` 그룹 'warpQuadToRect'
