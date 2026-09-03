# G20 — EXIF 로더 통일 (학습·검출·벤치)

- 브랜치: `glm/G20-exif-loader`
- 커밋: 이 보고서와 함께 커밋
- 상태: 완료 (Dart 쪽은 "이미 통일돼 있었음"을 실측으로 확정 — 아래 §Dart)

## 무엇을 했나

- `assets_dev/train/build_cache_v2.py` — `Image.open` 뒤 `convert("RGB")` 앞에
  `ImageOps.exif_transpose(pil)` 를 넣었다. 캐시 파일명 규칙은 그대로 두고
  기존 `data_cache_v2.npz` 를 지워 다시 만들었다(train 1104 / holdout 903,
  같은 시드 분할 유지).
- `assets_dev/train/detect_datumo_gm.py` — `cv2.imread`(EXIF 적용) 1차 +
  `Image.open`(무시) 폴백의 혼재를 `_load_bgr()` 단일 로더(PIL +
  `exif_transpose`, 출력은 기존과 같은 BGR 순서)로 통일했다. 모델 입력·후처리
  경로는 한 줄도 안 바꿨다.
- `tools/ocr_bench/bin/golden_bench.dart` — **지시서의 수정(bakeOrientation +
  재인코딩)은 하지 않았고 근거 주석만 남겼다.** 이유는 아래 §Dart 를 보라.
- `lib/` 는 한 줄도 안 고쳤다.

## 왜 그렇게 했나 — 좌표계 실히를 먼저 잼

지시서는 "gmscreen_quads.jsonl 을 raw 로 가정"하는 뉘앙스였지만(구 안티패턴
문서의 미완 주석이 그렇게 적혀 있다), **실측은 반대다.**

1. `cv2.imread` 는 이 환경(OpenCV 4.11.0, sugartrain)에서 EXIF orientation 을
   **적용한다**(ori=6 원본 4032×3024 → 3024×4032 세로).
2. `detect_datumo_gm.py` 의 1차 경로가 바로 그 cv2.imread 다 → 현행
   `gmscreen_quads.jsonl` 은 **표시(EXIF 적용) 좌표계**다.
3. 픽셀로 확정: 같은 쿼드를 raw / 표시 이미지에 각각 워프해 보니
   **표시 이미지에서만** 106·152·95·92 mg/dL 로 바로 선 화면이 나온다
   (`_diag/g20_warp/`, 몽타주).
4. 경계 검사(quad 가 raw 치수 안에 들어가는가)로는 판별이 안 됐다 — 둘 다
   "맞음"이 나왔다. `bounds-check-as-correctness-proof` 안티패턴의 재현.
   그래서 워프+육안으로 판정했다.

따라서 Python 쪽 진짜 결함은 "쿼드가 표시 좌표계인데 **build_cache_v2 만**
PIL raw 이미지에 물리고 있던 것"이고, 두 수정 모두 표시 좌표계로의 통일이라는
지시 목적과 정확히 일치한다. `detect_datumo_gm.py` 의 수정은 좌표계 의미
변화가 없다(1차 경로가 이미 표시 좌표계였으므로) — 폴백 경로만 바로잡혔다.

## Dart — 지시서 전제가 이 버전에서는 거짓이었다

지시서는 "`package:image` 의 decodeImage 는 방향을 굽지 않는다"고 전제하고
`decodeImage → bakeOrientation → encodePng` 스니펫을 지시했다. **실측 결과:**

- `img.decodeImage` (image 4.9.2) 의 JPEG 경로 `getImageFromJpeg`
  (`lib/src/formats/jpeg/_jpeg_quantize_io.dart:213`)은 **디코드 시점에
  orientation 을 픽셀에 구우고 태그를 지운다**(ori=6 → `setPixelRgb(h1-y, x, …)`,
  치수 스왑, `exif.imageIfd.orientation = null`).
- 실측: ori=6 원본 4032×3024(PIL raw) 가 `decodeImage` 로 3024×4032(세로)로
  디코드된다. 표본 15장 중 디코드 가능한 9장 전부 PIL `exif_transpose` 치수와
  일치(ori=1·6 혼합, 8/8 대조 + 1장 개별, 불일치 0).
- 따라서 **디코드 뒤 `bakeOrientation` 은 항상 no-op** 이다(태그가 이미
  지워져 있어 판단 불가). 스니펫을 그대로 넣으면 장당 ~1.7초의 PNG 재인코딩
  비용만 물고 픽셀은 하나도 안 바뀐다.
