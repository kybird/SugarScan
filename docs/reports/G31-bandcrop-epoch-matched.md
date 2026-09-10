# G31 — 밴드 크롭 팔을 기준선과 같은 학습 예산으로 다시 잰다

- 브랜치: `glm/G31-bandcrop-e60`
- 커밋: 코드 커밋(드라이버) + 이 보고서 커밋
- 상태: 완료 — **채택/기각 판정은 이 문서가 하지 않는다.** 수치를 냈고 거기서 멈춘다.

## 요약 — 세 줄

1. **파인튜닝 예산을 12에폭 → 60에폭으로 맞추자 크롭만 팔의 완전일치는
   87.79% → 95.72%, 위험군(자릿수 보존 오독)은 8.29% → 3.48%** 로 움직였다.
   기준선은 97.06% / 0.98%. McNemar p 는 1.7e-23 → **0.0357**.
2. **예산 일치 확인**: 이번 팔의 파인튜닝은 60에폭 · 최종 손실 **0.1095**,
   기준선 마지막 런은 60에폭 · **0.1238**. G30 의 12에폭 팔은 0.9616 에서
   멈춰 있었다.
3. **60에폭 끝에서도 손실은 하강 중**(마지막 5에폭 0.2448 → 0.1095).
   지시서대로 그렇게 적고 멈췄다. 에폭을 더 늘리지 않았다.

## 무엇을 했나

- `assets_dev/train/g31_ft_e60.py` 신규 — `g30_ft_nojit.py` 의 복사본에서
  **파인튜닝 에폭 수(12→60)와 산물 이름만** 바꿨다. 학습 결과에 영향을 주는
  변경은 에폭 수 하나다. 그 밖의 차이는 기록용 추가 두 가지뿐이다:
  `CSVLogger`(60에폭 손실 곡선이 보고서에 필요)와 최종 가중치 저장
  (`checkpoints_v2_bandcrop_ty008_e60/ft_last.weights.h5`). 둘 다 fit 뒤
  평가·저장 경로이며 학습 동역학을 바꾸지 않는다.
- 사전학습은 다시 하지 않았다. G30 이 만든 `checkpoints_v2_bandcrop/
  pre_best.weights.h5` 를 출발점으로 읽기만 했다(조기중단이 스스로 멈춘
  단계라 예산 불일치가 없다).
- 캐시는 `data_cache_v2_bandcrop.npz`(G30 산물)을 그대로 재사용했다.
  재생성하지 않았다.
- 산물(전부 신규 이름. G30 산물 미건드림): `reader_model_bandcrop_ty008_e60` ·
  `reader_preds_bandcrop_ty008_e60.json`(TTA) ·
  `training_log_bandcrop_ty008_e60.csv` · `checkpoints_v2_bandcrop_ty008_e60/`.
- 평가는 G30 과 같은 경로: `eval_reader.py --model
  reader_model_bandcrop_ty008_e60 --cache data_cache_v2_bandcrop.npz
  --bandcrop --out reader_preds_bandcrop_ty008_e60.json`(TTA_N=8 ·
  TTA_SEED=7 · crc32 시드, 불변), 보고는 `g30_ab_report.py` 를 그대로.
- 학습 중 이어붙이기는 없었다. **재시작 0회, 1회 연속 실행.**

### 두 드라이버의 diff (주석 제외, CR 정규화 후)

```text
< C.CKPT_DIR = TRAIN / "_diag" / "G30" / "probe_ckpt"
> C.CKPT_DIR = TRAIN / "checkpoints_v2_bandcrop_ty008_e60"
< C.CSV_LOG = TRAIN / "training_log_bandcrop_ty008.csv"
< C.OUT_DIR = TRAIN / "reader_model_bandcrop_ty008"
< C.OUT_PREDS = TRAIN / "reader_preds_bandcrop_ty008.json"
> C.CSV_LOG = TRAIN / "training_log_bandcrop_ty008_e60.csv"
> C.OUT_DIR = TRAIN / "reader_model_bandcrop_ty008_e60"
> C.OUT_PREDS = TRAIN / "reader_preds_bandcrop_ty008_e60.json"
< FT_EPOCHS = 12
> FT_EPOCHS = 60
> C.CKPT_DIR.mkdir(exist_ok=True)
<     epochs=FT_EPOCHS, verbose=2)
>     epochs=FT_EPOCHS, verbose=2,
>     callbacks=[tf.keras.callbacks.CSVLogger(str(C.CSV_LOG))])
> train_model.save_weights(str(C.CKPT_DIR / "ft_last.weights.h5"))
```

