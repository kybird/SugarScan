# G5 — 라이선스 문서의 "확인 필요" 채우기

- 브랜치: `glm/G5-license-audit`
- 커밋: `75b6302` (문서) + 보고서 커밋 (이 파일)
- 상태: 완료 (1건은 "확인 실패 — 이유" 로 기록)

## 무엇을 했나

- `docs/LICENSES.md` — 표의 "확인 필요" 7개 항목을 아래 표와 같이 채우고, 각 행에
  확인 URL 과 확인 날짜(2026-08-21)를 붙였다. §4 체크리스트 두 항목에 실사 결과를
  각주로 덧붙였다. 코드·의존성은 전혀 건드리지 않았다.

## 확인 결과 (전부 LICENSE 파일/저장소를 직접 열어 확인)

| 프로젝트 | 결론 | 근거 URL (2026-08-21 확인) |
|---|---|---|
| JaidedAI/EasyOCR (코드) | Apache-2.0 | https://github.com/JaidedAI/EasyOCR/blob/master/LICENSE |
| JaidedAI/EasyOCR (가중치) | **확인 실패** — README·공식 사이트(jaided.ai/easyocr)에 가중치 배포 조건 문구가 없음 | https://github.com/JaidedAI/EasyOCR · https://jaided.ai/easyocr |
| clovaai/CRAFT-pytorch | MIT (NAVER Corp.) — **연구용 한정 조항 없음** (LICENSE 원문·README 모두) | https://github.com/clovaai/CRAFT-pytorch/blob/master/LICENSE |
| clovaai/deep-text-recognition-benchmark | Apache-2.0 (파일명 `LICENSE.md`) | https://github.com/clovaai/deep-text-recognition-benchmark/blob/master/LICENSE.md |
| microsoft/onnxruntime | MIT (Microsoft Corporation) | https://github.com/microsoft/onnxruntime/blob/master/LICENSE |
| TensorFlow Lite (tflite_flutter 경유) | Apache-2.0 (TensorFlow 본저장소. 원문 말미에 Caffe 유래 고지 포함) | https://github.com/tensorflow/tensorflow/blob/master/LICENSE |
| scottmudge/SegoDec | Apache-2.0 (저작자명이 비어 있는 템플릿 원문) | https://github.com/scottmudge/SegoDec/blob/master/LICENSE |
| suyashkumar/seven-segment-ocr | **LICENSE 파일 없음** — 파일 목록에 라이선스 파일 자체가 없음 | https://github.com/suyashkumar/seven-segment-ocr |

## 왜 그렇게 했나

- EasyOCR 가중치는 "확인 실패 — 이유" 로 남겼다. 코드 LICENSE(Apache-2.0)를
  가중치까지 적용되는 것으로 추정해 채우는 선택이 있었지만, 지시서가 명시적으로
  금지한 추측이다. 공개 문서에 근거가 없으므로 "Jaided AI 문의 필요" 상태로
  두었다.
- seven-segment-ocr 는 "확인 실패"가 아니라 "**라이선스가 없다는 사실**을 확인"한
  경우라 표현을 구분했다. 라이선스 미기재는 기본적으로 전 저작권 보유를 뜻하지만
  이 프로젝트는 코드를 쓰지 않으므로 실무상 영향은 없다.
- CRAFT 의 "연구용 한정 조항" 은 당초 의심과 달리 없었다. LICENSE 원문은
  NAVER 명의 순수 MIT 이고 README 에도 어떤 제한 문구도 없다. 문서의 기존
  주석("연구용 조항 확인 요")을 이 결과로 바로잡았다.

## 검증

flutter analyze  → No issues found! (ran in 3.8s)
flutter test     → All tests passed! (329 tests)

(문서만 고친 작업이지만 §3.1 대로 둘 다 실행했다.)

## 건드리지 않고 남긴 것

- `7seg_classifier.tflite` (Kazuhito00/7segment-display-reader) 행 — 지시서의
  조사 대상 7개에 포함되지 않아 기존 기재(GitHub API 확인)를 그대로 두었다.
- 폰트(§2), Flutter 패키지(§3) — 대상 아님.

## 막힌 것

없음 — 다만 EasyOCR 가중치 조건은 공개 자료로는 결론을 내릴 수 없어 사람의
문의 절차를 `docs/LICENSES.md` §4 에 남겨 두었다.