- 실험으로도 확인: 스니펫을 넣은 채 20장 벤치를 돌린 SUMMARY 와 원본 코드의
  SUMMARY 가 **전 항목 완전히 동일**했다(아래 검증 3).

그래서 golden_bench.dart 는 원복하고, 다음 사람이 같은 함정에 빠지지 않게
파일 머리에 근거 주석만 남겼다. **Dart 벤치 수치는 원래부터 표시 좌표계에서
나온 것이었다** — 과거 기준선(bench_v2.log 등)이 좌표계 오염이었던 게 아니다.

부수 확인: `lib/features/scan/photo_preprocessor.dart` 도 같은
`img.decodeImage` 를 쓰므로 앱의 사진 경로 역시 이미 표시 좌표계다. 지시서
"남길 것"의 우려("image_picker 가 방향을 정규화하지 않아 누운 채로 들어올 수
있다")는 현재 의존성(image 4.9.2)에서는 **재현되지 않는다** — EXIF 태그가
바이트에 살아 있는 한 디코드가 방향을 굽는다. 재현 방법 자체가 존재하지 않는
것으로 봐야 한다(태그가 벗겨진 바이트가 들어오는 경우만 취약한데, 그건
EXIF 미적용이 아니라 메타데이터 소거 케이스다).

## 검증

### 1. 캐시 재생성 + 표본 10장 눈검증

`build_cache_v2.py` 재실행 로그(전문):

```
합성: 23000/23000
실사진 풀: 2007 → train 1104 / holdout 903
실사진 rect: train 1104 / holdout 903
캐시: D:\Project\sugarScan\assets_dev\train\data_cache_v2.npz
  train synth: 21850 | val synth: 1150 | real train: 1104 | real holdout: 903
```

재생성 캐시에서 train/holdout 고르게 10장을 PNG 로 떨어뜨려 눈으로 봤다
(`_diag/g20_cache/`):

| 표본 | id | 판정 |
|---|---|---|
| t0 | glucose_batch1/1550 | 판독불가(어두운 얼룩) — 재생성 전에도 같은 자리가 불량 |
| t275 | glucose_batch1/1619 | **정립 "177"** |
| t551 | glucose_batch1/728 | **정립 "11"** — 수정 전에는 회전돼 있었음(효과 실증) |
| t827 | glucose_batch1/824 | 파편(쓰레기 rect) |
| t1103 | glucose_batch1/547 | **정립 "134"** — ori=1, 수정 전후 불변(대조군) |
| h0 | glucose_batch2/2552 | **정립 "138"** |
| h225 | glucose_batch1/407 | 화면 가장자리 파편(쿼드가 버튼 영역을 잡음) |
| h451 | glucose_batch1/568 | **정립 "138"** |
| h676 | glucose_batch1/1997 | **정립 "98"** |
| h902 | glucose_batch1/2463 | **정립 "139"** |

**옆으로 누운 것 0건.** 정립 7 / 불량 rect 3 — 불량 3건은 회전이 아니라
쿼드가 엉뚱한 곳을 잡은 기존 쓰레기-rect 집단(~8-13%, 이미 알려진 문제)이라
EXIF 수정과 무관하다. 수정 전 캐시 표본 6장 중 4장이 회전·깨짐이었던 것과
대비된다(ori=1 2장만 정립 — 83.5% ori=6 통계와 정확히 부합).

### 2. detect_datumo_gm 재실행 + 쿼드 오버레이

환경은 막히지 않았다(torch 2.5.1+cu121, CUDA 사용 가능, YOLOX 체크아웃
`D:/tmp/YOLOX` 존재). 실행 로그:

```
... 2400 (det 1928)
done: 2007/2512
```

재생성된 `gmscreen_quads.jsonl` 의 쿼드를 표시 이미지 위에 그려 9장 확인
(`_diag/g20_overlay/`): **7/9 가 유리에 부착**(106·152·95·92·110·84 등
라벨 GT 와 일치하는 판독이 보임). 어긋난 2건(1019·1022)은 모두 **ori=1** 의
Accu-Chek Performa Nano — 좌표계가 아니라 모델이 특이 화면에 약한 기존
품질 문제고, 검출 총량 2,007/2,512(79.9%)도 구 파일과 같다.

### 3. golden_bench — 전/후 나란히

Dart 는 위 §Dart 의 이유로 **코드 변경이 없다(전=후)**. 근거 실험:

- 스니펫(bake+재인코딩) 탑재 상태 20장 vs 원본 코드 20장 — SUMMARY 전 항목
  동일:

```
전(원본 코드)   SUMMARY n=20 exact=0 numEq=0 misread=3 digitChanged=0 hiLoReads=3 rejected=9 prep=ok:12/fallback:0 detectFail=3 warpFail=5 ... align=from-json
후(스니펫 탑재) SUMMARY n=20 exact=0 numEq=0 misread=3 digitChanged=0 hiLoReads=3 rejected=9 prep=ok:12/fallback:0 detectFail=3 warpFail=5 ... align=from-json
```

(스니펫 탑재판 개발 중 디코드 실패 파일 7장을 undecodable 로 세는 카운터
의미 변화가 있었으나, 원본과 같이 원본 바이트 폴백을 태워 최종 비교판에서는
카운터 의미까지 동일하게 맞췄다.)

기준선 수치(신규 쿼드, 원본 코드 — **전량 2,512장**, 전문은
[`G20-goldenset-fromjson-baseline.md`](G20-goldenset-fromjson-baseline.md)):

| 지표 | 값 |
|---|---|
| 전처리 정렬 성공 | 1484 (59.08%) |
| 완전일치 | 0 (0.00%) |
| **치명적 오독** | **346 (13.77%)** — 이중 숫자를 `HI`/`LO` 로 읽음 318 · 자릿수 변화 26 |
| 미인식 | 1138 (45.30%) — `unknownGlyph` 1041 이 주성분 |
| 쿼드 없음(detectFail) | 505 (= 2,512 − 2,007 검출) |
| 워프 실패 | 523 |
| 엔진 예외 | 0 |
| 전량 소요 | 1760.1s |

```
SUMMARY n=2512 exact=0 numEq=0 misread=346 digitChanged=26 hiLoReads=318
rejected=1138 prep=ok:1484/fallback:0 detectFail=505 warpFail=523 modelFail=0
relayout=ok:0/fail:0 missing=0 undecodable=0 engineError=0 align=from-json
```

완전일치 0 은 좌표가 아니라 규칙 엔진 품질의 문제다(과거 기록 `bench_v2.log`
n=300 exact=0 과 같은 수준). 전/후로 수치가 달라지지 않는 이유는 §Dart —
Dart 파이프라인 전체가 원래 표시 좌표계에서 돌고 있었기 때문이다.

`legacy`(앱 내장 전처리기) 300 표본도 돌렸으나 80분 무진행(사실상 정지,
원인 미상)으로 중단했다. from-json 전량으로 갈음한다.

### 4. flutter analyze · flutter test

```
flutter analyze  → No issues found! (ran in 6.0s)
flutter test     → 00:11 +384: All tests passed!
```

(중간에 임시 디버그 스크립트의 print 경고 3건이 있었으나 커밋 전에 파일을
지웠고 재실행에서 무경고.)

## 건드리지 않고 남긴 것

1. **라벨러 GM 힌트가 이중 회전돼 있다(중요).**
   `convert_quads_oriented.py` 는 `gmscreen_quads.jsonl` 을 **raw 좌표계로
   가정**하고 ori=6 좌표를 회전 변환해 `gmscreen_quads_oriented.jsonl` 을
   만드는데, 원본이 이미 표시 좌표계이므로 **ori=6 이미지(전체의 83.5%)의
   힌트가 두 번 회전돼 어긋난 자리에 놓인다.** 실측: 표시 이미지에 원본
   쿼드(초록)는 유리를 정확히 감싸고 변환본(빨강)은 어긋남(표본 10·1000,
   `_diag/g20_hint/`). `webtool.py` 의 `GM_QUADS` 가 이 파일을 보고 있다(40행).
   밴드 힌트(`datumo_quads_v2.jsonl`)는 변환 없이 직접 쓰여 정상이다.
   **고치는 방법은 자명하지만(힌트를 원본 쿼드로 갈아끼우거나 변환기를
   no-op 만들기) webtool 은 지시 범위 밖이라 손대지 않았다. 재라벨링 진행
   중이므로 사람이 결정할 것.**
2. `lib/features/scan/photo_preprocessor.dart` — 위 §Dart 참조. 변경 0줄.
3. `data_cache_v2.npz` 재생성으로 바뀐 CTC 학습 입력의 효과(정확도 상승
   여부)는 이 작업의 범위 밖이다. 다음 학습 실행이 기대치를 정할 것이다.
4. 쓰레기 rect 3건(1550·824·407)과 Accu-Chek 2건(1019·1022)의 검출 품질 —
   기존 알려진 문제, 좌표계 수정과 무관함을 확인만 했다.

## 막힌 것

- 없음. detect_datumo_gm.py 실행 환경(torch·YOLOX·GPU)이 모두 갖춰져 있어
  "막힘" 보고 없이 실행·검증했다.
