# G30 — 세로형 밴드 크롭 A/B

- 브랜치: `glm/G30-band-crop`
- 커밋: `1c0bd70`(코드) + 이 보고서 커밋
- 상태: 완료 — **채택 여부는 이 문서가 정하지 않는다.** 수치를 냈고 거기서 멈춘다.

## 요약 — 세 줄

1. **지시서 스펙 팔(크롭 + 세로 지터 0.15)은 학습 자체가 붕괴했다** — 파인튜닝
   손실이 5.40 에서 동결, TTA 완전일치 **1.34%**. 차분 실험으로 원인이
   **0.15**임을 확정했다(같은 캐시에서 0.08 만 바꾸면 즉시 수렴).
2. **크롭만 남긴 팔(세로 지터 0.08 = 기준선 값, 나머지 레시피 동일)은
   완전일치 87.79% / 위험군 8.29%** — 기준선 97.06% / 0.98% 에 크게 못
   미친다(McNemar p = 1.7e-23). 고정 12에폭 예산에서는 아직 수렴 중이었다
   (마지막 에폭 손실 0.96, 하강 중).
3. 가로형 44장의 **입력 프레이밍은 기준선과 픽셀 완전일치**(기하·좌표계
   정상). 판독 정확도가 달라진 것(57.1%→23.8%)은 모델이 재학습된 탓이다.
   또한 사람 라벨 가로형(wide_ids.json) 47장 중 13장(+회전 1장)이 규칙
   (w/h>1.2)상 세로형으로 판정돼 **크롭됐다** — 아래 상세 참조.

## 무엇을 했나

- `build_cache_v2.py` — `band_crop_box` 가 세로형 크롭의 **유일한** 구현.
  원본 GM 박스(마진 전)에서 w/h ≤ 1.2 면 세로 `[0.00, 0.72]` 를 남기고,
  **그 새 박스에** BOX_MARGIN 을 적용한다(지시서 순서 ①→②). 가로형·
  `band_rotation.jsonl`(1564)·합성은 불변. `--bandcrop` 이
  `data_cache_v2_bandcrop.npz` 를 낸다. 분할 시드(123/42)·필터 불변.
- `eval_reader.py` — `framed_src_rect`/`frame_crop` 이 같은 `band_crop_box` 를
  마진 **전에** 적용(`--bandcrop`). 기본 경로는 종래와 바이트 동일.
  `--bandcrop` 의 기본 출력은 `reader_preds_bandcrop.json`.
- `ctc_reader_v2.py` — `--bandcrop` 이 캐시·체크포인트·CSV·모델·판독 json 을
  전부 `*_bandcrop` 로 갈아 끼우고 `RandomTranslation` 세로 성분만 0.15 로.
  플래그 없으면 종래 동작(0.08) 그대로.
- 신규: `g30_check_cache.py`(캐시 검증), `g30_ab_report.py`(A/B 표),
  `g30_ft_nojit.py`(크롭만 팔 학습 드라이버).
- 산물: `data_cache_v2_bandcrop.npz` · `reader_model_bandcrop`(스펙 팔) ·
  `reader_preds_bandcrop.json` · `reader_model_bandcrop_ty008`(크롭만 팔) ·
  `reader_preds_bandcrop_ty008.json`. **기존 `reader_model/`·
  `data_cache_v2.npz`·`reader_preds.json` 은 한 번도 쓰지 않았다.**

## 결과 — 숫자만

### 기준선 재확립 (crc32 시드, 현 `reader_model`)

시작 전 사용자 지시로 main 을 43789ad(TTA 시드 crc32)로 맞추고 재측정했다.
2회 실행 항목별 0차이 — `reader_preds.json` 기존값과 동일.

| | 값 |
|---|---|
| 완전일치 | **1089/1122 = 97.06%** |
| 위험군(자릿수 보존 오독) | **11 (0.98%)** |
| blank / 안전 실패 | 3 (0.27%) / 19 (1.69%) |

### 스펙 팔(크롭 + 세로 지터 0.15) — 학습 붕괴

사전학습은 정상(27에폭 조기중단, val_loss 0.40). **파인튜닝이 5.40 에서
동결**했다(12에폭: 6.90 → 5.52(3ep) → 5.40(12ep)). 모델이 모든 장에 같은
값을 내는 모드 collapse. TTA 평가:

