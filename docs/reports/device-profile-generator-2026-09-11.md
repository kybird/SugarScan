# 합성에 기기 프로파일 도입 — 레이아웃·아이콘·화살표 (2026-09-11)

- 브랜치: `glm/atlas` (워크트리 `D:\Project\sugarScan-glm-atlas`)
- 상태: 완료 — **효과는 정직하게: 순수 개선 아님(아래 AC#4)**
- 신규: `synth_profiles.py`(프로파일 정의+렌더) · `build_profiled_cache.py`(A/B 캐시)
- `synth_lcd.py` 는 한 줄도 고치지 않았다 — 기준선 팔의 생성기가 그대로 보존된다.

## 무엇을 했나

- **프로파일 10종을 데이터로 정의**(AC #1·#2) — 9종은 실사진 근거 id 와 함께,
  1종(generic_v1)은 기존 무작위 레이아웃(다양성 하한). 근거 id 는 전부 이번
  아틀라스 카드에서 워프 이미지를 직접 보고 기록한 것이다:
  accuchek_instant(267·270·2610·2492·2039 — 화살표 갭 실측 72~84px) ·
  gmate(842·843·731·727 — 단위 글리프 4~5px 부착) ·
  dorucos_premium(120·694·695 — 도트매트릭스 줄, 좌정렬) ·
  green_doctor(1781·2498 — GLU 상단·M박스·삼각형·물리버튼) ·
  onetouch_ultra(1058·2110 — 이탤릭 숫자·단위 왼쪽) ·
  gc_ms_one(228·373·800 — M박스·GLU·도트 하단줄) ·
  acura_plus(475·477·2357 — DAY AVG 평균줄) ·
  caresens_n_premier(1911·1903 — 도트매트릭스 날짜·시각) ·
  performa_silver(1186 — 상단 단위·memory 표기·기록줄).
  프로파일 속성: 숫자 칸 수(전 3칸 — 밴드 쿼드 GT 기준)·정렬·이탤릭, 단위
  표기 변형('mg/dL'/'mg /dL')과 위치·간격·높이비, 메모리 표기 3종(M박스/M/mem),
  GLU 라벨, 화살표(곡선·삼각형, 갭 2~80px 흔들림 — '거의 닿는' 배치 포함),
  아이콘(배터리·혈액방울·삼각형·블루투스·메모리플래그), 도트매트릭스 보조줄
  (위·아래, 표기 8형식), 시간줄, DAY AVG 줄, 날짜·기록줄, 베젤 인쇄(프레임
  가장자리), 물리 버튼.
- **라벨 오염 방지(AC #3)**: 라벨은 언제나 값 자릿수뿐. 빌더가 전 표본에
  `label.isdigit()` assert 로 고정했다.
- **A/B 캐시(변인 1개)**: 기기 단절 캐시의 실사진 8개 배열을 바이트 그대로
  복사(md5 검증 8/8)하고 합성 23,000장만 프로파일 렌더로 교체(21,850 train +
  1,150 val = 5%, RandomState(42) 순열 — build_cache_v2 와 같은 절차, 시드 19000).
- **학습(예산 규약)**: `ctc_reader_v2.py fresh --data-root ../train_profiled` —
  기준선 팔과 같은 스크립트·같은 규칙. pre 단계는 조기중단(val_loss patience 8)으로
  27에폭에서 끝났고 pre_best 는 19에폭 가중치(최종 val_loss 0.680). ft 12에폭도
  기록로 그대로 돌렸다(산출물 미사용). 기준선 pre_best 의 실제 조기중단 에폭은
  과거 로그 덮어쓰기로 **미확인** — 규칙·데이터 장수·배치·시드는 동일이다.
- **렌더 눈검증(AC #5·#6)**: `_diag/synth_real_atlas/profile_render_check.png` ·
  `profile_dot_check.png` — 비전 판독 2회. 확인: 빈 앞칸 슬롯·이탤릭·단위
  왼쪽/오른쪽·AC 식전식후 마커·Instant 화살표가 숫자 밴드에 붙음·도트매트릭스
  점 격자(1차 판은 뭉개져 양자화 방식을 고쳐 재검)·베젤 인쇄('GREEN Doctor'·
  'Premium'·'ACURA PLUS')·물리 버튼. 단위 텍스트의 프레임 밖 절단('mg/d')는
  실사진 관찰(#28) 재현으로 의도된 것이다.

## AC #4 — 생성기 품질 지표 전후 비교 (기기 단절 홀드아웃 1,138장)

평가 프로토콜: eval_reader(TTA 8+기본·crc32·거절 0.778) + device_eval_report.
재현: `eval_generator_baseline.py --weights ../train_profiled/checkpoints_v2/pre_best.weights.h5 --name pre_profiled`

| 층 | pre_v1(개선 전) | pre_profiled(개선 후) |
|---|---|---|
| 완전일치 | 0 (0.00%) | **11 (0.97%)** |
| **위험(자릿수 보존 오독)** | 34 (2.99%) | **115 (10.11%) — 3.4배 악화** |
| 안전 실패 | 392 | 1012 |
| 무출력 | 712 | **0** |
| 거절(agree<0.778) | 699 (61.4%) | 915 (80.4%) |
| 거절 통과 후 완전일치 | 0 | 1 |
| 거절 통과 후 위험 | 1 | 2 |
| 새니티: 합성 검증셋 greedy 300장 | 279/300 (93%) | 266/300 (88.7%) |

**판정: 순수 개선이 아니다.** 완전일치가 0→11 로 처음 생겼고 무출력이 사라졌지만,
그 대가로 위험층이 34→115 로 3.4배 불었다 — 모델이 '빈칸을 내던지던' 것에서
'무조건 3자리를 찍는' 쪽으로 바뀌었다(프로파일 전종이 3칸 필드라는 편향이
후보 원인). 거절 게이트(0.778)는 두 팔 모두 사실상 전부를 걸러낸다(통과 후
일치 0 vs 1) — pre-only 모델은 실사진에서 아직 쓸 수 없다는 기준선 결론이
유지된다. 레이아웃·방해 글리프 계층만 메워서는 도메인 갭이 닫히지 않는다;
아틀라스 D1(세그먼트 형상)·D2(잔상)·D9(명암) 광학 계층(뒤따르는
「합성 LCD 광학 재현」카드와 DSEG 교체 카드)이 다음 시험 지점이다.

기기별: 개선 후 일치 11건은 CareSens N 5·오토-첵 4·CareSens Dual 1·ACURA
PLUS 1 — 3칸 우정렬 프로파일과 가장 닮은 기기들이다. 반대로 화살표·도트
프로파일의 원 주인(Instant 0/34, Gmate 0/89, 도루코S 0/3)은 여전히 0.

## 검증

```
$ python build_profiled_cache.py
saved ../train_profiled/data_cache_v2.npz
synth train=21850 val=1150 (seed 19000, 프로파일 10종 균등)
real arrays byte-identical: 8/8

$ python ctc_reader_v2.py fresh --data-root ../train_profiled   (conda run, GPU)
== synthetic pretrain == 조기중단 27에폭(best 19, val_loss 0.680) → ft 12에폭 → SAVED

$ python eval_generator_baseline.py --weights ../train_profiled/checkpoints_v2/pre_best.weights.h5 --name pre_profiled
hold-out total=1138 (skipped 0)
{"exact": 11, "risky": 115, "safe": 1012, "blank": 0, "rejected": 915}
(기준선 팔: {"exact": 0, "risky": 34, "safe": 392, "blank": 712, "rejected": 699})

새니티(합성 검증셋 greedy 300장): pre_profiled 266/300 — 모델·평가 정상,
수치는 도메인 갭 실측이다.
```

산출물(전부 공유 _diag 또는 워크트리 로컬): `eval_pre_profiled_by_device.json`
(_diag/device_split/) · `reader_preds_pre_profiled.json` · 렌더 검증 시트 2장
(_diag/synth_real_atlas/) · 학습 로그·CSV(../train_profiled/).

## 건드리지 않고 남긴 것

- `ctc_reader_v2.py`(하이퍼파라미터·NUM_CLASSES·blank 인덱스)·`eval_reader.py`·
  `device_eval_report.py` 무수정. 기기 단절 분할·시드 20260911·홀드아웃 구성
  불변(실사진 배열 md5 동일로 증명). device_labels.jsonl 읽기 전용.
- `synth_lcd.py` 무수정 — 기준선 팔 재현성 보존.
- ft 60에폭 재평가는 하지 않았다(카드가 요구하는 비교는 pre-only 지표다).

## 막힌 것

- 없음. 단 두 가지 관찰 한계를 명시한다: ① 식전·식후 마커(AC/PC)는 이 40장
  표본에서 관찰 0건이라 근거 id 없이 AC#5 요건으로만 렌더했다. ② 기준선 pre 의
  실제 조기중단 에폭과 최종 val_loss 는 과거 로그 덮어쓰기로 원본 확인 불가
  (미확인) — 규칙 동일성으로 예산을 맞췄다.
