# CTC 리더 학습 파이프라인 재설계 계획서

> 작성: 2026-08-30 · 작성자: 에이전트 (ZCode)
> 상태: 초안 — subagent 리뷰 대기
> 목적: 15시간 학습 실패의 원인 분석 및 재발 방지 설계

---

## 1. 배경 및 현재 상태

### 1.1 프로젝트 컨텍스트
- SugarScan: 혈당계 LCD 사진 → 수치 판독 (Flutter 앱)
- 현재 단계: ML 판독기(CTC 리더) 학습 — 사진 → GM 박스 검출(79.9%) → 화면 펴기 → CTC 판독
- 학습 데이터: 합성 LCD 화면 23,000장 + 실사진 240장 rect (320×160 grayscale)
- 학습 환경: RTX 4070 Laptop 8GB, TensorFlow 2.10.1 (CPU 모드), Python 3.10

### 1.2 발생한 문제
- 학습 시작 17:43 → 현재 09:01 = **15시간 18분 경과**, 완료 안 됨
- 로그가 stdout 버퍼링으로 파일에 기록 안 됨 → 진행률 파악 불가
- 체크포인트 없음 → 중단 시 15시간 전부 손실
- GPU 사용률 33~68% 변동 — 풀 가동 아님

### 1.3 확인된 설계 결함

| 결함 | 영향 | 심각도 |
|---|---|---|
| 데이터 로딩: 매 스텝 JPEG 디코딩 (단일 스레드) | GPU 유휴 시간 증가 | 높음 |
| 체크포인트 부재 | 중단 시 전체 손실 | 높음 |
| 진행률 불가시 (stdout 버퍼링) | 학습 상태 파악 불가 | 중간 |
| 에폭당 23k JPEG 재디코딩 | 반복 실험 비효율 | 높음 |

---

## 2. 원인 분석

### 2.1 데이터 로딩 병목 (가설 1 — 미검증)
- 현재: 매 스텝마다 16장 × cv2.imread + resize (단일 스레드 Python)
- 23k 이미지 × 40 에폭 = 920,000회 디스크 읽기 + JPEG 디코딩
- 추정: 이미지당 30~50ms → 스텝당 0.5~0.8s → 에폭당 12~20분
- **검증 필요**: 프로파일링으로 데이터 로딩 vs GPU 연산 시간 분리 측정

### 2.2 BiLSTM 순차 연산 (가설 2 — 미검증)
- LSTM은 타임스텝 간 의존성 때문에 GPU 병렬화 효율이 낮음
- 40 타임스텝 × BiLSTM(96×2) — 모델은 작지만 순차 병목 가능
- **검증 필요**: GPU util이 BiLSTM 구간에서 떨어지는지 확인

### 2.3 CTC loss 연산 (가설 3 — 낮음)
- tf.nn.ctc_loss는 일반적으로 효율적
- 40 타임스텝 × 배치 16이면 부담 적음

---

## 3. 수정 계획

### 3.1 [최우선] 프로파일링 — 병목 실측

수정 전에 반드시 측정. 추측으로 최적화하면 또 틀린다.

```
측정 항목:
  A. 이미지 로딩+디코딩 (1장당 시간)
  B. 배치 구성 시간
  C. GPU 순전파+역전파 시간
  D. CTC loss 계산 시간

방법: 10 샘플로 각 단계 시간 측정 (time.perf_counter)
예상 소요: 10분
```

### 3.2 [프로파일링 결과별] 병목 수정

| 프로파일링 결과 | 수정 방안 | 예상 효과 |
|---|---|---|
| 데이터 로딩이 병목 | .npz 캐시 (한 번 디코딩 → RAM) | 에폭당 15분 → 30초 |
| BiLSTM이 병목 | conv-only 구조 검토 또는 LSTM 축소 | 모델 변경 필요 — 검토 |
| 둘 다 | 조합 적용 | |

