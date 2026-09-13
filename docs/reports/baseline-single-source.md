# 기준선 정본화 — 실사진 기준선을 한 곳에 고정하고 합성을 새 기준선으로 판정한다

- 카드: 「밴드 라벨 확장 뒤 합성 밀도·기하 기준선을 재고정한다」
- 브랜치: `glm/synth-overhaul` (커밋 해시는 카드 Result 에)
- 상태: 완료

## 무엇을 했나

- `assets_dev/train/make_real_baseline.py` **신규** — 정본 생성기. 축을 새로 재지
  않고 세 자(`measure_panel_stats`·`diag_density_where`·`measure_polarity`)를
  import 해 모은다. `--markdown` 으로 GLM_TASKS §3.8 표를 뽑는다.
- `assets_dev/train/real_baseline.json` **신규** — 실사진 기준선 정본. 라벨
  파일(band_boxes 277행·join 264·md5 `09ebd651…`, gmscreen_quads_oriented
  2,497행·md5 `08763562…`, 코퍼스 labels 2,512행), 생성 시각, 손잡이
  (density frame_exc=0, ring 0.15, 밴드 대비 p95-p5)가 파일 안에 적혀 있다.
- `measure_panel_stats.py` — `cmd_aspect`·`cmd_band`·`cmd_density` 의 계산을
  `collect_aspect`·`collect_band`·`collect_density` 로 분리. 인쇄문은 그대로.
- `measure_polarity.py` — `cmd_polarity` 계산을 `collect_polarity` 로 분리.
- `synth_panel.py` — `REAL_DENSITY` 의 84값 리터럴을 삭제하고 정본의
  `density.values`(n=264)를 읽는다. 머리말의 '실측 근거' 수치 나열(전부 n=84
  시절 값)을 삭제하고 정본 포인터로 교체했다.
- `validate_synth_panel.py` — `REAL` 리터럴을 삭제하고 정본에서 읽는다
  (표시용 반올림만 추가).
- `docs/GLM_TASKS.md` §3.8 — 명령 블록에 정본 생성기를 넣고, 표를
  `make_real_baseline.py --markdown` 출력으로 교체(대비 행에 p90 178 추가).
  표 위에 "정본은 real_baseline.json 하나" 를 명시.

## 왜 그렇게 했나

- **자를 import 로 재사용했다(§3.7).** 정본 생성기는 어떤 축도 스스로 계산하지
  않는다. `collect_*` 분리는 같은 코드를 두 호출자(CLI 인쇄·정본 생성)가 쓰게
  하려는 것이고, 분리 전후 출력이 바이트 단위로 같은 것을 diff 로 확인했다
  (aspect·band·density·polarity 4종 전부 IDENTICAL).
