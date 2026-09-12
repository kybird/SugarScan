# DSEG 폰트 기반 글리프 렌더러 교체 — 2026-09-11

- 브랜치: `glm/atlas` (워크트리 `D:\Project\sugarScan-glm-atlas`)
- 상태: 완료
- 신규: `assets_dev/train/fonts/dseg/`(폰트 12종+라이선스 원문) · `synth_profiles.py`
  의 DSEG 경로(USE_DSEG 토글) · `eval_generator_baseline.py --cache` 옵션
- `synth_lcd.py`·`ctc_reader_v2.py` 무수정. 배치 계산·라벨 경로 불변(라벨=값 자릿수).

## 무엇을 했나

- **AC #1 라이선스**: DSEG v0.46 (keshikan, SIL OFL 1.1) 반입 — 원문
  `DSEG-LICENSE.txt` 동봉, `docs/LICENSES.md` §2 행에 버전·출처·반입 위치·RFN
  조항(수정·재배포 안 함, 렌더만) 갱신. 변형은 렌더 단계에서만(파일 무수정).
- **변형 선택(눈 검증)**: 실기기 8종 숫자 밴드(도루코S·Instant·Gmate·OneTouch·
  SD CodeFree·Green Doctor·CareTouch·N Premier)와 DSEG 후보 7종을 나란히 놓은
  시트(`_diag/synth_real_atlas/dseg_variant_check.png`) — **Classic 계열이
  주력**(모따기 끝단 근사), 굵기 Light/Regular/Bold 를 표본마다(한 화면 안에선
  일정), 이탤릭 기기엔 Italic 변형, 12% 확률로 Modern-Light(가는획 소수 기기).
- **AC #2·#3 렌더**: `draw_digit_dseg` — PIL 로 글리프를 이진 마스크로 렌더(획
  굵기는 폰트 변형이 담당). 이탤릭은 폰트 변형으로만(패널을 기울이는 전역 shear
  폐지 — 광학 카드 지적 선반영). **꺼진 세그먼트 잔상**: '8' 전체 획을 배경↔잉크
  블렌드로 먼저 깔고 진한 글리프를 얹는다. 2026-09-11 실사진 정정("잔상은
  생각보다 훨씬 약하다, 빈 앞칸엔 흔적 없다")대로 **15% 표본에만**, 농도
  0.08~0.20 흔들림, 빈 슬롯엔 잔상 없음.
- **AC #4 몽타주**: 같은 시드 12쌍(값·프로파일·배치 동일, 글리프만 다름) —
  `_diag/synth_real_atlas/dseg_before_after_12x2.png`. 비전 검증: DSEG 셀에
  폰트형 7세그 숫자·굵기 변형·onetouch 이탤릭(패널 무기울기)·일부 셀 희미한
  잔상(빈 슬롯엔 없음) 확인, 슬롯 밖 오버플로·단위·화살표와 충돌 0건.
- **보너스 — 생성기 품질 지표 A/B**(품질지표 카드의 재현 명령으로): DSEG 캐시
  23,000장(실사진 8배열 md5 동일 복사, 합성만 교체, 시드 19000) → 같은 규칙
  pre 학습(조기중단 30에폭, best 21, val_loss 0.616) → 동일 프로토콜 평가.
  홀드아웃 정의는 로컬 캐시 복사본 사용 — **공유 train_device 캐시를 사람
  세션이 21:52~ 재작성 중**이라 읽지 않았다(실사진 id 구성은 동일).

## 세 팔 비교 (기기 단절 홀드아웃 1,138장, pre-only)

| | pre_v1 (rect 무작위) | pre_profiled (프로파일+rect) | **pre_dseg (프로파일+DSEG)** |
|---|---|---|---|
| 완전일치 | 0 (0.00%) | 11 (0.97%) | **19 (1.67%)** |
| 위험(자릿수 보존 오독) | 34 (2.99%) | 115 (10.11%) | **138 (12.13%)** |
| 안전 실패 | 392 | 1012 | 870 |
| 무출력 | 712 | 0 | 111 |
| 거절(agree<0.778) | 699 (61.4%) | 915 (80.4%) | 979 (86.0%) |
| 거절 통과 후 완전일치 / 위험 | 0 / 1 | 1 / 2 | 1 / 1 |
| pre 예산(같은 규칙) | 에폭 미확인(로그 소실) | 28ep, best 19, val 0.680 | 30ep, best 21, **val 0.616** |
| 새니티: 합성 검증셋 greedy 300장 | 279/300 (93%) | 266/300 (88.7%) | 272/300 (90.7%) |

**판정**: 글리프를 폰트로 바꾸니 전이는 계속 좋아졌다(완전일치 0→11→19,
합성 val 손실도 개선 0.680→0.616). 그러나 **위험층은 여전히 악화 방향**(34→115→138)
— 이전 카드의 결론이 강화된다: 렌더가 실사진에 가까워질수록 모델은 더 확신 있게
숫자열을 찍고, 틀릴 때는 '그럴듯한 값'으로 틀린다. 거절 게이트가 위험의 대부분을
걸러내지만(통과 후 위험 1건) 통과 후 일치도 1건뿐 — pre-only 모델의 실사진
성적은 여전히 실용 수준이 아니다. 남은 지점은 광학 계층(픽셀 격자·편광·명암 —
주차된 광학 카드)과 무엇보다 **실사진 파인튜닝과의 결합**이다.

일치 19건 분포: 오토-첵 14/156 · CareSens N 4/240 · ACURA PLUS 1/40.

## 검증

```
$ python build_profiled_cache.py --out ../train_dseg/data_cache_v2.npz
saved ../train_dseg/data_cache_v2.npz
synth train=21850 val=1150 (seed 19000, 프로파일 10종 균등)
real arrays byte-identical: 8/8

$ python ctc_reader_v2.py fresh --data-root ../train_dseg   (conda run, GPU)
== synthetic pretrain ==  조기중단 30에폭(best 21, val_loss 0.616) → ft 12 → SAVED

$ python eval_generator_baseline.py --weights ../train_dseg/checkpoints_v2/pre_best.weights.h5 \
     --name pre_dseg --cache ../train_profiled/data_cache_v2.npz
{"exact": 19, "risky": 138, "safe": 870, "blank": 111, "rejected": 979}

새니티: dseg synth_val first300 exact greedy 272/300
```

변형 선택·전후 비교 시트: `_diag/synth_real_atlas/dseg_variant_check.png` ·
`dseg_before_after_12x2.png`(공유 접합 — 메인 워크트리에서도 보인다).
기기별 전수: `_diag/device_split/eval_pre_dseg_by_device.json`.

## 건드리지 않고 남긴 것

- 폰트 파일 무수정(RFN). 폰트를 코드로 변형하지 않음 — 굵기·이탤릭은 변형
  파일 선택으로만.
- 시간줄·평균줄의 보조 7세그는 기존 rect 렌더 유지(메인 숫자만 DSEG) —
  카드 범위가 '숫자 글리프'고, 소형 글리프까지 바꾸면 변인이 하나 더 섞인다.
- 공유 train_device 캐시·메인 워크트리 전부 무접촉.

## 막힌 것

- 없음. 단 pre_v1 팔의 실제 에폭 수는 여전히 미확인(과거 로그 덮어쓰기) —
  세 팔 모두 같은 조기중단 규칙이라는 것으로 예산 동일성을 주장한다.