`C.TRANS_Y = 0.08`, `C.CACHE`, `build_model()`, `make_ds(..., C.FT_BATCH,
shuffle=True, augment=True)`, 사전학습 best 로드 — 전부 g30_ft_nojit.py 와
동일하다.

## 결과 — 숫자만

### 예산이 맞았는가 — 손실 나란히 보기

`training_log.csv`(기준선, reader_model/ 과 mtime 동일)의 파인튜닝 구간은
재시작 7회(30·10·40·60·60·60·60에폭)로 쌓여 있고 **마지막 런이 60에폭 ·
최종 손실 0.1238**(직전 두 런 60에폭 · 0.1347 · 0.1021)이다. 각 런은
사전학습 best 에서 다시 시작하는 구조라, 마지막 런 = 사전학습 best + 60에폭 —
이번 팔(bandcrop 사전학습 best + 60에폭)과 짝이 맞는다.

| | 파인튜닝 에폭 | 12에폭 지점 손실 | 30에폭 지점 손실 | 최종 손실 |
|---|---|---|---|---|
| 기준선 마지막 런 (`training_log.csv`) | 60 | 0.5601 | 0.2668 | **0.1238** |
| 기준선 직전 런 (참고) | 60 | — | — | 0.1347 / 0.1021 |
| **G31 크롭만 팔 e60** | 60 | 0.9142 | 0.2754 | **0.1095** |
| G30 크롭만 팔 (참고, 예산 불일치) | 12 | 0.9616(최종) | — | — |

### A/B 표 (`g30_ab_report.py` — G30 보고서와 같은 표)

평가 장수(두 팔 공통): 1,122

| | 기준선(A·스트레치) | 크롭만 팔 60에폭(B) | G30 의 12에폭 팔(참고) |
|---|---|---|---|
| 완전일치 | 1089 (**97.06%**) | 1074 (**95.72%**) | 985 (87.79%) |
| 위험군(자릿수 보존 오독) | 11 (**0.98%**) | 39 (**3.48%**) | 93 (8.29%) |
| blank(침묵) | 3 (0.27%) | 0 (0.00%) | 0 (0.00%) |
| 안전 실패(자릿수 붕괴) | 19 (1.69%) | 9 (0.80%) | 44 (3.92%) |

McNemar(정확 이항): 기준선만 틀림 **b=15**, 크롭만 팔만 틀림 **c=30**,
**p = 0.0357**. (G30 12에폭 팔은 b=10, c=114, p=1.68e-23.)

드라이버 즉석 greedy 홀드아웃(참고): 1062/1122 = 94.7%
(G30 12에폭 팔의 greedy 는 904/1122 = 80.6%).

### 층별 정확도 (형태 = 원본 GM 박스 w/h>1.2 규칙, 두 팔 공통 1,122장)

| 층 | 장수 | A 정확도 | B(60에폭) 정확도 | B(12에폭, 참고) |
|---|---|---|---|---|
| 가로형(크롭 안 함) | 21 | 12/21 (57.1%) | 6/21 (28.6%) | 5/21 (23.8%) |
| 세로형(크롭) | 1100 | 1077/1100 (97.9%) | 1068/1100 (97.1%) | 980/1100 (89.1%) |
| 회전 제외(1564, 원본 박스) | 1 | 0/1 | 0/1 | 0/1 |

### 새로 틀린 장 — 크롭만 팔 60에폭 전체 30장 (id gt→B [A 는 전부 정답])

