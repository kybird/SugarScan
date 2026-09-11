# 기기 편중 완화 A/B — 두 팔 다 개선 없음, 균등화 팔은 유의하게 악화 (기각)

2026-09-11 · 칸반 카드 「기기 편중을 줄이면 미학습 기기 성적이 오르는지 잰다」.
전제: [`device-holdout-eval-2026-09-11.md`](device-holdout-eval-2026-09-11.md) —
대조군 = 기기 단절 자연 분포 학습(1,356장), 미학습 기기 95.52% / 위험 2.46%.

## 판정 (AC4)

**기각.** 기기 편중을 줄여도(절단·균등화 어느 쪽이든) 미학습 기기 성적은
오르지 않았고, 총량을 유지한 균등화 팔은 완전일치·위험군 모두 유의하게
나빴다(McNemar p=0.0015). "있는 데이터를 고르게 쓰기"보다 "더 모으기"가
옳은 방향이라는 정보로 다음 결정을 바꾼다.

## 설계

세 팔 모두 같은 사전학습 체크포인트(`pre_best.weights.h5` 복사 — 로그
`pre_best 로드` 확인)·같은 60에폭·같은 평가 프로토콜(eval_reader TTA crc32).
홀드아웃은 기기 단절 1,138장을 세 팔이 동일 배열로 공유(짝비교 가능).
**바꾼 것은 real_train 의 기기 분포뿐** (`build_device_balance_split.py`,
기기명·id 정렬 + 고정 시드 20260911 — 결정적).

| 팔 | real_train | 기기 분포 |
|---|---|---|
| 대조 | 1,356장(고유) | 자연(최대 189, 상위 4종 36%) |
| B 절단(cap) | **603장**(고유) | 기기당 상한 28 = train 기기 중앙값(AC1 예시 규칙) |
| C 균등화(equalize) | **1,356행**(고유 783 + 복제 573) | 기기별 쿼터 45~46, 작은 기기 순환 복제(카드 Notes 의 총량 일치 팔) |

교란 명시(카드 Notes 요구): B 팔은 총 학습 장수가 1,356→603으로 줄었다
(효과가 '절단'인지 '감소'인지 분리 불가). C 팔이 그 분리를 담당한다 —
총 행수·스텝수(85/epoch)를 대조와 같게 두고 분포만 바꿨다.

## 결과 — 기기 단절 홀드아웃 1,138장 (세 팔 같은 시험지)

| 층 | 대조(자연) | B 절단 | C 균등화 |
|---|---|---|---|
| 완전일치 | **95.52%** (1,087) | 94.73% (1,078) | **92.97%** (1,058) |
| 위험(자릿수 보존) | **2.46%** (28) | 3.16% (36) | 3.69% (42) |
| 안전 실패 | 23 | 24 | 38 |
| 무출력 | 0 | 0 | 0 |
| 득표율 거절(agree<0.778) | 7.29% | 9.31% | 12.13% |
| McNemar(대조 대비) | — | 33/24, p=0.289 | 54/25, **p=0.0015(악화)** |

기기별 표는 `device_ab_report.py` 출력 전문(_diag 참조)을 요약하면:
- C 팔에서 악화: MaeilzeN -26.7pp(30장) · CareSens N Premier -10.3pp(29) ·
  ACURA PLUS -10.0pp(40) · Gmate -9.0pp(89) · SD CodeFree -6.7pp(60).
- C 팔에서 호전: 도루코S Premium 33→100%(3장) · ACURA VIEW 75→100%(4) ·
  Performa Nano +6.8pp(59) · Instant +5.9pp(34) — 절대 수가 작아 우연 폭이 크다.
- B 팔은 전 기기에서 대조와 ±수 pp 내(ACURA PLUS -15pp 가 최대 실질 낙폭).

### 보조 층 — 같은 기기의 '학습에 안 쓴 사진' (부산물, 짝비교 아님)

절단·균등화로 real_train 에서 빠진 사진(=학습한 기기의 미사용 사진)의 성적:
- B 팔 753장: 완전일치 95.88% / 위험 2.39% / 거절 7.70%
- C 팔 573장: 완전일치 94.42% / 위험 2.62% / 거절 7.33%

