# 모델 에셋

이 디렉터리의 `.tflite` / `.onnx` 파일은 저장소에 커밋된다(라이선스가 허용하고
크기가 작은 경우에 한함). 학습 중간 산출물(`.pth`, 체크포인트)은 커밋하지 않는다.

## 7seg_classifier.tflite (아직 없음)

| | |
|---|---|
| 출처 | [Kazuhito00/7segment-display-reader](https://github.com/Kazuhito00/7segment-display-reader) |
| 라이선스 | Apache-2.0 |
| 크기 | 609,904 바이트 (약 596 KB) |
| 입력 | `[1, 96, 96, 3]` float32, RGB, 0~1 정규화 |
| 출력 | `[1, N]` 클래스 점수 — 0~9 는 숫자, 그 이상은 "표시 없음" |
| 사용처 | `SevenSegCnnEngine` (mg/dL 전용) |

내려받기:

```bash
curl -L -o assets/models/7seg_classifier.tflite "https://github.com/Kazuhito00/7segment-display-reader/raw/main/02.model/7seg_classifier.tflite"
```

파일이 없어도 앱은 정상적으로 동작한다. `TfliteDigitClassifier.tryLoad()` 가
null 을 돌려주고, 스캐너는 `ScanUnavailable(modelUnavailable)` 을 내며, 앱은
수동 입력으로 안내한다.

## 라이선스 고지

Apache-2.0 은 배포 시 라이선스 사본과 변경 사항 고지를 요구한다. 출시 전
`docs/LICENSES.md` 의 미해결 항목과 앱 내 오픈소스 라이선스 화면에 반영할 것.
