# 모델 에셋

이 디렉터리의 `.tflite` / `.onnx` 파일은 저장소에 커밋된다(라이선스가 허용하고
크기가 작은 경우에 한함). 학습 중간 산출물(`.pth`, 체크포인트)은 커밋하지 않는다.

## band_detector.onnx · reader_crnn.onnx (커밋됨 · 2026-10-10)

| | band_detector | reader_crnn |
|---|---|---|
| 출처 | 자체 설계·학습 (BandNet `ftk5_g0.06`) | 자체 설계·학습 (CRNN `rftk5_foldall`) |
| 크기 | 4,491,297 B (4.49MB) | 9,277,118 B (9.28MB) |
| 입력 | `image [1,1,640,640]` float32 (/255, 레터박스 패드 114) | `crop [1,1,96,144]` float32 (/255−0.5) |
| 출력 | `obj [1,1,40,40]` logit + `reg [1,4,40,40]` softplus(l,t,r,b) | `logits [1,36,11]` (0~9 + blank=10) |
| 사용처 | `BandNetCrnnEngine` (mg/dL 전용) | 같음 |

변환·전량 파리티 자(실촉 2,504장 판정 완전 일치): `assets_dev/train/export_deploy_onnx.py`.
디코드(argmax·ltrb·CTC greedy)는 그래프 밖 `lib/ocr/src/engines/bandnet_crnn/`
의 순수 Dart 로 돈다.

**계보·라이선스**: 외부 사전학습 가중치·외부 데이터셋 0 으로 학습됐으나
**실촉 파인튜닝에 셀렉트스타 지원사업 "디지털 숫자 데이터셋"(틸더 협업)
2,504쌍이 들어갔다 — 라이선스 CC BY-SA 3.0**(2026-10-10 데이터셋 상세
페이지에서 확정). 이행: 앱 라이선스 화면에 출처 표기(BY) + 이 모델 파일들의
CC BY-SA 3.0 배포 표기(SA 안전판) — `docs/LICENSES.md` §1.5·§1.6·§4.

두 파일이 없어도 앱은 정상적으로 동작한다. `OnnxRuntimeModel.tryLoad()` 가
null 을 돌려주고, 스캐너는 다음 엔진(규칙 기반)으로 넘어가거나 수동 입력으로
안내한다.

## 7seg_classifier.tflite (커밋됨 · `f10074a`)

| | |
|---|---|
| 출처 | [Kazuhito00/7segment-display-reader](https://github.com/Kazuhito00/7segment-display-reader) |
| 라이선스 | Apache-2.0 |
| 크기 | 609,904 바이트 (약 596 KB) |
| 입력 | `[1, 96, 96, 3]` float32, RGB, 0~1 정규화 |
| 출력 | `[1, N]` 클래스 점수 — 0~9 는 숫자, 그 이상은 "표시 없음" |
| 사용처 | `SevenSegCnnEngine` (mg/dL 전용) |

출처(이미 커밋돼 있으므로 받을 필요 없다 — 재취득용):

```bash
curl -L -o assets/models/7seg_classifier.tflite "https://github.com/Kazuhito00/7segment-display-reader/raw/main/02.model/7seg_classifier.tflite"
```

파일이 없어도 앱은 정상적으로 동작한다. `TfliteDigitClassifier.tryLoad()` 가
null 을 돌려주고, 스캐너는 `ScanUnavailable(modelUnavailable)` 을 내며, 앱은
수동 입력으로 안내한다.

## 라이선스 고지

Apache-2.0 은 배포 시 라이선스 사본과 변경 사항 고지를 요구한다. 출시 전
`docs/LICENSES.md` 의 미해결 항목과 앱 내 오픈소스 라이선스 화면에 반영할 것.