| | 기준선(A) | 스펙 팔(B) |
|---|---|---|
| 완전일치 | 1089 (97.06%) | **15 (1.34%)** |
| 위험군 | 11 (0.98%) | 882 (78.61%) |
| blank / 안전 실패 | 3 / 19 | 0 / 225 |
| McNemar(정확 이항) | — | b=2, c=1076, p=3.6e-319 |

**원인 격리(차분 실험).** 같은 `data_cache_v2_bandcrop.npz` 에서 세로 지터만
0.08 로 바꾼 파인튜닝: 5.94(2ep) → 4.91(4ep) → 2.83(6ep) 로 즉시 수렴,
6에폭 시점 홀드아웃 greedy 39.9%. **이미지(크롭)는 문제가 없고 0.15 가
붕괴시켰다.** 참고로 G29 letterbox 팔의 ft 는 4.30→0.64(12ep) — 정상.

기전 정량(숫자 띠 검출된 660장 기준, `_diag/G30/probe_digit_band.py`):
이동 한 방향이라도 숫자 획 절단이 가능한 비율이 **기준선+0.08 = 0.9%** 에서
**밴드크롭+0.15 = 9.5%** 로 뛴다(크롭 프레임의 숫자 아래 여유 p5 = 0.072
— 0.15 를 못 감당한다; 줌·회전이 겹치면 더 커진다). 검출 불가 1,834장은
포함 안 된 보수적 하한이다.

### 크롭만 남긴 팔(세로 지터 0.08, 나머지 기준선 레시피 동일)

`g30_ft_nojit.py` — 스펙 팔과 같은 사전학습 best(증강이 없는 단계라 동일
출발점)에서 12에폭. 마지막 에폭 손실 0.96, 아직 하강 중(레퍼런스: letterbox
12에폭 끝 0.64). TTA 평가:

| | 기준선(A·스트레치) | 크롭만 팔(B) |
|---|---|---|
| 완전일치 | 1089 (**97.06%**) | 985 (**87.79%**) |
| 위험군(자릿수 보존 오독) | 11 (**0.98%**) | 93 (**8.29%**) |
| blank(침묵) | 3 (0.27%) | 0 (0.00%) |
| 안전 실패(자릿수 붕괴) | 19 (1.69%) | 44 (3.92%) |

McNemar(정확 이항): 기준선만 틀림 **b=10**, 크롭만 팔만 틀림 **c=114**,
**p = 1.68e-23**.

오답 성격: 자릿수 보존 오독(위험군)이 93건으로 폭증 — `167→161`,
`144→140`, `124→24`(=자릿수 붕괴로 안전) 등 가운데/끝자리 혼동이 많다.
에폭 예산 내에서 수렴이 덜 끝난 징후와 일치한다.

### 층별 정확도 (형태 = 원본 GM 박스 w/h>1.2 규칙, 두 팔 공통 1,122장)

| 층 | 장수 | A 정확도 | 스펙 팔(0.15) | 크롭만 팔(0.08) |
|---|---|---|---|---|
| 가로형(크롭 안 함) | 21 | 12/21 (57.1%) | 2/21 (9.5%) | 5/21 (23.8%) |
| 세로형(크롭) | 1100 | 1077/1100 (97.9%) | 13/1100 (1.2%) | 980/1100 (89.1%) |
| 회전 제외(1564, 원본 박스) | 1 | 0/1 | 0/1 | 0/1 |

**"가로형은 기준선과 같아야 한다"에 대해.** 가로형 44장(전체 풀 기준,
holdout 21장 포함)의 캐시 이미지는 기준선 캐시와 **픽셀 완전일치 44/44**
(아래 검증) — 형태 판정·좌표계는 정상이다. 그런데 판독 정확도는
57.1%→23.8%(크롭만 팔)로 **같지 않다**. 이유: 이 팔은 재학습된 모델이라
입력이 같아도 가중치가 다르다(전체 학습의 98.2%가 크롭된 세로형 이미지라
가로형 풀프레임 입력이 모델에게 분포 밖이 됐다). 지시서의 전제는 입력
동일성으로는 성립하지만 판독 동일성으로는 재학습 팔에서 성립할 수 없다.
참고로 **기준선 모델 스스로도 가로형 21장에서 57.1%** 다 — 가로형은 이미
기준선에서 약한 층이며(검출 박스가 밴드를 담지 않는, 지시서가 이미 아는
별도 검출 문제) 이 층의 절대 성적은 낮다.

