# 생성기 품질 기준선 — 합성만 학습해 실사진에서 잰다 (2026-09-11)

- 브랜치: `glm/atlas` (워크트리 `D:\Project\sugarScan-glm-atlas`)
- 상태: 완료
- 측정 스크립트: `assets_dev/train/eval_generator_baseline.py`(신규 커밋)
- 산출: `_diag/device_split/eval_pre_v1_by_device.json`(공유 접합) ·
  `reader_preds_pre_v1.json`(워크트리 로컬, gitignore 관례)

## 무엇을 했나

**pre 단계(합성만 40에폭) 체크포인트를 기기 단절 홀드아웃 1,138장에서
eval_reader.py 프로토콜 그대로(TTA 8+기본, crc32 시드, 득표율 거절 0.778) 재고
네 층으로 집계했다.** 체크포인트는 재학습하지 않고 기존
`train_device/checkpoints_v2/pre_best.weights.h5`(2026-09-11 02:02) 를 썼다 —
카드 Notes 가 허용한 절약 경로다. 출처 검증은 아래 '검증' 절.

### 기준선 수치 (AC #1)

| 층 | pre(합성만) | ft(같은 체크포인트→실사진 60에폭) |
|---|---|---|
| 완전일치 | **0 / 1,138 (0.00%)** | 1,087 / 1,138 (95.52%) |
| 위험(자릿수 보존 오독) | **34 (2.99%)** | 28 (2.46%) |
| 안전 실패(자릿수 변동) | **392 (34.45%)** | 23 (2.02%) |
| 무출력 | **712 (62.57%)** | 0 |
| 거절(득표율 < 0.778) | 699 (61.4%) | 83 |

ft 열은 기존 기록이다 — `_diag/device_split/eval_by_device.json`, 같은
pre_best 에서 `ctc_reader_v2.py ft 60 --data-root ../train_device`(최종 ft 손실
0.200)로 이어진 모델의 평가. 프로토콜 동일(TTA·crc32·0.778). 출처:
`docs/reports/device-holdout-eval-2026-09-11.md` 재현 절 1~4.

**읽는 법 (AC #3)** — 두 수치의 격차 95.52pp 가 '파인튜닝이 덮는 양'이다.
현 구조에서 합성 생성기는 최종 성적에 직접 기여하는 것이 사실상 0이고(완전일치
0), ft 이 실사진 1,356장으로 사실상 전부를 다시 학습한다. 즉 생성기 개선의
효과는 최종 성적으로는 절대 안 보이고, **이 pre-only 지표로만 잡힌다.**
주목할 디테일: 실사진을 한 장도 못 본 모델에서도 위험층 34건이 이미 나온다 —
'그럴듯한 오독'은 실사진 학습 없이도 생성기의 편향만으로 발생할 수 있다.

기기별: 24개 홀드아웃 기기 전부 완전일치 0. 무출력 비중이 큰 기기: Gmate
80/89, GC 녹십자 MS/Green Doctor 51/55, GC 녹십자 MS ONE 49/52, ACURA PLUS
38/40, CareSens N 108/240. (전체 표: `eval_pre_v1_by_device.json`)

## 왜 그렇게 했나

- **완전일치 0 이 측정 버그가 아님을 새니티로 묶었다.** 같은 체크포인트로 합성
  검증셋(synth_val 앞 300장, greedy)을 읽히니 **279/300(93%) 완전일치** —
  모델·로드·디코드는 정상이고, 실사진 0% 는 도메인 갭 그 자체다. 이 갭의
  항목별 정체가 바로 어제 아틀라스 카드의 D1~D12다.
- pre 체크포인트 재사용 전제(카드 Notes)를 두 겹으로 검증했다: ① 두 캐시의
  합성 배열이 바이트 동일(md5 전체 일치) — pre_best 의 합성이 현행
  synth_lcd.py 산출과 같다. ② device-holdout-eval 보고서가 같은 파일을 ft 의
  시작점으로 기록 — ft 와 같은 혈통이므로 나란히 놓을 수 있다.
- eval_reader 가 원본 jpg 를 다시 워프하지만 이는 프로토콜의 정본(학습과 같은
  build_cache_v2 프레이밍)이라 그대로 썼다. hold-out 정의는 기기 단절 캐시의
  real_train_ids 1,356장 제외 — 평가 대상 1,138장이 기기 단절 홀드아웃 전량과
  정확히 일치한다.

## 검증

```
$ conda run -n sugartrain python eval_generator_baseline.py \
    --weights ../train_device/checkpoints_v2/pre_best.weights.h5 --name pre_v1
학습셋 1356장을 평가에서 제외한다 (캐시 기준)
hold-out total=1138 (skipped 0)
{"exact": 0, "risky": 34, "safe": 392, "blank": 712, "rejected": 699}

# 새니티(합성 검증셋, greedy, 커밋 안 한 일회 스크립트):
synth_val first300 exact greedy: 279/300

# 캐시 합성 배열 동일성:
train_device synth: (21850, 160, 320)  base: (21850, 160, 320)
hash first 200: b3727bd1630e86eec5fbb548d1a7f576 (양쪽 동일)
identical full: True
```

재현 명령(AC #2 — 이후 생성기 카드가 짝비교에 쓰는 명령):

```bash
conda run -n sugartrain python assets_dev/train/eval_generator_baseline.py \
    --weights <개선 생성기로 pre 40에폭 학습한 체크포인트> --name <카드슬러그>
```

스크립트는 ①아키텍처를 저장소 코드(ctc_reader_v2.build_model)로 세우고
pre 가중치만 얹고 ②eval_reader.py 를 같은 인자로 돌리고 ③device_eval_report.py
로 네 층 집계까지 한 번에 수행한다. 하이퍼파라미터·임계는 전부 불변.

## 건드리지 않고 남긴 것

- `synth_lcd.py` 한 줄도 고치지 않았다(카드 Notes — 기준선의 대상이 현재
  생성기 그 자체다).
- eval_reader.py·device_eval_report.py·ctc_reader_v2.py 수정 없음 — 래퍼만 추가.
- 옛 성적(97.06 등)과 나란히 두지 않았다. ft 열은 이 측정의 짝(같은 체크포인트
  혈통)으로만 인용했다.

## 막힌 것

- 없음. 단 완전일치 0% 라는 기준선의 해석은 남은 것: pre-only 성적이 바닥이라
  생성기 카드들의 개선 폭을 재기엔 좋은 출발점이지만, 위험층 34건의 성격
  (어떤 혼동쌍인가)은 이 카드 범위 밖이라 따로 보지 않았다.