- **판정 기준(AC#3).** 밀도 세 축은 후속 카드의 AC 허용폭을 그대로 썼다
  — 링 1.90±0.5pp, 안쪽 1.11±0.4pp(양방향), 전체 1.77±0.5pp. 밴드 기하·
  종횡비는 |Δmedian| ≤ 0.05 를 통과선으로 삼았다(판정 표에 기준 명시).
  종횡비·자릿수는 분포 설계가 이미 실측 히스토그램을 쓰고 있어 참고로만.
- **몽타주 눈검(비전 도구 보조).** 쿼드 판과 plain 판을 봤다. 도트줄 회귀·
  글리프 파손·숫자줄 이탈은 없었다. 비전 도구가 4·6번 패널의 "붐빔/가장자리
  클립"을 지적했으나 프로그램 검사(요소 겹침 0·마진 이탈 0)와 상충해 몽타주
  해상도의 과민 판정으로 봤다. 도트줄 2줄로 보인 4번 패널은 도루코 프로파일의
  위·아래 쌍(`dotrow_above`+`dotrow_below`, 근거 120·694·695)이다.
- **쿼드-유리 '이탈 30장'은 좌표계 불일치다.** 워프 후 쿼드(manifest)를 워프 전
  마진(margins)과 비교하면 원근 변위만큼(≤5px) 삐져나 보인다. 정식 검사는
  워프 전 좌표계에서 하며 이 코드(2bc0495 패치 A)는 리뷰에서 0/600 이다.
  이 카드에서 바꾼 것은 밀도 목표뿐이라 기하 경로는 동일하다.
- **합성이 자기 목표를 초과 달성한다.** 렌더 후 밀도 median 0.0225 vs 재표본
  목표 median 0.0182(n=300) — `render_panel` 이 최대 3판 중 최고 밀도를
  고르는 선택 편향(리뷰 지적 3)이 그대로 작동한다. 고치는 일은 이 카드
  밖이다(별도 카드 「밀도 최대 선택이 여백 분포를 왜곡한다」 존재).

## 검증

실사진 재측정(커밋된 band_boxes.jsonl 277행 기준, 직접 python.exe 호출 —
conda run 래퍼가 셸 스냅샷과 충돌해 rc=127):

```
python measure_panel_stats.py aspect      → n=2497 median=0.792 p10=0.705 p90=0.975 portrait 91.7%
python measure_panel_stats.py band        → join=264/277 · portrait n=217 (0.888/0.447/0.512/0.407) · wide n=47 (0.640/0.757/0.500/0.506)
python measure_panel_stats.py density --frame-exc 0 → n=264 median=0.0177 p10=0.0046 p90=0.0384
python diag_density_where.py ring         → 실사진 n=263 바깥 링 0.0190 안쪽 0.0111
python diag_density_where.py denoise      → 실사진 n=264 질감 기여 22.4%(밀도0 1장 제외)
python measure_polarity.py                → n=264 inverted 33.7% · 대비 median 99 p10 60 min 21 (<40 1.1%)
python make_real_baseline.py              → real_baseline.json 생성 + 위 값 전수 일치
```

정본 생성 후 `validate_synth_panel.py --count 120 --seed 23000`:

```
-- 하드 검사: {'overlaps': 0, 'quad_out': 0, 'long_side': 0, 'label': 0, 'clipped': 0, 'bezel_inside': 0}
하드 검사 전부 0
gpc median=0.9997 p10=0.9924 (min 0.7845 — 리뷰 지적 5 의 잡음 민감성 범위)
```

합성 판정(n=300, seed 31000, 명령은 §3.8 그대로):

| 축 | 합성 | 실사진 정본(n) | 허용폭 | 판정 | 어디로 가나 |
|---|---|---|---|---|---|
| 바깥 링 밀도 | 2.76% | 1.90% (263) | ±0.5pp | **실패(+0.86)** | 카드「GM 크롭과 같은 물건으로」AC#3 |
| 안쪽 밀도 | 1.29% | 1.11% (263) | ±0.4pp 양방향 | 통과 | — |
| 전체(밴드 밖) | 2.45% | 1.77% (264) | ±0.5pp | **실패(+0.18)** | 같은 카드 AC#5 |
| 세로형 band_w | 0.821 | 0.888 (217) | Δ≤0.05 | **실패(−0.067)** | 같은 카드 AC#7 |
| 세로형 band_h | 0.446 | 0.447 (217) | Δ≤0.05 | 통과 | — |
| 세로형 cx | 0.512 | 0.512 (217) | Δ≤0.05 | 통과 | — |
| 세로형 cy | 0.397 | 0.407 (217) | Δ≤0.05 | 통과 | — |
| 종횡비 median | 0.789 | 0.792 (2497) | Δ≤0.05 | 통과 | — |
| 극성 반전 | 16.7% | 33.7% (264) | ±5pp | **실패(−17.0)** | 같은 카드 AC#8 |
| 대비 median | 132 | 99 (264) | 99±15 | **실패** | 카드「열화 상한」AC#2 |
| 대비 p10 | 92 | 60 (264) | 60 근접 | **실패** | 같은 카드 AC#3 |
| 대비 40미만 | 0.0% | 1.1% (264) | 0<x≤3% | **실패** | 같은 카드 AC#4 |
| 가로형 band_w | 0.832 | 0.640 (47) | Δ≤0.05 | **실패(+0.192)** | 카드「가로형 정보칼럼」AC#3 |
| 가로형 band_h | 0.693 | 0.757 (47) | Δ≤0.05 | **실패(−0.064)** | 같은 카드 AC#3 |
| 질감 기여 | 24.7% | 22.4% (263) | AC 없음 | 참고(Δ2.3pp) | — |

재현:

```
python synth_panel.py gen --count 300 --seed 31000 --out <dir>
python diag_density_where.py ring --images <dir>/images --manifest <dir>/manifest.jsonl
   → 합성 n=298 바깥 링 0.0276 안쪽 0.0129
python measure_panel_stats.py synth-density --images <dir>/images --manifest <dir>/manifest.jsonl --frame-exc 0
   → n=300 median=0.0245
python measure_panel_stats.py synth-band --manifest <dir>/manifest.jsonl
   → portrait n=268 (0.821/0.446/0.512/0.397) · wide n=32 (0.832/0.693)
python measure_polarity.py synth-polarity <dir>/images <dir>/manifest.jsonl
   → n=300 inverted 16.7% · 대비 median 132 p10 92 (<40 0.0%)
python synth_panel.py montage --out <png> --images <dir>/images --manifest <dir>/manifest.jsonl --n 12
```

앱 회귀(this branch는 assets_dev·docs 만 건드린다):

```
flutter analyze  → No issues found! (ran in 12.2s)
flutter test     → All tests passed! (471 tests)
```

## AC#4 — 허용폭 밖 축의 행선

실패 축 전부이미 전용 카드가 있다. 새 카드를 세우지 않았다(중복 카드 방지).

- 링·전체·세로 band_w·극성 → 「합성을 GM 크롭과 같은 물건으로 — 기기 몸체를
  함께 렌더한다」(AC#3·#5·#7·#8) — 이 체인의 2번 카드
- 대비 3축 → 「합성 열화 상한 — 사람이 못 읽는 표본을 만들지 않는다」 — 3번 카드
- 가로형 2축 → 「합성에 가로형 정보칼럼을 넣는다」 — 4번 카드

## 건드리지 않고 남긴 것

- `BAND_GEOM`·`PITCH_RATIO`·`GENERIC_INVERTED_P`(0.274)·`PANEL_ATTRS` — 여전히
  n=84 시절 값. 이 카드는 재는 카드다(AC#4). 2번 카드가 정본 값으로 갱신한다.
  머리말에 "아직 n=84 값" 임을 명시해 두었다.
- 밀도 최대 선택 루프(렌더 3판 중 최고) — 목표 초과 +0.43pp 의 상당분이 여기서
  온다. 별도 카드가 살아 있으므로 손대지 않았다.
- `ASPECT_BINS`(n=2497 히스토그램) — 밴드 라벨과 무관해 값이 그대로다. 정본에
  히스토그램을 `aspect.hist_0p1` 로 넣어 두긴 했다(소비처는 아직 없음).

## 막힌 것

없음.