### wide_ids.json(사람 라벨 가로형) 과 규칙의 어긋남 — 보고 사항

`_diag/wide_all/wide_ids.json` 51장 중 풀 내 47장. 이 중 **13장(+회전 1장)이
규칙(w/h>1.2)상 세로형으로 판정돼 크롭됐다**:

```text
1565(회전, diag_wide_gm.py Case 9 에 1564 와 함께 문서화됨·band_rotation.jsonl 에는 1564 만 있음)
1622 1624 1627 1815 1822 1826 2198 2210 2221 2371 2391 2431   (w/h 0.56~1.10)
```

`diag_wide_gm.py` 의 분류에 따르면 이들은 회전 촬영(1564·1565) 또는 GM
검출기가 가로 화면을 "접은" 실패(w/h<1.2 = 접힘) 장들이다. 이 중 holdout
5장(1565·1622·1627·2210·2221)이 크롭됐다. 눈검 결과 4장(1565 `LO`·1622
`110`·1627·2210)은 크롭 후에도 숫자가 온전했고, 2221 은 기준선에서부터
마지막 자리가 잘려 있었다(크롭과 무관). 몽타주:
`_diag/G30/montage_wide_mismatch.png`.

### 새로 맞은 장(크롭만 팔, 10장)

```text
glucose_batch1/1099 1718 1951 247 488 61 694 845 · glucose_batch2/2501 2618
```

### 새로 틀린 장 — 크롭만 팔 전체 114장 (id gt→B [A 는 전부 정답])

```text
glucose_batch1/1026 124→24      glucose_batch1/1037 144→140
glucose_batch1/1055 177→171     glucose_batch1/1068 167→161
glucose_batch1/1073 167→161     glucose_batch1/1083 147→141
glucose_batch1/1094 97→172      glucose_batch1/1133 114→144
glucose_batch1/1178 79→78       glucose_batch1/1191 204→200
glucose_batch1/1193 154→152     glucose_batch1/1210 133→132
glucose_batch1/1218 144→143     glucose_batch1/1244 389→289
glucose_batch1/1245 275→75      glucose_batch1/1281 235→232
glucose_batch1/1286 326→226     glucose_batch1/1320 342→42
glucose_batch1/1324 439→139     glucose_batch1/1366 302→02
glucose_batch1/1368 315→15      glucose_batch1/1395 124→24
glucose_batch1/140 83→3         glucose_batch1/1406 119→115
glucose_batch1/1509 124→24      glucose_batch1/1526 108→100
glucose_batch1/1545 117→17      glucose_batch1/1562 108→188
glucose_batch1/1563 239→39      glucose_batch1/1588 103→172
glucose_batch1/1602 168→160     glucose_batch1/1611 89→197
glucose_batch1/1613 95→54       glucose_batch1/1622 110→107
glucose_batch1/1635 247→2277     glucose_batch1/1641 99→2
glucose_batch1/1643 114→17      glucose_batch1/1659 173→172
glucose_batch1/1684 108→106     glucose_batch1/1694 179→175
glucose_batch1/1716 336→32      glucose_batch1/1781 104→100
glucose_batch1/1922 148→146     glucose_batch1/1923 110→170
glucose_batch1/1934 125→122     glucose_batch1/2003 104→107
glucose_batch1/2039 141→153     glucose_batch1/211 200→208
glucose_batch1/2210 124→121     glucose_batch1/223 237→37
glucose_batch1/2261 409→09      glucose_batch1/2324 350→50
glucose_batch1/2382 184→187     glucose_batch1/2400 118→116
glucose_batch1/2402 139→135     glucose_batch1/2409 219→119
glucose_batch1/2428 135→35      glucose_batch1/244 223→23
glucose_batch1/249 361→61       glucose_batch1/267 125→122
glucose_batch1/303 145→175      glucose_batch1/32 229→299
glucose_batch1/341 226→26       glucose_batch1/35 211→217
glucose_batch1/36 172→272       glucose_batch1/366 140→170
glucose_batch1/40 113→272       glucose_batch1/407 111→117
glucose_batch1/408 148→146      glucose_batch1/409 118→116
glucose_batch1/421 106→186      glucose_batch1/45 58→229
glucose_batch1/459 237→37       glucose_batch1/499 158→101
glucose_batch1/501 107→111      glucose_batch1/530 80→180
glucose_batch1/534 111→171      glucose_batch1/540 124→24
glucose_batch1/634 224→221      glucose_batch1/66 252→253
glucose_batch1/69 55→255        glucose_batch1/702 102→182
glucose_batch1/710 100→180      glucose_batch1/711 110→170
glucose_batch1/724 213→212      glucose_batch1/735 129→125
glucose_batch1/740 183→182      glucose_batch1/749 128→126
glucose_batch1/750 126→122      glucose_batch1/753 139→135
glucose_batch1/762 211→2211     glucose_batch1/768 134→137
glucose_batch1/783 219→19       glucose_batch1/805 141→140
glucose_batch1/819 114→117      glucose_batch1/83 164→167
glucose_batch1/867 213→13       glucose_batch1/871 222→22
glucose_batch1/892 95→96        glucose_batch1/90 201→01
glucose_batch1/921 103→102      glucose_batch1/94 157→151
glucose_batch1/941 144→140      glucose_batch1/946 112→12
glucose_batch1/947 85→82        glucose_batch1/95 172→112
glucose_batch1/956 120→201      glucose_batch1/960 204→207
glucose_batch1/969 207→07       glucose_batch1/971 282→82
glucose_batch2/2518 444→40      glucose_batch2/2619 143→122
glucose_batch2/2626 116→176     glucose_batch2/2630 389→289
```