**.npz 캐시 설계**:
```
파일: assets_dev/train/data_cache.npz
내용:
  - synth_images: (23000, 160, 320) uint8 — 약 1.2GB
  - synth_labels: (23000,) 문자열 배열
  - real_images: (240, 160, 320) uint8
  - real_labels: (240,) 문자열 배열
로딩: np.load(...) — 수 초
```

### 3.3 체크포인트·이어학습

```
목적: 학습 중단해도 이어서 재개 가능 + 최고 성능 모델 보존
구현:
  1. tf.keras.callbacks.ModelCheckpoint — 매 에폭 저장
  2. tf.keras.callbacks.EarlyStopping — val_loss 기반
  3. 초기화 시 latest_checkpoint 로드 → initial_epoch 설정
저장 항목:
  - 모델 가중치
  - 옵티마이저 상태
  - 에폭 번호
저장 위치: assets_dev/train/checkpoints/
```

### 3.4 진행률 가시화

```
문제: stdout 버퍼링으로 에폭 요약이 파일에 기록 안 됨
수정:
  1. python -u (언버퍼드) 또는 PYTHONUNBUFFERED=1
  2. 또는 tf.keras.CSVLogger 콜백 — 에폭마다 CSV 기록
  3. tf.keras.callbacks.TensorBoard — 선택사항
효과: 학습 중에도 진행률·loss 실시간 확인 가능
```

---

## 4. 재설계된 학습 파이프라인

```
[캐시 구축] (일회성, 40~60분)
  23k 합성 + 240 실사진 rect → npz 캐시
  
[학습] (캐시 사용, 에폭당 수 초 예상)
  tf.data.Dataset.from_tensor_slices(npz) 
  → shuffle(10000) → batch(32) → prefetch(AUTOTUNE)
  → MobileNetV2 전이 or 기존 CNN+BiLSTM (프로파일링 결과에 따라)
  → 40 에폭 (early stopping)
  
[평가]
  hold-out 1,767장 → 완전일치 % 산출
```

---

## 5. 체크포인트·이어학습 설계

```
목적: 언제든 중단해도 이어서 재개 가능
구현:
  1. tf.keras.callbacks.ModelCheckpoint(
       filepath='checkpoints/epoch_{epoch:02d}_loss_{loss:.4f}',
       save_best_only=True, save_weights_only=False)
  2. 재개: model.load_weights(latest_checkpoint)
       + initial_epoch=저장된 에폭
검증:
  - 학습 5에폭 → 강제 종료 → 재시작 → 6에폭부터 이어지는지 확인
```

---

## 6. 성공 기준

| 기준 | 목표 |
|---|---|
| 에폭 시간 | < 30초 (캐시 사용 시) |
| hold-out 완전일치 | > 7.9% (기존 기준선) |
| 체크포인트 이어학습 | 중단→재시작 시 정확히 이어짐 |
| 진행률 가시화 | 학습 중 실시간 확인 가능 |

---

## 7. 리스크 및 대안

| 리스크 | 대응 |
|---|---|
| npz 캐시가 RAM 초과 | 1.2GB — 8GB RAM에 충분. 초과 시 memmap |
| 프로파일링 결과 예상과 다름 | 측정 결과에 따라 유연하게 수정 |
| BiLSTM 자체가 근본 병목 | conv-only CTC 구조로 전환 검토 |
| 데이터 자체가 부족 | 합성 렌더러 변주 확대 (별도 이슈) |

---

## 8. 실행 순서

```
1. [30분] 현재 학습 프로파일링 (병목 실측 — 수정 전 근거 확보)
2. [5분] .npz 캐시 구축 스크립트 작성
3. [40분] 캐시 생성 (23k+240장 디코딩 — 일회성)
4. [10분] ctc_reader_v2.py 작성 (캐시 로딩 + 체크포인트 + 이어학습)
5. [5분] 학습 실행 → 에폭 시간 확인
6. [3분] hold-out 평가
7. [판정] 기존 7.9% 대비
```