대조군에는 이 층이 없다(전부 학습에 썼으므로). 참고: B 팔의 '본 적 없는
같은 기기 사진' 95.88% ≈ 대조군의 '본 적 없는 기기' 95.52% — 사진 단위
일반화와 기기 단위 일반화의 격차는 이 조건에서 작다.

## 해석

- 균등화가 유의하게 나쁜 이유로 가장 설득력 있는 것은 **고유 사진 다양성의
  감소**다: C 팔은 1,356행이지만 고유는 783장 — 큰 기기에서 끌어낸 573장의
  다양성을 작은 기기 사진의 반복으로 채웠고, 반복은 새 정보가 아니다.
  거절률(7.3→12.1%)도 같이 오른 것은 모델이 확신을 잃었다는 방증.
- 절단(B)이 거의 중립인 것(-0.79pp, p=0.29)은 "큰 기기의 추가 사진이
  미학습 기기 전이에 주는 한계효용이 낮다"는 쪽으로도 읽히지만, 장수 감소
  교란과 섞여 있어 단정하지 않는다.
- 카드의 질문 "데이터를 더 모아야 하나, 있는 것을 고르게 쓰면 되나"에 대한
  이 측정의 답: **더 모아야 한다.** 재배분으로는 미학습 기기 성적을 살리지
  못한다. 다음 우선순위는 편중 재배분이 아니라 (a) Gmate·Instant 류
  미학습 기기 데이터 확보, 또는 (b) 합성 렌더러에 '숫자 옆 글리프(단위·
  화살표·아이콘)' 변인 반영(카드 2 보고서의 실패 서명)이다.

## 한계

- ft 1회씩(시드 1개) — 런 간 분산을 못 잰다. 다만 C 팔의 악화는 짝비교
  p=0.0015 로 방향이 뚜렷하고, B 팔은 '차이 없음'으로 읽는다(기각의 근거가
  아니라 채택 근거도 아님 — 중립).
- 상한 28(중앙값)은 카드 예시 규칙 그대로다. 더 완만한 상한(예: P90)은
  이 실험 범위 밖이며, B 팔 결과가 중립이었으므로 우선순위가 낮다.

## 재현

```bash
cd assets_dev/train
# 캐시(홀드아웃은 대조와 동일·복사)
C:/Users/admin/miniconda3/envs/sugartrain/python.exe build_device_balance_split.py --mode cap --out ../train_device_bal_cap/data_cache_v2.npz
C:/Users/admin/miniconda3/envs/sugartrain/python.exe build_device_balance_split.py --mode equalize --out ../train_device_bal_eq/data_cache_v2.npz
for d in train_device_bal_cap train_device_bal_eq; do
  cp gmscreen_quads.jsonl gt_corrections.jsonl band_rotation.jsonl ../$d/
  mkdir -p ../$d/checkpoints_v2
  cp checkpoints_v2/pre_best.weights.h5 ../$d/checkpoints_v2/
  C:/Users/admin/miniconda3/Scripts/conda.exe run -n sugartrain python ctc_reader_v2.py ft 60 --data-root ../$d
  C:/Users/admin/miniconda3/Scripts/conda.exe run -n sugartrain python eval_reader.py --data-root ../$d --out reader_preds_tta.json
done
# 짝비교(팔 preds 는 대조 홀드아웃 1138장으로 자동 제한)
C:/Users/admin/miniconda3/envs/sugartrain/python.exe device_ab_report.py --control ../train_device/reader_preds_tta.json --arm ../train_device_bal_cap/reader_preds_tta.json --name "팔B cap"
C:/Users/admin/miniconda3/envs/sugartrain/python.exe device_ab_report.py --control ../train_device/reader_preds_tta.json --arm ../train_device_bal_eq/reader_preds_tta.json --name "팔C equalize"
```

산출물(gitignored): `train_device_bal_cap/`·`train_device_bal_eq/`(캐시·
checkpoints·reader_model·reader_preds_tta.json). 커밋되는 것:
`build_device_balance_split.py`·`device_ab_report.py`(자기비교 항등 검증
통과)·이 보고서.