(득표율 agree 포함 전체 데이터: `_diag/G30/ab_report_ty008.json`의
`newly_wrong`. 스펙 팔의 새로 틀린 1,076장은 붕괴 모델의 전방위 오답이라
의미가 없어 본문에 넣지 않는다 — 같은 json 시리즈 `_diag/G30/ab_report_spec.json`.)

## 왜 그렇게 했나

- **스펙 팔(0.15)을 그대로 끝까지 돌리고 평가했다.** 지시서가 지정한
  설정이므로 붕괴를 확인한 뒤에도 TTA 평가까지 완주해 "스펙대로면 이렇게
  나온다"를 수치로 남겼다. 다만 그대로 멈추면 "크롭이 망쳤다"라는 거짓
  결론이 남는다 — 차분 실험(같은 캐시·세로 0.08)으로 원인이 지터 0.15
  단독임을 분리했고, 크롭 단독의 효과를 잰 팔(0.08)을 추가 학습해 함께
  보고한다. 어느 쪽 채택도 하지 않는다.
- **0.15 팔은 `--bandcrop` 플래그 뒤에만 건다.** 기본 경로(기준선 재현)는
  0.08 을 유지한다. 스크립트 기본값을 바꾸면 기준선 재현성이 조용히 깨진다.
- **크롭만 팔은 `ctc_reader_v2.py` 대신 `g30_ft_nojit.py` 드라이버로 냈다.**
  스펙이 아닌 설정을 본 스크립트에 노브로 추가하면 "하이퍼파라미터 하나도
  바꾸지 마라"의 우회로가 된다. 드라이버는 사전학습 best(증강 없는 단계라
  스펙 팔과 동일 출발점)에서 12에폭만 돈다 — 레시피는 기준선과 동일.
- `g30_ab_report.py` 의 McNemar 을 로그 공간으로 계산한다. 스펙 팔 비교에서
  n=1,102 로 `2**n` 이 float 범위를 넘어 오버플로가 났다. 작은 n 에서는
  G29 식과 동치다.
- 1564(회전 제외)는 holdout 에 포함돼 있고 두 팔 모두 원본 박스 프레이밍
  (픽셀 일치)으로 평가됐다. 이 장은 기준선에서도 오답(0/1)이라 층별 표에
  0/1 로 표시했다.

## 검증

기하 단위(`_diag/G30/probe_geometry.py`) — 합성 좌표로 크롭 규칙 확인:

```text
tall  : (100, 100, 200, 316.0)  기대 y1=316.0  → OK
wide  : (100, 100, 400, 200)  → OK (w/h=1.5 > 1.2)
rot   : (100, 100, 200, 400)  → OK (세로형 모양이지만 제외)
border: w/h=1.20 → y1=72.0  → OK(세로형, 크롭)
rotated_ids: ['glucose_batch1/1564']  (glucose_batch1/1564 만 있어야 한다)
RESULT: PASS
```

캐시(`python g30_check_cache.py`) — wide_ids 교차검증 항목만 FAIL(위 어긫남
보고 사항, 의도된 실패 아님 — 사실 관계), 나머지 전부 통과:

