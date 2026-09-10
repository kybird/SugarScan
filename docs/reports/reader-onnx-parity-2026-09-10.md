# CTC 리더 ONNX 내보내기 파리티 — 2026-09-10

칸반 카드 「CTC 리더 ONNX 내보내기 파리티」 결과. 방향 결정 근거: G28(tflite
불가)·커밋 86d3dbe(ONNX 확정).

## 결과

| 항목 | 값 |
|---|---|
| 산출물 | `assets_dev/train/reader_model.onnx` (opset 13, 2.4 MB) |
| 파리티 대상 | 캐시 홀드아웃 **1,122장 전량** |
| 디코드 완전일치 | **1,122 / 1,122 (100%)** |
| logits 최대 절대차 | 0.0060 (float32 수준) |
| 배치별 평균 차 | 0.0049 |
| 전처리 규격 | `assets_dev/train/reader_onnx_spec.md` (정본) |

방법: `export_reader_onnx.py` — Keras logits 그래프(CTC 손실 제외)를
tf2onnx(opset 13) 로 변환, 학습 캐시(`data_cache_v2.npz`)의 홀드아웃 배열을
TF 와 ONNX Runtime 양쪽에 동일 투입해 greedy 디코드를 비교했다. 캐시 배열을
그대로 쓰므로 전처리 동일성은 구조적으로 보장된다(§36).

스모크(64장) → 전량(1,122장) 순으로 확인했다. 중간 수정 한 건: 입력 채널 축
누락(3 rank → 4 rank)은 호출측 수정으로 해결, 모델은 무결.

## 남은 것(이 카드 범위 밖)

- 모바일 런타임 패키지 선택·실기기 벤치마크(p50/p95·메모리) — 칸반
  「온디바이스 ONNX 런타임 선택」(사람 판정 대기).
- 앱 내 GM 검출기 탑재(현재 앱은 가이드 박스 수동 ROI).
- charset 0~9 한정 — 소수점·상태 문자 확장은 재학습 필요.

## 환경 사고·복구 기록 (sugartrain, 밤샘 중 발생)

`pip install tf2onnx`(최신)가 numpy 2.2.6·protobuf 7.36.1 을 끌어와 **TF 2.10.1
임포트가 죽었다**(`TF_bfloat16_type()` TypeError). 복구: `numpy==1.23.5` 복원이
핵심이었고, protobuf 는 3.20.3(신·구 pb2 를 모두 지원하는 다리 버전), onnx 는
1.13.0(1.22.0 은 numpy≥1.25 를 요구해 TF 와 양립 불가 — 원래 환경에서도
임포트 불가 상태였을 것), tf2onnx 1.12.0. 최종 네 모듈 임포트 + 미니 Keras
fit(`TRAIN OK`)로 훈련 경로까지 검증했다. 현재 조합은
`reader_onnx_spec.md` 말미에 기록.