```text
glucose_batch1/1039 184→194  glucose_batch1/1055 177→171
glucose_batch1/1086 171→111  glucose_batch1/1094 97→74
glucose_batch1/1174 137→131  glucose_batch1/1324 439→139
glucose_batch1/1329 105→109  glucose_batch1/1602 168→160
glucose_batch1/1611 89→189   glucose_batch1/1613 95→57
glucose_batch1/1622 110→111  glucose_batch1/1643 114→117
glucose_batch1/1716 336→236  glucose_batch1/2039 141→111
glucose_batch1/211 200→208   glucose_batch1/2210 124→127
glucose_batch1/2407 62→63    glucose_batch1/36 172→179
glucose_batch1/393 100→108   glucose_batch1/499 158→188
glucose_batch1/530 80→180    glucose_batch1/536 89→189
glucose_batch1/538 93→193    glucose_batch1/669 82→182
glucose_batch1/710 100→180   glucose_batch1/946 112→122
glucose_batch1/95 172→142    glucose_batch1/950 93→99
glucose_batch1/956 120→100   glucose_batch2/2518 444→144
```

### 새로 맞은 장 — 15장 (A 만 틀림, B 정답)

```text
glucose_batch1/101 151→157 · 1099 108→106 · 1717 23→293 · 1718 15→158 ·
1951 14→144 · 213 38→381 · 220 370→270 · 247 24→294 · 42 120→150 ·
488 109→105 · 51 8→85 · 61 13→130 · 647 8→98 · 845 159→155 ·
glucose_batch2/2618 1711→171
```

(득표율 agree 포함 전체 데이터: `_diag/G31/ab_report_ty008_e60.json`)

### 파인튜닝 손실 곡선 60에폭 전체 (`training_log_bandcrop_ty008_e60.csv`)

```text
 1:7.3546   2:6.0908   3:5.7619   4:5.3606   5:4.2339
 6:3.0787   7:2.2229   8:1.5986   9:1.4246  10:1.1760
11:1.3018  12:0.9142  13:0.8266  14:0.6864  15:0.6278
16:0.5853  17:0.5715  18:0.5035  19:0.5503  20:0.4409
21:0.4314  22:0.3790  23:0.4508  24:0.5349  25:0.4311
26:0.4501  27:0.3365  28:0.4604  29:0.3894  30:0.2754
31:0.3302  32:0.3162  33:0.4852  34:0.5106  35:0.2957
36:0.2709  37:0.2350  38:0.2641  39:0.3845  40:0.3920
41:0.3229  42:0.2416  43:0.2605  44:0.2435  45:0.2256
46:0.1898  47:0.2068  48:0.1879  49:0.1834  50:0.2112
51:0.1670  52:0.2431  53:0.2947  54:0.3645  55:0.2763
56:0.2448  57:0.2244  58:0.1998  59:0.1424  60:0.1095
```

**마지막 에폭에서도 하강 중**이다(마지막 5에폭: 0.2763 → 0.2448 →
0.2244 → 0.1998 → 0.1424 → 0.1095). 지시서대로 에폭을 더 늘리지 않고
멈췄다.

## 실행 환경 특이사항

학습 중(16:19~18:34) 이 머신의 GPU/CPU 를 다른 프로세스가 함께 쓰고 있었다
(다른 프로젝트 세션의 `python -`, 게임 등 — 어느 쪽도 이 저장소 소속이
아니고 건드리지 않았다). 에폭 1~15 는 에폭당 95초~11분까지 늘어났다가
16에폭부터 경합이 풀려 에폭당 8~10초로 회복했다(86 steps, G30 관측과
동일 속도). **중단·재시작은 없었고 1회 연속 실행**이므로 예산은 60에폭
정확히다. 경합은 속도에만 영향을 주었고 학습 수식·시드·데이터는 무관하다.

## 왜 그렇게 했나

- **드라이버를 새 파일로 뗐다(`g30_ft_nojit.py` 미변경).** G30 의 12에폭
  결과가 그대로 재현 가능해야 하고, 본 스크립트(`ctc_reader_v2.py`)에
  에폭 노브를 추가하는 것은 "하이퍼파라미터를 바꾸지 말라"의 우회로가 된다.
- **CSVLogger·ft_last 저장만 추가했다.** 60에폭 손실 곡선과 12/30/60에폭
  지점 손실이 보고 요건이라 로그가 없으면 재측정조차 못 한다. 둘 다
  학습 결과에 영향을 주지 않는 기록 경로다.
- **재개(resume) 장치를 일부러 안 넣었다.** 중간에 죽으면 처음부터 다시
  돌리는 것이 지시서 요구다. 이어붙이면 예산이 쌓여 이 작업이 고치려는
  문제를 재현한다.