```text
[OK] real_train_ids: 1372 vs 1372, 순서일치=True, 집합일치=True
[OK] real_holdout_ids: 1122 vs 1122, 순서일치=True, 집합일치=True
[OK] 합성 항등: 500/500 픽셀 완전일치 (크롭 대상이 아니므로 항등이어야 한다)
[OK] 가로형 항등: 44장 전부 픽셀 일치 (불일치 0) — 크롭 안 한 경로 검증
[OK] 회전 제외 항등: 1장 전부 픽셀 일치 (불일치 0)
[OK] 세로형 크롭됨: 2449장 전부 픽셀 불일치 (우연히 일치 0)
  형태 집계(실사진 2494장): 세로형(크롭) 2449 · 가로형 44 · 회전 제외 1
[FAIL] wide_ids.json 교차검증: 풀 내 47장 중 규칙-가로형 아님 13 [...]
[OK] 학습/추론 bandcrop 프레이밍 등가: 11/11 픽셀 완전일치
RESULT: FAIL (위 1항목 — 본문 '어긋남' 절에서 설명)
```

- hold-out 분할은 기준선 캐시와 **순서까지 동일**(시드 123/42 불변) —
  두 팔이 같은 1,122장을 본다(키 집합 사전 검증 포함).
- TTA 시드는 G29 의 `zlib.crc32`(43789ad) 그대로. 기준선 재측정 2회 0차이.
- 육안: 세로형 4·가로형 2·회전 1 몽타주 `_diag/G30/montage_baseline_vs_bandcrop.png`
  — 세로형은 숫자가 커지고 아래 날짜·아이콘이 사라지며 윗획이 잘리지 않고,
  가로형·1564 는 좌우 동일. 어긋난 13장 몽타주 `montage_wide_mismatch.png`,
  라벨-이미지 정렬 6/6(`probe_label_alignment.png`), 증강 스택 0.08/0.15
  눈검(`probe_augment_visual.png` — 표본 2장은 여유가 커 온전해 보임).
- 라벨-이미지 정렬·기하는 위와 같이 별도 검증. 학습 재현: 스펙 팔
  `ctc_reader_v2.py --bandcrop`, 크롭만 팔 `g30_ft_nojit.py`(conda sugartrain).

flutter(파이썬만 건드렸으나 lib/ 우발 변경 게이트 — 커밋 전 재실행):

```text
flutter analyze  → No issues found! (ran in 6.7s)
flutter test     → All tests passed! (387 tests)
```

## 건드리지 않고 남긴 것

- `reader_model/`·`data_cache_v2.npz`·`checkpoints_v2/`·`training_log.csv`·
  `reader_preds.json` — 읽기만 함(재측정 결과가 기존 파일과 0차이라
  덮어쓰지도 않았다).
- `BOX_MARGIN`(0.10 사방)·모델 구조·에폭 수(40+12)·TTA_N=8·TTA_SEED=7·
  가로 지터 0.08·그 밖의 하이퍼파라미터 전부.
- `band_boxes.jsonl`·`band_rotation.jsonl`·`screen_boxes.jsonl`·
  `wide_band_queue.json`·`make_failure_atlas.py`·`webtool.py`·`lib/` — 0줄.
- 채택/기각 판정, `reader_model` 교체, 0.15 유지/변경, 에폭 증가 여부,
  13장 어긋남에 대한 형태 판정 기준 수정 — 전부 사람 몫.
- 밴드크롭 산물은 메인 트리에 남아 있다(gitignored): 필요 없어지면
  `data_cache_v2_bandcrop.npz`·`checkpoints_v2_bandcrop/`·
  `reader_model_bandcrop{,_ty008}`·`reader_preds_bandcrop{,_ty008}.json`·
  `training_log_bandcrop{,_ty008}.csv`·`_diag/G30/` 삭제로 끝난다.

## 막힌 것

- 0.15 붕괴의 정밀 기전(장당 획 절단 비율 전수 계산)은 못 냈다 — 프레임
  수준 구조(베젤·배경)가 숫자보다 커서 두 종의 검출기가 포화됐다.
  자릿수 크기 필터로 검출된 660장 부분집합의 수치(0.9% → 9.5%)만
  근거로 남긴다. 원인 지정은 차분 실험(0.08 vs 0.15, 같은 캐시)으로
  확정적이다.
- 그 외 없음.
