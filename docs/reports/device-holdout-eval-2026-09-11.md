# 미학습 기기 성적 — 완전일치 95.52% / 위험 2.46% (세션 무결 기준선 대비 -1.15pp / +0.95pp)

2026-09-11 · 칸반 카드 「미학습 기기 성적을 잰다」.
전제: [`device-split-cache-2026-09-11.md`](device-split-cache-2026-09-11.md) —
기기 단절 분할(train 1,356 / holdout 1,138, 홀드아웃 24종).

## 한 줄 결론

처음 보는 기기에서 CTC 리더는 **완전일치 95.52% / 위험(자릿수 보존 오독)
2.46%** 다. 세션 무결 기준선 96.67% / 1.51% 에서 **각각 -1.15pp / +0.95pp**
잃는다. 이 격차가 '처음 보는 기기에서 잃는 실력'의 첫 측정치다.

## 방법 — 선례(grouped-split-rebaseline)와 같은 절차

1. **같은 사전학습 체크포인트**: `checkpoints_v2/pre_best.weights.h5`(원본
   2,417,832 바이트)를 `train_device/checkpoints_v2/` 로 복사. 실행 로그에
   `pre_best 로드: ..\train_device\checkpoints_v2\pre_best.weights.h5` 확인.
2. **같은 예산**: `ctc_reader_v2.py ft 60 --data-root ../train_device` —
   로그에 `Epoch 1/60` … `Epoch 60/60`(85/85 step). 최종 ft 손실 0.200
   (CSV 59행 0.1999). 바꾼 것은 ft 데이터의 기기 구성뿐이다.
   참고: 훈련 직후 비TTA 평가 93.0%(1,058/1,138), 학습셋 참고 98.0%(588/600).
3. **같은 평가 프로토콜**: `eval_reader.py --data-root ../train_device
   --out reader_preds_tta.json` — TTA 8회+기본(crc32 시드), 득표율 다수결.
   `hold-out total=1138 (skipped 0)` — 캐시 real_train_ids 1,356장 제외와
   정확히 일치.
4. 네 층 집계·기기별 표: `device_eval_report.py` →
   `_diag/device_split/eval_by_device.json`.

## 결과 — 두 기준선을 나란히

| 층 | 세션 무절 기준선(1,322장) | **기기 단절(1,138장)** | 차이 |
|---|---|---|---|
| 완전일치 | 96.67% (1,278) | **95.52% (1,087)** | **-1.15pp** |
| 위험(자릿수 보존 오독) | 1.51% (20) | **2.46% (28)** | **+0.95pp** |
| 안전 실패(자릿수 변동) | 1.66% (22) | 2.02% (23) | +0.36pp |
| 무출력(blank) | 0.15% (2) | 0.00% (0) | -0.15pp |
| 득표율 거절(agree<0.778) | 6.4% (85) | 7.29% (83) | +0.9pp |

**두 수치는 같은 시험지가 아니다**(AC 주의). 세션 무절 홀드아웃 1,322장과
기기 단절 홀드아웃 1,138장은 구성이 다르고, 기기 단절이 더 엄격한 조건이다
(기기가 갈리면 그 기기의 장면도 함께 갈린다 — 세션 누수가 구조적으로 있을 수
없다). 비교의 의미는 "난이도가 다른 시험에서의 낙폭"이며, **격차가 곧 처음
보는 기기에서 잃는 실력**이다.

## 기기별 성적 (홀드아웃 24종)

| 사진 | 일치 | 일치% | 위험 | 안전 | 거절 | 기기 |
|---:|---:|---:|---:|---:|---:|---|
| 240 | 237 | 98.8 | 1 | 2 | 7 | CareSens N |
| 156 | 154 | 98.7 | 1 | 1 | 2 | 오토-첵 |
| 89 | 71 | **79.8** | **12** | 6 | 21 | **Gmate** |
| 80 | 80 | 100.0 | 0 | 0 | 0 | HANDOK BAROZEN |
| 79 | 79 | 100.0 | 0 | 0 | 2 | ACCU-CHEK Performa(은색 각진버튼) |
| 60 | 58 | 96.7 | 2 | 0 | 7 | SD CodeFree |
| 59 | 54 | 91.5 | 4 | 1 | 8 | ACCU-CHEK Performa Nano(파랑 케이스) |
| 59 | 59 | 100.0 | 0 | 0 | 0 | CareSens Dual |
| 55 | 53 | 96.4 | 0 | 2 | 4 | GC 녹십자 MS Green Doctor |
| 52 | 49 | 94.2 | 2 | 1 | 4 | GC 녹십자 MS ONE |
| 40 | 38 | 95.0 | 1 | 1 | 4 | ACURA PLUS |
| 34 | 26 | **76.5** | 1 | **7** | 15 | **ACCU-CHEK Instant** |
| 30 | 29 | 96.7 | 1 | 0 | 2 | OneTouch Ultra |
| 30 | 29 | 96.7 | 1 | 0 | 0 | MaeilzeN |
| 29 | 29 | 100.0 | 0 | 0 | 1 | CareSens N Premier |
| 14 | 14 | 100.0 | 0 | 0 | 0 | gDoctor |
| 10 | 9 | 90.0 | 0 | 1 | 1 | Dr.Diary+ |
| 6 | 6 | 100.0 | 0 | 0 | 1 | FORA |
| 4 | 3 | 75.0 | 0 | 1 | 1 | ACURA VIEW |
| 3 | 1 | **33.3** | 2 | 0 | 1 | **도루코S Premium** |
| 3 | 3 | 100.0 | 0 | 0 | 0 | ACCU-CHEK Active(원형베젤) |
| 3 | 3 | 100.0 | 0 | 0 | 0 | Boryung CareTouch(일반LCD) |
| 2 | 2 | 100.0 | 0 | 0 | 2 | Contour TS |
| 1 | 1 | 100.0 | 0 | 0 | 0 | VERI-Q |

