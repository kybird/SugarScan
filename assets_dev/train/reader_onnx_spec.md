# CTC 리더 ONNX — 입력·출력 규격 (정본)

2026-09-10 · `export_reader_onnx.py` 로 생성된 `reader_model.onnx` 의 계약.
온디바이스 런타임(패키지 미확정, 칸반 「온디바이스 ONNX 런타임 선택」 대기)은
이 문서를 따라야 한다. 학습-추론 전처리 일치(강화 프롬프트 §36)의 기준점.

## 파일

- `reader_model.onnx` — opset 13, 2,393,391 바이트(2.4 MB)
- 원본: `reader_model/`(Keras SavedModel, TF 2.10.1)의 logits 그래프
  (CTC 손실 레이어 제외 — 학습 전용)

## 입력

```text
이름   img
형태   [N, 160, 320, 1]  (NHWC)
dtype  float32
값     0.0 ~ 255.0 (정규화 금지 — 모델 첫 층 Rescaling(x/127.5 - 1) 이 처리)
```

## 출력

```text
형태   [N, 40, 11]  (시퀀스 40 = 320/2^3, 클래스 = 0~9 + blank 10)
dtype  float32 (logits)
```

## 디코딩

greedy CTC — argmax 시퀀스에서 반복 제거 후 blank(인덱스 10) 제거.
클래스 i → 문자 `str(i)`. **charset 은 0~9 뿐이다**(mg/dL 코퍼스).
소수점·HI/LO 등을 넣으려면 재학습이 필요하다(칸반 「dot·unit 지표 추가」).

## 프레임 조립(전처리 체인)

모바일에서 재현해야 할 순서. 좌표계 정본은 **EXIF 적용 표시 좌표계**(G20/G22).

1. 디코드 + `exif_transpose` (표시 좌표계)
2. GM 검출기 쿼드(4점) 확보 — 앱에서는 검출기 미탑재, 가이드 박스 ROI 로 대체
   하는 경로가 별도 과제다.
3. 쿼드를 `BOX_MARGIN = (0.10, 0.10, 0.10, 0.10)`(좌우상하) 로 사방 확장
   — `build_cache_v2.py` 의 관례. **학습과 추론이 갈라지면 그 자체가 성능 저하다.**
4. 확장 쿼드 → 원근 워프로 `320×160` 리사이즈( cv2.warpPerspective 기본 bilinear )
   — 참조 구현 `eval_reader.py` 의 `framed_src_rect`/`frame_crop`
5. 그레이스케일 uint8 → float32 [N,160,320,1] (0~255)

## 검증 기록

- 파리티(2026-09-10, `export_reader_onnx.py`): 캐시 홀드아웃 **1,122장 전량**
  TF vs ONNX Runtime 디코드 **100% 완전일치**, logits 최대 절대차 0.006
  (float32 수준). 상세 `_diag/reader_onnx_parity.json`.
- 모바일 latency·메모리는 미측정(런타임 패키지 확정 후).

## 환경 주의 (sugartrain)

TF 2.10.1 환경에 무심코 최신 tf2onnx 를 깔면 numpy 2.x·protobuf 7 이 따라와
**TF 임포트가 죽는다**(bfloat16 TypeError). 이 환경의 호환 조합:
`numpy 1.23.5 · protobuf 3.20.3 · onnx 1.13.0 · tf2onnx 1.12.0 · ort 1.23.2`.
onnx 1.22 이상은 numpy≥1.25 를 요구해 TF 2.10 과 양립 불가 — 올리지 말 것.