- **판정은 하지 않는다.** 어떤 격차가 "채택 가능"인지는 사람이 정한다.

## 검증

캐시(`python g30_check_cache.py` 재실행, 이번 작업 착수 시점) —
wide_ids 교차검증 1항목만 FAIL(지시서가 명시한 대로 G30 이 이미 보고한
사실 관계. 13장 목록도 동일), 나머지 전부 통과:

```text
[OK] real_train_ids: 1372 vs 1372, 순서일치=True, 집합일치=True
[OK] real_holdout_ids: 1122 vs 1122, 순서일치=True, 집합일치=True
[OK] 합성 항등: 500/500 픽셀 완전일치
[OK] 가로형 항등: 44장 전부 픽셀 일치 (불일치 0)
[OK] 회전 제외 항등: 1장 전부 픽셀 일치 (불일치 0)
[OK] 세로형 크롭됨: 2449장 전부 픽셀 불일치 (우연히 일치 0)
  형태 집계(실사진 2494장): 세로형(크롭) 2449 · 가로형 44 · 회전 제외 1
[FAIL] wide_ids.json 교차검증: 풀 내 47장 중 규칙-가로형 아님 13 [...]
[OK] 학습/추론 bandcrop 프레이밍 등가: 11/11 픽셀 완전일치
RESULT: FAIL (위 1항목 — G30 보고서의 '어긋남' 절에서 이미 설명된 사실)
```

- hold-out 분할은 기준선 캐시와 **순서까지 동일**(위 검증). 두 팔은 같은
  1,122장을 본다(`g30_ab_report.py` 의 키 집합 검사도 통과).
- TTA 시드는 `zlib.crc32`(43789ad) 그대로. TTA_N=8, TTA_SEED=7 불변.
- 세로 지터 0.08(0.15 아님), 가로 지터 0.08, BOX_MARGIN, 모델 구조, 학습률,
  배치 크기 전부 G30 과 동일 — diff 로 확인(위).
- 실행 로그: `_diag/G31/ft_e60.log`(학습 전체) · `eval_e60.log`(TTA 평가) ·
  `ab_report.log`(A/B).

flutter(파이썬만 건드렸으나 lib/ 우발 변경 게이트):

```text
flutter analyze  → No issues found! (ran in 75.8s)
flutter test     → All tests passed! (387 tests)
```

## 건드리지 않고 남긴 것

- `reader_model/` · `data_cache_v2.npz` · `reader_preds.json` ·
  `training_log.csv` · `checkpoints_v2/` — 읽기만 함.
- G30 산물 전부(`data_cache_v2_bandcrop.npz` · `checkpoints_v2_bandcrop/` ·
  `reader_model_bandcrop{,_ty008}` · `reader_preds_bandcrop{,_ty008}.json` ·
  `training_log_bandcrop.csv` · `g30_ft_nojit.py`) — 읽기만 함. 12에폭
  지점 관측값은 그대로 남아 있다.
- `band_crop_box` 구간 [0.00, 0.72] · 형태 판정 `w/h > 1.2` · BOX_MARGIN ·
  모델 구조 · 학습률 · 배치 크기 · TTA_N=8 · TTA_SEED=7 · 가로 지터 0.08 ·
  그 밖의 하이퍼파라미터 전부.
- `band_boxes.jsonl` · `band_rotation.jsonl` · `screen_boxes.jsonl` ·
  `wide_ids.json` — 읽기만 함.
- `lib/` 아래 전부 — 0줄. 새 파이썬 패키지 설치 없음.
- 채택/기각 판정, 에폭 추가, wide 13장 형태 판정 기준 수정 — 전부 사람 몫.
- 밴드크롭 e60 산물은 메인 트리에 남아 있다(gitignored): 필요 없어지면
  `data_cache_v2_bandcrop.npz`(G30 공유) 외에 `reader_model_bandcrop_ty008_e60` ·
  `reader_preds_bandcrop_ty008_e60.json` · `training_log_bandcrop_ty008_e60.csv` ·
  `checkpoints_v2_bandcrop_ty008_e60/` · `_diag/G31/` 삭제로 끝난다.

## 막힌 것

없음. (학습 속도 저하는 위 '실행 환경 특이사항'대로 외부 경합이었고
완주했다.)
