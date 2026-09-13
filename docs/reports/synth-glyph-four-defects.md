# 합성 글리프 네 결함 — 콜론·글자 크기 종수·배터리·화살표 위치

- 브랜치: `glm/synth-glyph-fix`
- 커밋: `<이 보고서와 함께 커밋>`
- 상태: 완료(AC#6 사람 blind 재판정 대기)
- 카드: 「합성 글리프 네 결함 — 콜론·글자 크기 종수·배터리·화살표 위치」(ordinal 48000)

## 무엇을 했나

- `synth_lcd.py` — 세그먼트 스트로크 폰트 `SEG_STROKES`/`seg_text`/`seg_text_width`
  추가. 숫자는 기존 7-세그(`SEG_MAP`), 글자는 직선 스트로크, 콜론은 사각 점
  두 개. 스트로크 표는 실사진 722 글자 모양을 보고 자체 정의(외부 폰트 아님).
- `synth_profiles.py`
  - 배터리 아이콘: 얇은 외곽선 + 오른쪽 돌기 + 가는 세로 막대 2개(부분 채움).
  - `dorucos_premium` 에 `dot_panel=True`(도트 패널 유일 기기, 근거 120·694·695).
  - `accuchek_instant` 에 `meter=True`, 화살표 kinds 를 `tri-right` 단일로.
- `synth_panel.py`
  - `_draw_text`(Hershey)·`_text_size` 삭제, `_lcd_text`(세그먼트+화이트리스트
    assert)로 교체. 시간·날짜·단위·mem·GLU·avgrow·가로형 칼럼/하단행·채움
    필러 전부 세그먼트. 도트 양자화는 `dot_panel` 기기만.
  - 보조 글자 높이를 패널당 하나(`aux_h = dh*U(0.15,0.19)`)로 통일. 렌더가
    그은 글자 높이를 `text_heights` 로 반환.
  - Instant: 몸체 오른쪽 여백에 미터기 점 눈금 10개 인쇄, LCD 안 오른쪽
    화살표의 세로 위치를 값에 대응(`y = clamp((value-95)/70, 0, 1)`, 1=위).
- `validate_synth_panel.py` — 하드 검사에 `sizes`(글자 높이 종수 ≤2) 추가.

## 왜 그렇게 했나

- **(가) 도트 유지 기기의 근거**: gc_ms_one(228·800)·caresens(1903·1911)의
  하단 시간·날짜줄을 원본 해상도로 확인했다 — 전부 세그먼트+사각점 콜론이었다.
  도트풍 얇은 글자는 도루코(120·694)에서만 봤다. 그래서 dot_panel 플래그로
  도루코만 도트를 유지하고 나머지는 전부 세그먼트로 바꿨다.
- **(마) 값→화살표 높이 대응의 근거**: 카드 Note 은 "확인 4장(값 132~154)으로는
  못 정한다"고 했다. `labels.jsonl` 전수 조사로 Instant 34장 전부에 값 라벨이
  있음을 확인했고 값 폭이 100~511 로 넓었다. 34장의 오른쪽 영역을 값 순으로
  나열한 눈검 시트(inst_all_0..2.png, 임시)에서 화살표 위치는 단조 상승 후
  상단 포화다: v100 하단 · v119 하중단 · v123~126 중앙 · v131~135 중상단 ·
  v141~150 상단 상승 · v159+(178·201·206·261·444·511 포함) 전부 상단.
  `y=clamp((v-95)/70, 0, 1)` 이 34장 전부와 어울린다(눈검 정밀도 ±0.1).
  근거가 부족하지 않아 handoff 하지 않았다. 기울기·바닥 앵커의 정밀값에는
  ±가 있음을 전제로 쓴다(보고 하단 "건드리지 않고 남긴 것").
- 미터기 눈금을 균일 회색 점 10개로 그렸다 — 사람 관찰("위로 갈수록 붉은
  구간")의 색 정보는 흑백 렌더에서 확인 불가라 반영하지 않았다(지어내지
  않는다). 점 열의 위치·모양·밝기 관통은 사진 근거 그대로.

## 검증

### AC#7 — 축 재검 (전축 동일 명령, n=300 seed 31000)

| 축 | after | 실측 정본(n) | 허용폭 | 판정 |
|---|---|---|---|---|
| 바깥 링 밀도 | 2.09% | 1.90% (263) | ±0.5pp | 통과 |
| 안쪽 밀도 | 1.43% | 1.11% (263) | ±0.4pp | 통과 |
| 전체(밴드 밖) 밀도 | 1.99% | 1.77% (264) | ±0.5pp | 통과 |
| 대비 median | 102 | 99 (264) | 99±15 | 통과 |
| 대비 p10 | 61 | 60 | 근접 | 통과 |
| 대비 40미만 | 1.0% | 1.1% (264) | 0<x≤3% | 통과 |
| 종횡비 median | 0.787 | 0.792 (2497) | Δ≤0.05 | 통과 |
| 세로 band_w | 0.847 | 0.888 (217) | Δ≤0.05 | 통과(Δ0.041) |
| 세로 band_h | 0.438 | 0.447 (217) | Δ≤0.05 | 통과 |
| 세로 cx / cy | 0.513 / 0.421 | 0.512 / 0.407 (217) | Δ≤0.05 | 통과 |
| 가로 band_w / h | 0.673 / 0.745 | 0.640 / 0.757 (47) | 가까워진다 | 통과(n=25) |

```
python synth_panel.py gen --count 300 --seed 31000 --out <임시>
python diag_density_where.py ring --images … --manifest …
  합성 n=299  바깥 링 median=0.0209  안쪽 median=0.0143
python measure_panel_stats.py synth-density … --frame-exc 0
  n=300 density median=0.0199 p10=0.0102 p90=0.0362
python measure_polarity.py synth-polarity …
  n=300 inverted=176 (58.7%)  대비 median=102 p10=61 (<40: 1.0%)
python measure_panel_stats.py synth-band --manifest …
  (위 표 값)
```

극성 58.7% 는 별도 REVIEW 카드(프로파일 세트 대표성)의 알려진 구조 문제다 —
AC#7 이 지킬 축으로 나열하지 않은 축이고 이 카드의 변경이 아니다.

### 하드 검사·자가검사

```
python validate_synth_panel.py --count 120 --seed 23000
-- 하드 검사: {'overlaps': 0, 'quad_out': 0, 'long_side': 0, 'label': 0,
               'clipped': 0, 'bezel_inside': 0, 'sizes': 0}
  하드 검사 전부 0
글리프 평면 gpc median=0.9997 p10=0.9912 (0.9 미만 1.7%)   # 1번 카드의 비례 문턱
```

`sizes: 0` — 120장 전부 글자 높이 2종 이하(대부분 {dh, aux_h} 정확히 2종).

### 몽타주 눈검

- 12장 몽타주(validate montage_plain.png): 보조 글자 전부 각진 세그먼트,
  콜론 사각 점 두 개, 배터리 얇은 테두리+돌기+가는 막대.
- 가로형 전용 8장 몽타주(칼럼형+하단행형): 세그먼트 적용 확인.
- Instant 8값 시트(v100·119·125·135·150·165·250·480): 화살표 하단→상단
  포화 단조, 미터기 점 열 몸체 우측 — 실측 시트(inst_all)와 대응.

### AC#6 — blind 시트 (사람 게이트, 판정 대기)

- **고치기 전**: `C:\Users\admin\AppData\Local\Temp\sugarscan-glyphfix\blind_before_card2.png`
- **고친 뒤**: `C:\Users\admin\AppData\Local\Temp\sugarscan-glyphfix\blind_after_card2.png`
  (같은 그림이 `assets_dev/train/_diag/synth_vs_real/blind_all.png` 에도 있다)

```
python synth_vs_real_sheet.py blind --n 8 --no-quad --images <dir>/images --manifest <dir>/manifest.jsonl
```

before 는 본 카드 변경 전 렌더(seed 31000 n=300), after 는 변경 후 같은 명령.
사람이 여전히 8/8 을 맞히면 남은 단서를 카드에 추가한다(AC#6).

flutter analyze → No issues found!
flutter test    → All tests passed! (471 tests)

## 건드리지 않고 남긴 것

- **Instant 값→높이 식의 정밀값**: `clamp((v-95)/70, 0, 1)` 은 34장 눈검과
  어울리는 가장 단순한 단조 포화 곡선이다. 기울기(1/70)와 바닥 앵커(95)의
  최적값은 눈검 정밀도(±0.1)보다 아래에서 못 가린다 — 더 정하려면 화살표
  픽셀 중심의 자동 측정이 필요한데 시도한 블롭 검출 두 벌(임시 스크립트)이
  LCD 창 검출·눈값과 어긋나 실패했다. 구간 경계 정밀화는 글리프 정밀화
  카드로 넘긴다.
- 베젤(몸체 인쇄) 글자는 Hershey 그대로 — 몸체 인쇄는 LCD 가 아니라 계층이
  다르다. AC#3 의 '2종' 계산에서도 제외했다(validate 의 sizes 검사는
  text_heights=LCD 글자만 센다).
- 화살표 배치 실패(dropped arrow)가 13→17/120 로 늘었다 — Instant 는 미터기
  때문에 후보 자리가 값이 정하는 한 곳뿐이라 유닛과 겹치면 뺀다. Placer 가
  지키는 정상 동작이고 하드 검사 아니다.
- 렌더의 프로세스 간 비결정성(카드1 보고서)은 이 카드와 무관하게 그대로다.

## 막힌 것

없음 — 값→화살표 대응은 34장 근거로 충분했고 handoff 는 필요하지 않았다.
