---
status: active
version_context: "sugartrain conda env (TF 2.10.1) · tf2onnx"
tags: [environment, ml, anti-pattern]
aliases: [고정 환경 pip, 의존성 상승 파손, numpy 2 충돌, TF_bfloat16 TypeError, dependency drift, pip resolver]
created: 2026-09-10
confidence: 5
---
# 돌아가는 훈련 환경에 버전 못박은 pip 설치를 하는 것

pip 의존성 해결기는 **요구를 만족하는 조합**을 찾을 뿐 **기존 워크로드가 돌아가는
조합**을 보존하지 않는다. 고정된 훈련 환경에 버전을 못박지 않고(최신 패키지 설치)
들어가면 체인 전체가 끌려 올라가 다음 날 학습이 죽어 있다.

## 실패 모드

sugartrain(TF 2.10.1) 에 `pip install tf2onnx`(최신) 한 방으로:

```text
numpy 1.23.x → 2.2.6   ← 원인
protobuf 3.x → 7.36.1
onnx 1.22.0 → (후속 하강)
```

`import tensorflow` 즉사:

```text
_np_bfloat16 = _pywrap_bfloat16.TF_bfloat16_type()
TypeError: Unable to convert function return value to a Python type!
The signature was () -> handle
```

**이 시그니처를 보면 numpy 2.x 를 먼저 본다.** protobuf 를 먼저 의심해 protobuf만
내리면 소용없다(실제 3차례 왕복했다). TF<2.11 은 numpy 2.x 와 pybind11 타입
체계가 맞지 않는다.

호환 조합은 요건이 교차하는 좁은 지점에만 존재했다:

```text
numpy 1.23.5 · protobuf 3.20.3(신·구 pb2 다리 버전) · onnx 1.13.0
(1.22+ 는 numpy≥1.25 요구 → TF 2.10 과 양립 불가) · tf2onnx 1.12.0
```

복구 후에는 임포트뿐 아니라 **미니 Keras fit** 으로 훈련 경로까지 검증했다.

## 점검 체크리스트

- [ ] 공유 환경에 새 패키지를 설치하기 전 `pip install <pkg>==<version>` 으로
      **버전을 못박았는가** — 못박지 않으면 해결기가 체인을 재배치한다
- [ ] 설치 직후 `pip check` 와 핵심 워크로드 임포트(TF·torch 등)를 돌렸는가
- [ ] 실패 시 가장 최근에 **의존성이 상승한 패키지**(pip log)부터 봤는가
- [ ] 복구 조합을 환경별 문서에 남겼는가(예: reader_onnx_spec.md 말미)
- [ ] 검증은 임포트로 끝내지 않고 최소 학습 루프까지 돌렸는가

## 왜 이게 반복되는가

설치는 즉시 성공하고 워크로드는 나중에 도니 **원인과 증상이 시간적으로 분리**된다.
게다가 pip 의 경고문(requires ... but you have ...)은 항상 떠 있어서 치명적인
상승과 무해한 상승이 같은 경고로 보인다. 경고 전체를 읽는 대신 "돌아가는 조합"을
버전 몇 개로 고정해 기록하는 것이 유일한 방어다.

## Related

- [[tolerance-without-preservation]] — 같은 뿌리: 요건 충족과 원본 보존은 다르다
- [[experiment-budget-parity]] — 환경 드리프트는 재현성의 적
- [[dry-run-before-repair]] — 복구도 검증 가능한 최소 단위로

## Grounding (References)

- `doc/raw/2026-09-10.md` Case 1
- `docs/reports/reader-onnx-parity-2026-09-10.md` §환경 사고·복구 기록
- `assets_dev/train/reader_onnx_spec.md` 말미(고정 조합)
