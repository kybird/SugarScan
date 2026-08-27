# 서드파티 라이선스 검토

> 최초 작성 2026-08-20 · 담당: 개발자 본인
> 라이선스 실사: 2026-08-21 (G5) — 아래 각 행의 확인 URL 은 당일 직접 연 기준.
> 남은 미해결 항목은 §4 참조.

앱에 실제로 반입되는 자산(모델 가중치·폰트·학습 코드)의 상업적 사용 가능 여부와
고지 의무를 여기에 모은다. 정확도만 보고 모델을 골랐다가 출시 직전에 라이선스로
막히는 것이 이 프로젝트에서 가장 값비싼 실수가 된다.

---

## 1. OCR 모델 / 학습 코드

| 자산 | 출처 | 라이선스 | 앱에 반입되는가 | 상태 |
|---|---|---|---|---|
| EasyOCR | JaidedAI/EasyOCR | **코드: Apache-2.0** ([LICENSE](https://github.com/JaidedAI/EasyOCR/blob/master/LICENSE), 2026-08-21 확인) | 코드는 아니오, **가중치는 예**(ONNX 변환본) | **가중치: 확인 실패** — README·공식 사이트 어디에도 가중치의 배포 조건이 명시되어 있지 않다. 코드 LICENSE 가 가중치까지 덮는다는 문구도 없다. 반입 전 Jaided AI 에 직접 확인 필요 |
| CRAFT (text detector) | clovaai/CRAFT-pytorch | **MIT** (Copyright (c) 2019-present NAVER Corp., [LICENSE](https://github.com/clovaai/CRAFT-pytorch/blob/master/LICENSE), 2026-08-21 확인) — **연구용 한정 조항 없음.** LICENSE 원문과 README 어디에도 비상업 조항이 없는 순수 MIT 다 | **미반입** (가이드 박스로 대체) | 확인 완료 |
| deep-text-recognition-benchmark | clovaai | **Apache-2.0** ([LICENSE.md](https://github.com/clovaai/deep-text-recognition-benchmark/blob/master/LICENSE.md), 2026-08-21 확인 — 파일명이 `LICENSE.md` 다) | 아니오 (학습 도구) | 확인 완료 |
| ONNX Runtime | microsoft/onnxruntime | **MIT** (Copyright (c) Microsoft Corporation, [LICENSE](https://github.com/microsoft/onnxruntime/blob/master/LICENSE), 2026-08-21 확인) | 예 (flutter_onnxruntime 경유) | 확인 완료 |
| **7seg_classifier.tflite** | [Kazuhito00/7segment-display-reader](https://github.com/Kazuhito00/7segment-display-reader) | **Apache-2.0** (GitHub API 확인 완료) | **예** — `assets/models/` 에 번들 | 고지 의무 반영 필요 |
| TensorFlow Lite | tflite_flutter 경유 | **Apache-2.0** (TensorFlow 본저장소 [LICENSE](https://github.com/tensorflow/tensorflow/blob/master/LICENSE), 2026-08-21 확인. 원문 말미에 Caffe 유래 코드의 BSD 스타일 고지가 함께 실려 있다) | 예 | 확인 완료 |

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
| DSEG (7-세그먼트) | **합성 학습 데이터 생성 전용** | SIL OFL 1.1 | 아니오 |
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

---

## 4. 미해결 항목

- [ ] **Datumo(TILDE 통합 납품본) 이용 조건 문서 확보** — 수령은 끝났지만 라이선스
      규정 문서가 아직 없다. 혈당계 2,512쌍을 벤치·학습에 쓰기 전에 확정한다
- [ ] Downloads 에 남아 있는 Roboflow zip 원본 2개(≈4.6GB, upstream 으로 사본 확보됨)
      — 중복이므로 삭제 여부는 개발자 본인 판단
- [ ] EasyOCR 사전학습 가중치의 배포 조건 확인 — 2026-08-21: 공개 문서상 명시가
      없음을 확인. Jaided AI 문의 필요
- [ ] fine-tune 파생 가중치의 라이선스 귀속 확인 — EasyOCR 가중치 조건 확인에
      의존하므로 위 항목과 함께 진행
- [ ] 실촬 학습 데이터에 타인의 혈당계·개인정보가 찍히지 않도록 하는 수집 지침 문서화
- [ ] 출시 빌드에 `showLicensePage` 연결
- [ ] **Apache-2.0 고지**: `7seg_classifier.tflite` 는 앱에 직접 번들되므로 라이선스 사본과 저작자 고지를 앱 내 라이선스 화면에 포함해야 한다. 모델을 fine-tune 해 교체하면 "변경 사항 고지"도 함께 필요하다.
