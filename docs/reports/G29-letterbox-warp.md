# G29 — TTA 시드 고정 + letterbox 워프 A/B

- 브랜치: `glm/G29-letterbox-warp`
- 커밋: `9ee32ff`(A — 시드 crc32) · `61efc37`(B — letterbox 구현) · 보고서 커밋(이 파일)
- 상태: 완료 — **채택 여부는 이 문서가 정하지 않는다.** 수치를 냈고 거기서 멈춘다.

작업 워크트리 `D:/Project/sugarScan-g29`. 데이터(npz·모델·원본)는 전부 메인 트리
`D:/Project/sugarScan/assets_dev/train` — gitignored 라 워크트리에 없고, 스크립트의
`--data-root` 로 접근했다.

## 무엇을 했나

- `eval_reader.py` — TTA 시드를 `hash(cid)` → `zlib.crc32(cid.encode("utf-8"))`
  으로 고정(이것만이 판독 동작 변경). 평가 대상 교체용 CLI
  (`--data-root`·`--model`·`--cache`·`--out`·`--letterbox`) 추가, 인자 없이 돌리면
  종래 동작 그대로.
- `build_cache_v2.py` — `letterbox_rect()` 추가: **유일한** letterbox 구현.
  `letterbox` 인자로 `data_cache_v2_letterbox.npz` 를 만든다(기본은 종래 stretch,
  `data_cache_v2.npz` 그대로). 분할 시드(123/42)·풀 필터·BOX_MARGIN 전부 불변.
- `ctc_reader_v2.py` — `--letterbox` 가 캐시·체크포인트·CSV 로그·모델·판독 json 을
  전부 `*_letterbox` 이름으로 갈아 끼운다. 구조·하이퍼파라미터·에폭 수 불변.
- 신규: `g29_check_cache.py`(캐시 검증), `g29_ab_report.py`(A/B 표).

## 결과 — 숫자만

### A. 새 기준선 (crc32 시드 · 현 `reader_model` · 2:1 스트레치)

| | 값 |
|---|---|
| 완전일치 | **1089/1122 = 97.06%** |
| 위험군(자릿수 보존 오독) | **11 (0.98%)** |
| blank / 안전 실패 | 3 (0.27%) / 19 (1.69%) |

- 재현성: 2회 실행, 1,122항목 전부 `pred`·`agree` 0차이.
- 옛 값 96.88% / 위험 1.07%(atlas 기준)은 불안정한 시드로 잰 값이라 **폐기** —
  이 표가 앞으로의 대조군이다.
- `reader_preds.json`(라벨러 모니터)은 이 기준선 판독으로 갱신됐다. 모델은
  여전히 `reader_model` 이므로 라벨러가 보는 내용의 정본이 바뀐 것은 아니다.

### B. letterbox (`reader_model_letterbox` · 동일 학습 설정)

두 팔은 **같은 1,122장**(키 집합 사전 검증)을 본다. 위험군 분류 기준은 webtool
`api_failures` 와 동일(빈 출력=blank · 자릿수 같은 오답=위험 · 다르면 안전).

| | 기준선(A·스트레치) | letterbox(B) |
|---|---|---|
| 완전일치 | 1089 (**97.06%**) | 1063 (**94.74%**) |
| 위험군(자릿수 보존 오독) | 11 (**0.98%**) | 39 (**3.48%**) |
| blank(침묵) | 3 (0.27%) | 1 (0.09%) |
| 안전 실패(자릿수 붕괴) | 19 (1.69%) | 19 (1.69%) |

### McNemar(정확 이항, 짝지은 비교)

- 기준선만 틀림 b=9 · letterbox 만 틀림 c=35 → **p = 0.0001**

### 늘림 배율 층별 정확도 (쿼드 축정렬 박스의 2h/w)

홀드아웃 배율 분포: median 2.56 · p10 2.08 · p90 2.91 · min 0.77 · max 3.60
(지시서의 "중앙 0.78 ≒ 배율 2.56, p10~p90 = 2.10~2.90" 전제와 일치).

| 층 | 장수 | A 정확도 | B 정확도 |
|---|---|---|---|
| <2.10 | 122 | 111/122 (91.0%) | 104/122 (85.2%) |
| 2.10~2.90 | 882 | 871/882 (98.8%) | 858/882 (97.3%) |
| >2.90 | 118 | 107/118 (90.7%) | 101/118 (85.6%) |

이 실험의 핵심 질문이었던 "오답이 몰려 있던 양쪽 극단층이 좋아지는가" —
**어느 층에서도 좋아지지 않았다**(전 층 하락). 사람이 다른 해석을 하려면
오답 목록이 필요할 것이다: `_diag/G29/ab_report.json`의 `wrong` 에 두 팔의
전체 오답 id 가 있다.

### 학습 참고 수치