(무출력 0건 전 기기. 12종이 100% 다. 오답 51건 중 26건(51%)이 Gmate 18 +
Instant 8 두 기기에 몰려 있다.)

## 무너진 기기의 눈검증 소견 (AC4)

`_diag/device_split/miss_*.png` 몽타주(모델 입력 320×160 워프 그대로)를
유툴로 읽었다. GT 는 가시 판독과 사실상 일치(라벨 오염 아님) — 실패는
전부 모델 쪽이다.

- **Gmate(18건)**: 압도적 패턴은 **숫자 오른쪽 글리프 삼키기** — "mg/dL"
  단위 글자·배터리/아이콘이 마지막 숫자에 붙어 `7`이나 `1`로 판독됨
  (GT 121→127, 61→617, 237→2397 등). 그다음으로 **흐린 선행 자리 탈락**
  (316→16, 381→81, 202→20), glare 로 `0`→`6`·`8`→`6` 혼동(130→136, 108→106).
  위험 12건 대부분이 여기서 왔다.
- **ACCU-CHEK Instant(8건)**: **오른쪽 화살표 표시를 끝자리 `1`로 붙임**이
  8건 중 5건(123→1231, 157→1571, 261→2611, 126→1261, 206→2061). 안전 실패
  7건의 대부분. 1장(151→11)은 GT 151 vs 가시 131로 **GT 의심** — 라벨은
  읽기 전용 자산이므로 사람 확인 대상으로만 적어둔다.
- **도루코S Premium(3장 중 2오답)**: 7-세그 숫자 위·아래 도트매트릭스
  (날짜/시간 줄)가 붙어 `8`→`0` 등 자리 붕괴(187→101). 표본 3장이라
  통계로는 약하지만 레이아웃 난이도는 실재한다.

요약: 미학습 기기에서 잃는 실력의 실체는 **낯선 인접 글리프(단위·아이콘·
화살표)를 숫자로 읽는 것**과 **낯선 게시 스타일의 흐림/고스트 처리**다.
숫자 자체의 판독(학습된 기기에서와 같은)은 대부분 온존한다 — 12종이 100%인
것이 그 증거다.

## 다음 작업으로 이어지는 해석

- 오답의 주된 축이 "기기 레이아웃 다양성 부족"이므로, 카드 3(기기 편중
  완화 — 상위 4종 30% 절단 재학습)이 정확히 이 지점을 찌른다.
- Gmate·Instant 스타일(숫자 옆 글리프)은 합성 렌더러가 반영하지 못한
  변인으로 보인다 — 편중 완화에서 안 오르면 렌더러 실화면화(기존 권고)가
  다음 후보다.

## 재현

```bash
cd assets_dev/train
# 1) 기기 단절 캐시(카드 1)
C:/Users/admin/miniconda3/envs/sugartrain/python.exe build_device_split.py
# 2) 평가 지원 파일 + 사전학습 체크포인트 복사
cp gmscreen_quads.jsonl gt_corrections.jsonl band_rotation.jsonl ../train_device/
mkdir -p ../train_device/checkpoints_v2
cp checkpoints_v2/pre_best.weights.h5 ../train_device/checkpoints_v2/
# 3) 재학습 — 로그에서 "pre_best 로드"와 Epoch 60/60 확인(예산 증거)
C:/Users/admin/miniconda3/Scripts/conda.exe run -n sugartrain python ctc_reader_v2.py ft 60 --data-root ../train_device
# 4) TTA 평가(crc32 시드)
C:/Users/admin/miniconda3/Scripts/conda.exe run -n sugartrain python eval_reader.py --data-root ../train_device --out reader_preds_tta.json
# 5) 네 층 + 기기별 집계
C:/Users/admin/miniconda3/envs/sugartrain/python.exe device_eval_report.py
```

산출물(전부 gitignored): `train_device/`(캐시·checkpoints·reader_model·
reader_preds_tta.json), `_diag/device_split/`(eval_by_device.json·miss_*.png).
커밋되는 것: `device_eval_report.py`·이 보고서.
