# 서드파티 라이선스 검토

> 최초 작성 2026-08-20 · 담당: 개발자 본인
> 라이선스 실사: 2026-08-21 (G5) — 아래 각 행의 확인 URL 은 당일 직접 연 기준.
> 검출기 가중치 계보 실사: 2026-09-17 (§1.1) — 로컬 사본과 어노테이션을 직접 세어 확인.
> 남은 미해결 항목은 §4 참조.

앱에 실제로 반입되는 자산(모델 가중치·폰트·학습 코드)의 상업적 사용 가능 여부와
고지 의무를 여기에 모은다. 정확도만 보고 모델을 골랐다가 출시 직전에 라이선스로
막히는 것이 이 프로젝트에서 가장 값비싼 실수가 된다.

---

## 1. OCR 모델 / 학습 코드

| 자산 | 출처 | 라이선스 | 앱에 반입되는가 | 상태 |
|---|---|---|---|---|
| ~~EasyOCR~~ | JaidedAI/EasyOCR | 코드: Apache-2.0 (2026-08-21 확인) | **아니오 — 채택하지 않음** | **2026-09-17 종결.** 벤치에서 기각됐고(크롭 9.3% · 원본 1.3% vs 자체 98.0%, `bench_external_ocr.py`), 남겨 둔 유일한 이유였던 mmol/L 소수점은 재구축 계획 §4 가 **우리 리더 charset 에 소수점을 처음부터 넣기로** 하면서 사라졌다. 가중치 조건을 확인할 이유가 없다 |
| CRAFT (text detector) | clovaai/CRAFT-pytorch | **MIT** (Copyright (c) 2019-present NAVER Corp., [LICENSE](https://github.com/clovaai/CRAFT-pytorch/blob/master/LICENSE), 2026-08-21 확인) — **연구용 한정 조항 없음.** LICENSE 원문과 README 어디에도 비상업 조항이 없는 순수 MIT 다 | **미반입** (가이드 박스로 대체) | 확인 완료 |
| deep-text-recognition-benchmark | clovaai | **Apache-2.0** ([LICENSE.md](https://github.com/clovaai/deep-text-recognition-benchmark/blob/master/LICENSE.md), 2026-08-21 확인 — 파일명이 `LICENSE.md` 다) | 아니오 (학습 도구) | 확인 완료 |
| ONNX Runtime | microsoft/onnxruntime | **MIT** (Copyright (c) Microsoft Corporation, [LICENSE](https://github.com/microsoft/onnxruntime/blob/master/LICENSE), 2026-08-21 확인) | 예 (flutter_onnxruntime 경유) | 확인 완료 |
| **7seg_classifier.tflite** | [Kazuhito00/7segment-display-reader](https://github.com/Kazuhito00/7segment-display-reader) | **Apache-2.0** (GitHub API 확인 완료) | **예** — `assets/models/` 에 번들 | 고지 의무 반영 필요 |
| TensorFlow Lite | tflite_flutter 경유 | **Apache-2.0** (TensorFlow 본저장소 [LICENSE](https://github.com/tensorflow/tensorflow/blob/master/LICENSE), 2026-08-21 확인. 원문 말미에 Caffe 유래 코드의 BSD 스타일 고지가 함께 실려 있다) | 예 | 확인 완료 |
| **YOLOX** (GM 화면 검출기의 구조·학습 코드) | [Megvii-BaseDetection/YOLOX](https://github.com/Megvii-BaseDetection/YOLOX) | **Apache-2.0** (GitHub API `spdx_id`, 2026-09-04 확인. 로컬 체크아웃 `D:\tmp\YOLOX\LICENSE` 원문도 Apache 2.0 으로 대조 완료) | 아직 아니오 — 검출기는 현재 학습·평가에서만 돈다. **앱에 넣으면 예** | 확인 완료. 반입 시 Apache-2.0 고지 필요 |
| **검출기 가중치 일체** (`yolox_out/**/best_ckpt.pth`) | 우리가 학습. 계보는 §1.1 참조 — 뿌리는 COCO 사전학습 `yolox_nano.pth` 이고 중간에 Roboflow(CC BY 4.0)와 Datumo(조건 미확인)가 들어온다 | 아직 아니오 | **체크포인트마다 의무가 다르다.** §1.1 표를 볼 것 |

### 1.1 검출기 가중치 계보 — 체크포인트마다 의무가 다르다

2026-09-17 실사. 구판은 `gmscreen_ft2` 한 줄만 적어 두었는데 **뿌리(COCO 사전학습)가
빠져 있었고**, 그 뒤 승격·파생이 반영되지 않았다. 실제 계보는 이렇다.

```
weights/yolox_nano.pth            COCO 사전학습 (Megvii 공식 배포본으로 보인다)
  │                               7,694,953 바이트 · md5 2f50e06ff9729cf41b81112d48c3c1c4
  │                               ※ 내려받은 출처 URL 이 저장소 기록에 없다
  ├─ gmscreen/best_ckpt.pth       + Roboflow glucometer_images-bc9dh 1,276장
  │    │                            (datumo 0장 — 확인함)
  │    └─ synthband_v0/best_ckpt.pth   + 우리 합성 900장   ← 마일스톤 검출기
  │
  └─ gmscreen_ft·ft2·ft3/best_ckpt.pth  + Roboflow 1,276장 **+ Datumo 410장**
                                    ft3 가 2026-09-12 운영 정본으로 승격
```

| 체크포인트 | 들어간 데이터 | 배포 시 따라오는 의무 |
|---|---|---|
| `gmscreen` (2026-08-28) | COCO 사전학습 + Roboflow CC BY 4.0 | YOLOX Apache-2.0 고지 · **Roboflow 저작자 표시** |
| `synthband_v0` (2026-09-16) | 위 + **우리 합성만** | 위와 같음. **Datumo 안 탄다** |
| `gmscreen_ft3` (운영 정본) | 위 + **Datumo 410장** | 위 + **Datumo 이용 조건 — 미확인(§4)** |

**이 표의 요점**: 운영 정본 `gmscreen_ft3` 는 이용 조건이 확정되지 않은 데이터
(Datumo)로 학습된 파생 가중치다. 마일스톤의 `synthband_v0` 는 그 경로를 타지
않는다 — 합성만 얹었기 때문이다. 배포 시점에 어느 체크포인트를 넣느냐로
의무가 갈린다.

**확인한 것과 못 한 것**

- [x] Roboflow 두 데이터셋의 라이선스 — 로컬 zip 안 `README.dataset.txt` 원문에
      `License: CC BY 4.0` 이 박혀 있다(`glucometer_images-bc9dh` ·
      `glucometer-amtkm` 둘 다). 웹 페이지가 아니라 **받아 둔 사본이 근거**다.
- [x] 어느 체크포인트에 Datumo 가 들어갔는가 — COCO 어노테이션의 `file_name`
      접두사로 셌다. `gmscreen` 0장 / `gmscreen_ft` 410장.
- [x] `glucometer-amtkm` 은 받아만 두고 **학습에 쓰지 않았다**(코드·문서 전체
      grep 결과 참조 없음). 지금은 의무가 없다.
- [ ] **`yolox_nano.pth` 의 가중치 라이선스** — YOLOX 저장소 LICENSE 는
      Apache-2.0 이지만 README 는 가중치를 표로 배포하면서 **가중치의 라이선스를
      따로 적지 않는다.** EasyOCR 과 똑같은 구멍이다(§4). 구판 문서는 EasyOCR
      에만 이 구멍을 적고 YOLOX 는 "코드가 Apache-2.0 이니 괜찮다"로 넘어갔다 —
      같은 근거로 EasyOCR 을 보류했으면서 YOLOX 는 통과시킨 것이라 일관되지 않다.
- [ ] `yolox_nano.pth` 를 **어디서 받았는지** 기록이 없다. 공식 릴리스 해시와
      대조해 출처를 고정해야 한다(md5 위에 적어 두었다).
- [ ] COCO 사전학습이 파생 가중치에 조건을 남기는지 — COCO 어노테이션은
      CC BY 4.0, 이미지는 Flickr 개별 조건이다. 가중치로의 전파는 법적으로
      정리되지 않은 영역이라 **판단이 필요한 항목**으로 남긴다.

**참고만 하고 코드를 쓰지 않은 것** (반입 자산 아님)

| 프로젝트 | 라이선스 | 처리 |
|---|---|---|
| [SSOCR](https://github.com/jiweibo/SSOCR) | GPL-3.0 | **코드 미사용.** GPL 전염성 때문에 상용 앱에 넣을 수 없어 알고리즘 아이디어만 참고하고 `SegmentRuleEngine` 을 자체 구현했다 |
| [SegoDec](https://github.com/scottmudge/SegoDec) | **Apache-2.0** ([LICENSE](https://github.com/scottmudge/SegoDec/blob/master/LICENSE), 2026-08-21 확인 — 저작자명이 기입되지 않은 템플릿 원문 그대로다) | 코드 미사용. CLAHE/대비 개선 접근만 참고 |
| [seven-segment-ocr](https://github.com/suyashkumar/seven-segment-ocr) | **LICENSE 파일 없음** (2026-08-21 확인 — 저장소 파일 목록에 라이선스 파일이 아예 없고 README 에도 규정이 없다. 라이선스 명시가 없으면 기본적으로 모든 권리가 저작자에게 남는다) | 코드 미사용이라 실무상 영향 없음. 코드를 쓰게 되면 저작자에게 별도 허락을 받아야 한다 |
| [OICWS/lcd-digit-recognition](https://github.com/OICWS/lcd-digit-recognition) | **AGPL-3.0** | **채택하지 않음.** YOLOv8 기반이며 AGPL 은 상용 배포에 부적합 |

> 자체 구현이라는 사실 자체가 라이선스 방어선이다. 나중에 성능이 아쉬워 참고
> 저장소의 코드를 조각이라도 붙여 넣으면 그 순간 라이선스가 따라 들어온다.

**확인 포인트**
- EasyOCR 사전학습 가중치는 코드와 라이선스가 다를 수 있다. 가중치 배포 조건을
  별도로 확인한다.
  - 2026-08-21 실사 결과: 저장소 LICENSE(Apache-2.0)·README·공식 사이트
    (jaided.ai/easyocr) 어디에도 **가중치의 배포 조건에 대한 문구가 없다.**
    "없다 = 코드와 같다"로 읽는 것은 추측이므로 반입 전 Jaided AI 에 문의하는
    것이 남은 절차다.
- CRAFT 는 현재 계획상 **앱에 넣지 않는다**(§2.5 Detector 생략). 학습 파이프라인
  에서만 쓴다면 반입 자산이 아니므로 조건이 완화된다.
  - 2026-08-21 실사 결과: LICENSE 원문·README 모두 순수 MIT 이며 연구용 한정
    조항은 없었다.
- fine-tune 결과물의 저작권 귀속: 원 가중치의 라이선스가 파생 가중치에도
  따라붙는지 확인한다. EasyOCR 가중치 조건이 확인되기 전까지는 이 항목도
  열려 있는 상태로 둔다.

---

## 1.4 실사진은 **검증에만** 쓴다 (2026-09-19 사람 결정)

**규칙**: 이용 조건이 미확인이거나 귀속 의무가 있는 실사진은
**학습에 넣지 않는다. 검증·측정에만 쓴다.** 이미지는 저장소에 커밋하지 않는다.

| 코퍼스 | 라이선스 | 학습 | 검증 |
|---|---|---|---|
| Datumo(TILDE) 272장 | **조건 미확인** | **금지** | 허용 |
| Datacluster 238장 | CC0 | 금지(이 규칙 아래 통일) | 허용 |
| Roboflow `glucometer_images-bc9dh` 1,273장 | CC BY 4.0 | **금지** | 허용 |

왜 검증은 되는가: 이미지가 가중치에 들어가지 않고 배포 산출물에도 들어가지
않는다. CC BY 4.0 의 귀속 의무와 조건 미확인 자료의 위험은 **배포물**에
걸리는데, 배포물에 아무것도 들어가지 않는다.

**점검 결과(2026-09-19)** — `git ls-files assets_dev/upstream` 0건, 전
체크포인트 `n_images=15996`(합성 `synth_coco/TB`만), 생성기의 `imread` 는
자기가 만든 PNG 를 되읽는 한 곳뿐, GPL/AGPL 문자열 0건.

**발견·처리한 위반 1건**: `docs/reports/profile-expansion-compare-2026-09-12.png`
(2026-09-12 커밋 `411c16f`)에 Datumo 실사진 크롭 6장이 들어 있었다. 파일을
지우고 **히스토리에서도 제거**한다(사람 결정). 같은 폴더의 다른 두 PNG 는
그래프뿐임을 열어서 확인했다.

**원격 주의**: 그 커밋은 `origin/main` 을 포함한 원격 브랜치 4곳에 푸시돼
있었다. 로컬 재작성만으로는 GitHub 에서 사라지지 않는다 — 강제 푸시가
필요하고, 그 뒤에도 GitHub 이 수거하기 전까지 커밋 해시로 접근될 수 있다.

## 1.5 학습·평가 데이터셋

2026-08-22 확보. 전부 `assets_dev/upstream/` 에 두며 **저장소에 커밋하지 않는다**
(`.gitignore` 의 `assets_dev/`). 앱에 반입되는 것은 여기서 파생된 모델뿐이고
이미지 자체는 나가지 않는다.

| 자산 | 내용 | 라이선스 | 확인 |
|---|---|---|---|
| [Kazuhito00/7segment-display-reader](https://github.com/Kazuhito00/7segment-display-reader) `01.dataset` | **실촬 41,990장** — 7세그 디스플레이 2종. 클래스 `00`~`09`(각 ≈4,000장) + `11`(표시 없음, 1,992장) | **Apache-2.0** (GitHub API `spdx_id`, 2026-08-22) | 확보 완료 (244MB) |
| [Kazuhito00/7segment-display-reader](https://github.com/Kazuhito00/7segment-display-reader) `02.model` | `7seg_classifier.tflite` (609,904 B) · `7seg_classifier(monochrome).tflite` (2,654,048 B) | **Apache-2.0** | 확보 완료 — `assets/models/README.md` 의 규격과 일치 |
| [Kazuhito00/7seg-image-generator](https://github.com/Kazuhito00/7seg-image-generator) | 합성 생성기(Python/OpenCV). 96×96 기본, shear −10~30°, shift ±10px | **Apache-2.0** (GitHub API `spdx_id`, 2026-08-22) | 확보 완료 (152KB) |
| Datacluster Labs — Glucometer Reading OCR | 실촬 폰 사진 **238장** (`assets_dev/upstream/datacluster-glucometer-ocr/`) — 값 GT 없음, 장치 박스뿐 | **CC0** (Kaggle License 필드, 게시자 설정. 단 설명문이 미공개 전체를 유료 판매한다고 밝힘 — 샘플 무료 배포와의 긴장은 기록 유지) | 확보 완료 2026-08-25 |
| Roboflow `glucometer-amtkm` | 실촬 **233장** (train/valid/test COCO, bbox 카테고리 `glucometer`/`7`/`glucometerrotation` — 값 GT 없음) | **CC BY 4.0** (배포 zip 내 `README.dataset.txt` 명시, 2026-08-27 확인) | 확보 완료 2026-08-26 |
| Roboflow `glucometer_images-bc9dh` | 실촬 **1,276장** (train+valid COCO, bbox 카테고리 `Digits`/`GM_SCREEN`/`READING`/`STRAIGHT`/`TIME` — 값 GT 없음) | **CC BY 4.0** (같은 방식 확인) | 확보 완료 2026-08-26 |
| Datumo / TILDE 통합 납품본 | 혈당계 실촬 **2,375장(1차)+137건(2차)** — **이미지 1장당 측정값 GT json 페어**(혈압계 9,500장·체중계·체온계가 한 파일에 섞여 납품됨). `assets_dev/upstream/datumo/` | **미확인 — 구매 조건 문서 수령 대기** (§4) | 수령·개봉 완료 2026-08-27 |
| Oxford / Finnegan 2019 — 혈당계·혈압계 실촬 | 논문 [10.1080/03091902.2019.1673844](https://www.tandfonline.com/doi/full/10.1080/03091902.2019.1673844), 기록 [ORA](https://ora.ox.ac.uk/objects/uuid:72be1fdf-327d-4d30-ab66-8892e642fc68) 의 라이선스는 **CC BY** | **확보 실패** — 아래 참조 | 2026-08-22 |

### Datumo(TILDE) 개봉 기록 — 2026-08-27

- 원본 `TILDE.zip`(74.8GB, D:\ 루트에서 이동) → `assets_dev/upstream/datumo/TILDE.zip`.
  생성 도구가 Mac 이라 한국 파일명이 NFD 로 들어 있다. zip 멤버 중 라벨 번들로 보이는
  것은 **딱 하나인데 이름은 「혈압계_json(BBOX+OCR).zip」**이다(14,500개 json, 전부
  sphygmomanometer). 처음 화면에 표시된 「혈당계」로 읽힌 것은 NFD 조합 표시 착시였다.
- **혈당계 GT 는 별도 번들이 아니라 이미지 egg 안에 이미지·json 1:1 페어로 들어 있다.**
  `.egg` 는 알집(EGGA 매직) 포맷이라 Bandizip(`bz.exe`)으로 개봉했다.
  batch1 = jpg 2,375 + json 2,375, batch2 = jpg 137 + json 137.
- 변환 스크립트 `_make_labels.py` 가 두 배치를 합쳐 `assets_dev/upstream/datumo/labels.jsonl`
  **2,512행**을 만들었다. 수치 GT 100%(4행은 벤더 json 문법 오류를 폴백 정규식으로 회복),
  값 범위 30~511, 38 미만은 1건(저혈당 30 — 표본 육안 일치 확인).
- 표본 눈 검증 3장: 30(선명 일치)·95(일치+화면의 05-18 DAY 12:18 이 json `Day-AVG/hour`
  완전 일치)·87(반사로 저대비 — 라벨 신뢰는 하나 후속 전수 검증 여지).
- 혈압계·체중계·체온계 데이터는 당장 용도가 없다. TILDE.zip 은 통째로 보관한다.

**Oxford 데이터셋은 사라졌다.** 배포처 `cameralab.eng.ox.ac.uk` 가 폐쇄되어
`data/bp_bg_meters.zip` 과 안내 페이지 `seven_segment.html` 이 모두
`eng.ox.ac.uk/lcmt` 로 302 리디렉트된다. **Wayback Machine 스냅샷도 zip 이 아니라
그 리디렉트 페이지(148바이트)를 담고 있어** 아카이브로도 복구되지 않는다.
남은 경로는 저자 문의(`eoin.finnegan@eng.ox.ac.uk`)뿐이다 —
[`CLAUDE_TASKS.md`](CLAUDE_TASKS.md) C2 에 딸린 항목으로 둔다.

> ORA 기록의 CC BY 는 **논문**에 붙은 것이다. 데이터셋 자체의 조건은 zip 안
> README 로만 확인할 수 있는데 그 zip 을 구할 수 없다. 확보하더라도 조건을
> 먼저 읽을 것 — "논문이 CC BY 니 데이터도 그렇다"는 추측이다.

**Kazuhito00 자산은 라이선스·규격이 둘 다 맞는다.** 생성기 기본 출력 96×96 이
`7seg_classifier.tflite` 의 입력 `[1, 96, 96, 3]` 과 일치한다(같은 저자). 합성
생성기를 새로 짤 이유가 없다.

**Apache-2.0 고지 의무**: 파생 모델을 앱에 번들하면 라이선스 사본과 저작자 고지,
그리고 **변경 사항 고지**가 필요하다. §4 에 항목이 있다.

---

## 2. 폰트

| 자산 | 용도 | 라이선스 | 앱에 반입되는가 |
|---|---|---|---|
| DSEG v0.46 (keshikan, [github](https://github.com/keshikan/DSEG), 2026-09-11 확인) | **합성 학습 데이터 생성 전용** — 7세그 폰트로 글리프 렌더. `assets_dev/train/fonts/dseg/` 에 12개 ttf + 원문 `DSEG-LICENSE.txt` 동봉 | **SIL OFL 1.1** (RFN "DSEG" — 수정·재배포 안 함, 렌더만) | 아니오 |
| Noto Sans KR / JP / SC | PDF 리포트 CJK 렌더링 | SIL OFL 1.1 | 예 |

SIL OFL 은 상업적 사용·임베딩을 허용하지만 **폰트 자체를 판매할 수 없고**
파생 폰트에 예약 이름을 쓸 수 없다. PDF 임베딩은 허용 범위 안이다.

> 리포트에 CJK 폰트를 임베딩하지 않으면 한국어·일본어 리포트에서 글자가 깨진다.
> 반면 3개 폰트를 모두 번들하면 앱 크기가 크게 늘어난다 → 필요한 폰트만 지연
> 로드하는 구조로 간다.

---

## 3. Flutter 패키지

`flutter pub deps` 기준 직접 의존 패키지는 대부분 BSD-3-Clause / MIT / Apache-2.0
이다. 출시 전 아래를 수행한다.

1. `flutter pub deps --style=compact` 로 전체 의존성 목록 확보
2. 앱 내 "오픈소스 라이선스" 화면 연결 (`showLicensePage`) — Flutter 가 패키지
   LICENSE 를 자동 수집하므로 별도 고지 문서를 만들 필요는 없다
3. GPL/AGPL 계열이 섞였는지 확인 (현재 목록에는 없음)

> **2026-09-17 해결**: `google_mlkit_text_recognition` 을 의존에서 **뺐다.**
> 플러그인 자체는 OSS 지만 구글 ML Kit SDK 는 별도 이용약관이고
> `showLicensePage` 자동 수집으로 덮이지 않는다. 그런데 `lib/` 에 실제 호출이
> 0건이었다(`OcrEngineKind.mlkit` 열거값과 "W5: MlKitEngine (비교군)" 주석뿐).
> **쓰지도 않으면서 약관만 지고 있었다.** 제거 후 `flutter analyze` 무경고 ·
> `flutter test` 471개 전부 통과. 비교군으로 다시 필요해지면 그때 넣고
> 이 표에 한 줄 적는다.

---

## 4. 미해결 항목

- [ ] **Datumo(TILDE 통합 납품본) 이용 조건 문서 확보** — 수령은 끝났지만 라이선스
      규정 문서가 아직 없다. 혈당계 2,512쌍을 벤치·학습에 쓰기 전에 확정한다
      > **2026-09-17 승격**: 이 항목은 더 이상 "쓰기 전에"가 아니다. **이미
      > 파생 가중치에 들어갔다** — `gmscreen_ft` 계열이 Datumo 410장으로
      > 학습됐고 그중 `ft3` 가 2026-09-12 운영 정본으로 승격됐다(§1.1).
      > 즉 조건이 확정되지 않은 데이터의 파생물이 파이프라인 정본이다.
      > 사람 라벨(`band_boxes`·`screen_boxes`·`device_labels`)도 전부 Datumo
      > 사진 위에 찍은 것이라 같은 우산 아래 있다.
      > 우회로가 하나 있다: 마일스톤 검출기 `synthband_v0` 는 Datumo 를 타지
      > 않는다(합성만 얹었다). 조건 확정이 늦어지면 **그쪽으로 출시하는 선택지**가
      > 존재한다는 뜻이다 — 다만 그건 성능 판단이 따로 필요하다.
- [x] ~~Downloads 에 남아 있는 Roboflow zip 원본 2개(≈4.6GB, upstream 으로 사본 확보됨)
      — 중복이므로 삭제 여부는 개발자 본인 판단~~ — **2026-08-27 MD5 대조 후 삭제 완료**
      (개발자 지시). 사본 해시와 완전 일치 확인済.
- [x] ~~EasyOCR 사전학습 가중치의 배포 조건 확인 — Jaided AI 문의 필요~~
      **2026-09-17 종결 — 문의 불필요.** EasyOCR 을 안 쓴다. 벤치에서 기각
      (크롭 9.3% · 원본 1.3% vs 자체 98.0%)됐고, 남겨 둔 유일한 이유였던 mmol/L
      소수점은 재구축 계획 §4 가 우리 리더 charset 에 소수점을 넣기로 하면서
      사라졌다. 쓰지 않는 모델의 조건을 확인할 의무는 없다.
      > 이 항목이 2026-09-17 까지 열려 있었던 이유: 기각은 벤치 보고서에,
      > 소수점 대체는 재구축 계획에 각각 적혔는데 **이 문서에는 반영되지
      > 않았다.** 라이선스 표는 "무엇을 쓰기로 했나"를 따라가야 하는데
      > 후보 시절 문구가 남아 살아 있는 의무처럼 보였다.
- [x] ~~fine-tune 파생 가중치의 라이선스 귀속 확인 — EasyOCR 조건에 의존~~
      **위 항목과 함께 종결.** 단 검출기 파생 가중치는 별개이고 §1.1 에 있다.
- [ ] 실촬 학습 데이터에 타인의 혈당계·개인정보가 찍히지 않도록 하는 수집 지침 문서화
- [ ] 출시 빌드에 `showLicensePage` 연결
- [ ] **Apache-2.0 고지**: `7seg_classifier.tflite` 는 앱에 직접 번들되므로 라이선스 사본과 저작자 고지를 앱 내 라이선스 화면에 포함해야 한다. 모델을 fine-tune 해 교체하면 "변경 사항 고지"도 함께 필요하다.
- [ ] **GM 검출기를 앱에 넣을 때의 고지 둘** (2026-09-04 추가) — 지금은 학습·평가에서만
      돌아서 의무가 발생하지 않지만, 파이프라인상 앱 반입이 예정된 자산이다.
      1. **YOLOX Apache-2.0 고지** — 구조·학습 코드가 Megvii YOLOX 파생이다.
      2. **Roboflow `glucometer_images-bc9dh` CC BY 4.0 귀속** — GM 베이스 가중치가
         이 데이터셋으로 학습됐다. CC BY 는 **저작자 표시가 조건**이라 파생
         가중치를 배포하면 따라온다. 데이터셋이 앱에 안 들어간다고 면제되지 않는다.
      3. (2026-09-17 추가) **`yolox_nano.pth` 가중치 자체의 조건** — 계보의
         뿌리인데 문서에 없었다. YOLOX README 가 가중치를 배포하면서 가중치
         라이선스를 따로 적지 않는다. EasyOCR 과 같은 구멍이라 같은 취급을
         해야 한다(§1.1).
      4. (2026-09-17 추가) **어느 체크포인트를 넣느냐로 의무가 갈린다** —
         `synthband_v0` 와 `gmscreen_ft3` 는 계보가 다르다(§1.1 표).
      > 이 두 줄이 2026-09-04 까지 이 문서에 **없었다.** 검출기가 저장소 밖
      > (`D:\tmp\YOLOX`)에 있어서 반입 자산 점검에서 통째로 빠져 있었다.
      > 저장소 밖 의존은 이 표에 안 잡힌다 — 다음에 외부 체크아웃을 쓰게 되면
      > 그 자리에서 여기에 한 줄 적을 것.