- 사전학습 21에폭에서 조기중단(종래와 같은 ES patience 8, best 복원) + 파인튜닝 12에폭.
- greedy(TTA 없음) 홀드아웃: 1043/1122 = 93.0%. 학습셋 참고 559/600 = 93.2%
  (과적합 격차 없음). 기준선 모델의 greedy 는 94.83%(2026-09-04 재학습 기록) —
  TTA 를 곱하기 전부터 동일한 방향의 차이.

## 왜 그렇게 했나

- **letterbox 를 한 번의 `warpPerspective` 로 캔버스에 직접 놓는 초기 구현은
  버렸다.** `dst` 캔버스를 넘겨도 warpPerspective 는 캔버스를 통째로 다시 써서,
  dst 쿼드 바깥 픽셀도 역매핑되어 원본 이미지 내부에 닿는 순간 배경이 여백으로
  흘러든다(난수 이미지 단위점검에서 포착 — 평탄 이미지 테스트로는 안 잡힌다).
  두 단계(중간 크기로 워프 → 128 캔버스 중앙에 붙임)만이 여백을 128 로 보장한다.
- **합성(320×160 = 2:1 캔버스)은 재표본 없는 정확 복사 경로**를 뒀다(전체
  이미지·이미 캔버스 크기면 copy). 합성은 두 팔에서 픽셀 동일이 되고, 실험
  변수는 실사진 프레이밍만 남는다. 합성도 공유 함수를 통과시켰다 — 렌더러가
  캔버스 크기를 바꾸면 자동으로 같은 규약이 적용된다.
- `gt_corrections.jsonl` 을 `--data-root` 기준으로 읽게 했다. 워크트리 사본과
  메인 트리가 갈라지면 isdigit 필터 대상이 달라져 **분할이 어긋난다** — 이
  작업에서 가장 조용히 무너질 수 있는 자리였다.
- 산물 전부 새 이름(`data_cache_v2_letterbox.npz`·`reader_model_letterbox`·
  `checkpoints_v2_letterbox`·`training_log_letterbox.csv`·`reader_preds_letterbox.json`).
  기존 `reader_model/`·`data_cache_v2.npz`·`checkpoints_v2/`·`training_log.csv` 는
  한 번도 쓰지 않았다.

## 검증

단위 — 난수·평탄 이미지로 letterbox 동작 점검:

```text
2:1: 여백 없음(전체가 내용)=(160, 320) max diff = 0 diff>0 픽셀 = 0
tall: 좌우 여백 128 = True | 내용 보존 = True
wide: 위아래 여백 128 = True | 내용 보존 = True
aspect: src 0.300 → dst 0.300
RESULT: PASS
```

캐시 — `python g29_check_cache.py --data-root ...`:

```text
[OK] real_train_ids: 1372 vs 1372, 순서일치=True, 집합일치=True
[OK] real_holdout_ids: 1122 vs 1122, 순서일치=True, 집합일치=True
[OK] 합성 letterbox 항등: 500/500 픽셀 완전일치 (2:1 캔버스라 항등이어야 한다)
[OK] 학습/추론 letterbox 프레이밍 등가: 12/12 픽셀 완전일치
hold-out 늘림 배율(2h/w): median=2.56 p10=2.08 p90=2.91 min=0.77 max=3.60
층별 장수: <2.1 122 · 2.1~2.9 882 · >2.9 118
RESULT: PASS
```

육안 — stretch/letterbox 나란히 6장 몽타주(배율 0.77~3.60):
`_diag/G29/montage_stretch_vs_letterbox.png`. 낮은 배율은 패딩 없이 두 팔이
같고, 높은 배율은 좌우 균일한 중간회색 여백과 자연스러운 숫자 비율 확인.

기준선 재현성 — 실행 2회, 항목별 비교:

```text
keys equal: True 1122 1122
pred diffs: 0 agree-only diffs: 0
```

flutter(파이썬만 건드렸으나 lib/ 우발 변경 게이트):

```text
flutter analyze  → No issues found! (ran in 60.0s)
flutter test     → All tests passed! (387 tests)
```

## 건드리지 않고 남긴 것

- `reader_model/`·`data_cache_v2.npz`·`checkpoints_v2/`·`training_log.csv` — 읽기만 함.
- `webtool.py`·기존 `diag_*.py`·`lib/` — 0줄.
- `BOX_MARGIN`(0.10 사방)·모델 구조·하이퍼파라미터·에폭 수·TTA_N=8·TTA_SEED=7.
- 채택/기각 판정과 `reader_model` 교체 — 사람 몫.
- letterbox 산물 5종은 메인 트리에 남아 있다(모두 gitignored). 필요 없어지면
  `reader_model_letterbox/`·`data_cache_v2_letterbox.npz`·`checkpoints_v2_letterbox/`·
  `training_log_letterbox.csv`·`reader_preds_letterbox.json` 삭제로 끝난다.

## 막힌 것

없음.
