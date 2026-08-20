# sugarScan — Flutter 구현계획서

> 문서 버전 v1.0 · 작성일 2026-08-20 · 대상 PRD: 온디바이스 OCR 기반 글로벌 혈당 관리 앱 sugarScan
> 개발 환경: Flutter 3.44.7 (stable) / Dart 3.12.2

---

## 0. 확정된 기술 결정 (Decision Log)

| # | 항목 | 결정 | 근거 / 영향 |
|---|------|------|-------------|
| D-1 | OCR 아키텍처 | **플러그인(교체 가능) 구조**. `OcrEngine` 추상 인터페이스 + 런타임 레지스트리 | 오픈소스 엔진을 실측으로 갈아끼우며 정확도를 끌어올리는 전략. 앱 코드는 엔진 구현에 의존하지 않음 |
| D-2 | 1차 OCR 엔진 | ~~EasyOCR~~ → **규칙 기반 판독기**(W1-d 에서 변경) | 7-세그먼트는 상태 공간이 유한하고 구조가 명시적이라 학습 모델이 과잉이다. 규칙 판독기가 소수점·LO/HI 까지 읽으므로 EasyOCR 은 조건부 후순위로 내렸다. §15 W1-d |
| D-3 | 백엔드 | **Supabase (Postgres + Auth + RLS)**, 초기부터 동기화 | 다기기 동기화·계정 복구를 MVP에 포함. EU 리전 선택으로 GDPR 대응 |
| D-4 | 로컬 저장 | **Drift(SQLite)가 source of truth**, Supabase는 복제본 | 오프라인 우선. 카메라 스캔은 네트워크 없이 완결되어야 함 |
| D-5 | 초기 플랫폼 | **Android 우선 → iOS 순차** | CameraX 프레임 파이프라인 디버깅 용이, 저가형 혈당기 사용자 비중 |
| D-6 | 상태관리 / 라우팅 | Riverpod 3 + go_router | 코드젠 기반 DI, 테스트 격리 용이 |
| D-7 | 리소스 | 1인 풀타임 | 로드맵(§12)은 1인 기준 주 단위로 재산정 |

---

## 0.1 PRD 대비 반드시 조정해야 할 3가지 (현실 체크)

계획을 실행하기 전에, PRD의 아래 3개 항목은 기술적/규제적으로 수정이 필요합니다.

**① "60fps 라이브 OCR" → 프리뷰 30fps + 추론 8~12fps 스로틀링**
중급 Android 기기에서 프레임당 CRNN 추론은 40~120ms입니다. 60fps(16.6ms/frame) 추론은 불가능하며, 시도하면 프레임 큐가 밀려 오히려 체감 지연이 커집니다.
→ **프리뷰는 30fps로 부드럽게 유지하고, "in-flight 프레임 1개" 규칙으로 추론만 스로틀링**합니다. 사용자 체감(첫 인식까지 0.5초)은 이 구조로도 충족됩니다.

**② "셔터 없이 자동 입력" → 자동 인식 + 사용자 1탭 확인 필수**
OCR 오독(예: `95` → `195`)이 무확인으로 기록되면 ⓐ 사용자가 잘못된 추이를 보고 행동을 바꿀 위험, ⓑ "측정값을 앱이 판단한다"는 인상 → General Wellness 포지셔닝(§10) 방어선이 무너집니다.
→ **인식은 자동, 저장은 확인 1탭.** 확인 시트에 인식값을 크게 띄우고 ±1 스텝 보정과 수동 입력 전환을 같은 화면에 둡니다. 이건 UX 타협이 아니라 **안전 요구사항**으로 취급합니다.

**③ EasyOCR은 Python/PyTorch 라이브러리 → Flutter에서 직접 실행 불가**
`pip install easyocr`를 앱에 넣을 수는 없습니다. 온디바이스로 가져오려면 모델을 ONNX로 export해 `flutter_onnxruntime`으로 추론해야 합니다.
→ 이 경로는 실현 가능하며(§2.5), 오히려 **detector(CRAFT)를 생략하고 recognizer만 돌릴 수 있어 더 빠릅니다.** 단, 변환·fine-tune에 3~4주가 필요하다는 점을 일정에 반영했습니다.

---

## 1. 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│  Presentation (Flutter Widgets + Riverpod Notifier)         │
│  scan · dashboard · history · stats · report · settings     │
└───────────────┬─────────────────────────────────────────────┘
                │ (도메인 모델만 통과 / UI에서만 단위·로케일 변환)
┌───────────────▼─────────────────────────────────────────────┐
│  Domain (순수 Dart, Flutter 의존 0)                          │
│  GlucoseReading · GlucoseUnit · MeasurementTag               │
│  TagSuggester · Ea1cCalculator · GlucoseValidator            │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼──────────────┐  ╔══════════════════════════╗
│  Data                        │  ║  OCR 모듈 (§2) — 격리     ║
│  ├ local: Drift (정본)       │  ║  ┌────────────────────┐  ║
│  ├ remote: Supabase          │  ║  │ GlucoseScanner     │  ║ ← 앱이 보는 전부
│  ├ sync: Outbox + 델타 pull  │  ║  └────────────────────┘  ║
│  └ health: HealthKit/HC      │  ║   src/ (모듈 내부)        ║
└──────────────────────────────┘  ║   ├ Normalizer·Validator ║
                                  ║   ├ Stabilizer           ║
                                  ║   └ Engines (교체 가능)   ║
                                  ╚══════════════════════════╝
```

**모듈 경계 규칙 (1인 개발이어도 지킬 것)**
- `domain/`은 `package:flutter`를 import하지 않는다 → 순수 유닛테스트 가능.
- **`ocr/`은 `lib/ocr/ocr.dart` 배럴 하나로만 노출된다.** 앱은 `src/` 안을 import하지 않는다. `ocr/`은 `domain/`(혈당값의 정의)에만 의존하고 `data/`·`features/`·`app/`은 모른다.
- **앱은 OCR 결과를 재검증하지 않는다.** OCR 특유의 보정(글자 오인식, 단위 표기, HI/LO)은 모듈 안에, 혈당값의 도메인 규칙(물리 범위·자릿수)은 `domain/`에 둔다. 후자는 수동 입력 경로와 공유한다.
- 단위 변환(mg/dL ↔ mmol/L)은 **presentation에서만** 수행. domain/data는 항상 mg/dL 정본.

---

## 2. OCR 플러그인 계층 (프로젝트의 핵심)

### 2.1 설계 원칙

1. **OCR 모듈은 격리된 블랙박스다.** 앱은 프레임을 넣고 결과를 받을 뿐이다. 글자 보정·값 검증·프레임 간 합의는 **전부 모듈 안에서 끝난다.**
2. **앱은 모듈의 결과를 무조건 신뢰한다.** `ScanConfirmed` 가 나왔다는 것은 곧 "쓸 수 있는 값"이라는 뜻이며, 앱은 재검증하지 않는다. 앱이 OCR 결과를 판정해야 한다면 엔진을 바꿀 때마다 앱도 같이 바뀐다.
3. **OCR 은 단말에서만 돌아간다.** 서버 인식 경로는 두지 않는다. 레지스트리가 네트워크를 요구하는 엔진의 등록을 **항상** 거부하며, 이 원칙에 조건부 허용 플래그를 두지 않는다 — 플래그가 있으면 언젠가 켜진다. 정확도 비교 실험은 앱이 아니라 PC 측 `tools/ocr_bench` 에서 한다.
4. **엔진은 모듈 내부 부품이다.** 엔진은 후보와 신뢰도만 돌려주고 판정하지 않는다. 엔진을 교체해도 보정·안전 로직은 그대로 유지되며, 그 교체가 앱 코드에 전혀 드러나지 않는다.
5. **모든 엔진은 동일한 골든 데이터셋으로 채점된다** (§2.6). 감(感)이 아니라 수치로 승격을 결정한다.

> **모듈 신뢰와 사용자 확인은 다른 층이다.** 앱이 OCR 결과를 재검증하지 않는 것은 아키텍처 결정이고, 저장 전 사용자 확인 1탭(§0.1-②)은 안전·규제 요구다. 확인 화면은 값을 의심해서가 아니라, 사용자가 자기 기록의 최종 결정권을 갖게 하려고 존재한다.

### 2.2 공개 표면 — 앱이 보는 것의 전부

```dart
// lib/ocr/ocr.dart  ← 앱은 이 배럴만 import 한다
sealed class ScanOutcome {}

final class ScanIdle      extends ScanOutcome {}
final class ScanScanning  extends ScanOutcome { double progress; String? previewValue; }
final class ScanConfirmed extends ScanOutcome {
  double value;          // 보정·검증까지 끝난 값
  GlucoseUnit unit;
  double get valueMgdl;  // 저장 정본. 앱은 단위 변환도 신경 쓸 필요가 없다
  double confidence; String engineId; String rawText; int frameCount;
}
final class ScanRejected    extends ScanOutcome { ScanRejectionReason reason; }  // meterHigh / meterLow
final class ScanUnavailable extends ScanOutcome { ScanUnavailableReason reason; }

class GlucoseScanner {
  Future<ScanOutcome> start({required GlucoseUnit unit, String? engineId});
  Future<ScanOutcome> offer(OcrFrame frame);   // 절대 예외를 던지지 않는다
  void reset();
  Future<void> stop();
}
```

앱 쪽 코드는 이게 전부다.

```dart
switch (await scanner.offer(frame)) {
  ScanConfirmed(:final value, :final unit) => showConfirmSheet(value, unit),
  ScanRejected(:final reason)              => showMeterRangeMessage(reason),
  ScanUnavailable()                        => goToManualEntry(),
  _                                        => updateScanningUi(),
}
```

`offer` 는 추론이 진행 중이면 프레임을 버리고 **직전 상태를 그대로** 돌려준다. 앱은 프레임이 드롭됐는지조차 알 필요가 없다.

### 2.2.1 내부 인터페이스 (모듈 밖으로 나가지 않음)

```dart
// lib/ocr/src/engine/ocr_engine.dart
enum OcrEngineKind { onnx, mlkit, tesseract, tflite, fake }

class OcrEngineDescriptor {
  final String id;                 // 'easyocr_onnx_v1'
  final String displayName;
  final OcrEngineKind kind;
  final bool supportsLiveStream;   // 라이브 프레임 처리 가능 여부
  final bool requiresNetwork;      // true면 레지스트리가 항상 등록을 거부
  final int targetLatencyMs;
  final Set<OcrImageFormat> acceptedFormats;
  final Set<GlucoseUnit> supportedUnits;  // 소수점을 못 읽는 모델은 mg/dL 만
}

/// 파이프라인이 엔진에 넘기는 단일 프레임.
class OcrFrame {
  final Uint8List bytes;
  final OcrImageFormat format;     // nv21 / yuv420 / bgra8888 / grayscale8 / png
  final int width, height;
  final int rotationDegrees;
  final Rect? roi;                 // 가이드 박스 (정규화 좌표 0~1)
}

class OcrCandidate {
  final String rawText;            // '138' / '7.6'
  final double confidence;         // 0.0 ~ 1.0
  final List<double> perCharConfidence;
}

class OcrResult {
  final String engineId;
  final List<OcrCandidate> candidates;  // 신뢰도 내림차순
  final Duration latency;
  final OcrFailure? failure;
}

/// 모든 엔진이 구현하는 유일한 계약.
abstract interface class OcrEngine {
  OcrEngineDescriptor get descriptor;
  Future<void> initialize(OcrEngineConfig config);
  bool get isReady;                // 모델 에셋이 없으면 false
  Future<OcrResult> recognize(OcrFrame frame);
  Future<void> dispose();
}
```

```dart
// lib/ocr/src/engine/ocr_engine_registry.dart
class OcrEngineRegistry {
  void register(OcrEngineDescriptor d, OcrEngine Function() factory);  // 네트워크 엔진 거부
  Future<OcrEngine> activate(String id);      // 이전 엔진 dispose 후 교체
  Future<OcrEngine?> activateFirst();
  List<OcrEngineDescriptor> get available;
}
```

> **왜 `abstract interface class`인가**: Dart 3의 `interface` 한정자로 서브클래싱을 막고 구현만 허용 → 엔진이 공통 파이프라인 로직을 상속으로 우회하는 것을 컴파일 타임에 차단합니다.

### 2.3 인식 파이프라인 — 전부 모듈 안에서 끝난다

```
┌─ 앱 ──────────────────────────────────────────────────────────┐
│  CameraController.startImageStream (30fps) → scanner.offer()  │
└──────────────────────────────┬────────────────────────────────┘
                               │  OcrFrame
╔══════════════════════════════▼════════════════════════════════╗
║  OCR 모듈 (lib/ocr) — 격리                                     ║
║                                                                ║
║   FrameThrottler      [Gate] 추론 진행 중이면 프레임 드롭       ║
║        │                     (in-flight = 1)                   ║
║        ▼              ROI 크롭 → 회전 보정 → 그레이스케일       ║
║   Preprocessor        → 32px 높이 리사이즈 (Isolate)           ║
║        │                                                       ║
║        ▼                                                       ║
║   OcrEngine.recognize()      ← ★ 여기만 교체 가능              ║
║        │  "138 mg/dL" / "1O5" / "LO"                           ║
║        ▼                                                       ║
║   ReadingNormalizer   ① 단위 표기 제거                          ║
║        │              ② HI/LO 판정  ← 순서가 안전을 만든다      ║
║        │              ③ 글자 교정(I→1, O→0, S→5, B→8)          ║
║        ▼                                                       ║
║   GlucoseValidator    포맷·자릿수·물리 범위                     ║
║        │              (검증 실패값은 안정화기에 들어가지 않음)   ║
║        ▼                                                       ║
║   ReadingStabilizer   동일값 3회 연속 + 평균 conf ≥ 0.85        ║
║        │                                                       ║
╚════════▼═══════════════════════════════════════════════════════╝
         │  ScanConfirmed(value, unit, valueMgdl, confidence, …)
┌────────▼──────────────────────────────────────────────────────┐
│  앱: 햅틱 + 하이라이트 → 확인 시트 → 저장                       │
│      값을 재검증하지 않는다                                     │
└───────────────────────────────────────────────────────────────┘
```

**`ReadingNormalizer` 의 순서가 곧 안전 장치다.** 글자 교정을 먼저 하면 혈당계의 저혈당 표시 `LO` 가 L→1, O→0 을 거쳐 **`10` 이라는 정상 범위 값으로 둔갑**한다. 사용자는 실제로 위험한 저혈당인데 앱에는 평범한 숫자가 남는다. 같은 이유로 `mg/dL` 의 D·L 이 교정되어 `138 mg/dL` 이 `13801` 이 된다. 그래서 ①→②→③ 순서를 회귀 테스트로 고정해 두었다.

**`ReadingStabilizer` 가 존재하는 이유**: 단일 프레임 오독을 프레임 간 합의로 걸러낸다. 엔진이 한 프레임에서 `95` 를 `195` 로 잘못 읽어도 연속 프레임이 같은 오답을 반복하지 않는 한 확정되지 않는다. 덕분에 앱이 결과를 그대로 신뢰할 수 있고, 엔진 정확도가 완벽하지 않아도 제품이 성립한다.

**Isolate 전략**: `flutter_onnxruntime` 세션은 생성 비용이 크므로 장기 실행 isolate 하나를 띄우고 `SendPort`로 프레임을 전달합니다. `Isolate.run`(매 호출마다 생성)은 사용하지 않습니다.

### 2.4 엔진 로스터와 도입 순서

| 순서 | 엔진 | 역할 | 상태 |
|------|------|------|------|
| 1 ★ | `SegmentRuleEngine` | **기본 엔진.** 규칙 기반 7-세그먼트 판독. 소수점·LO/HI 를 읽어 두 단위 모두 지원. 모델 에셋 없음 | **구현 완료 (W1-d)** |
| 2 | `SevenSegCnnEngine` | 자릿수 분류 CNN(TFLite) 비교군. **mg/dL 전용** — 소수점 클래스 없음 | 구현 완료 (W1-c) |
| 3 | `EasyOcrOnnxEngine` | 규칙 판독기가 실촬에서 무너지는 구간이 확인될 때만 도입 | 조건부, W4~ |
| 4 | `MlKitEngine` | 비교군 (`google_mlkit_text_recognition`) | 벤치마크용 |
| 5 | `TesseractEngine` | 비교군 (`flutter_tesseract_ocr` + letsgodigital) | 선택 |

**수동 입력은 엔진이 아니다.** OCR 실패는 "엔진 하나가 더 있는 것"이 아니라 모듈이 `ScanUnavailable` 을 돌려주는 것이고, 앱은 그 신호를 받아 수동 입력 화면으로 안내한다. 카메라 권한 거부·모델 로딩 실패·저사양 기기 어느 경우에도 사용자가 기록을 남기지 못하는 상태는 만들지 않는다.

**EasyOCR 개발 서버는 앱 엔진이 아니다.** 골든 데이터셋 라벨링과 정확도 상한 측정에 쓰는 PC 측 도구(`tools/easyocr_server` + `tools/ocr_bench`)이며, 앱에는 어떤 형태로도 들어가지 않는다. `requiresNetwork == true` 인 엔진은 빌드 모드와 무관하게 레지스트리 등록 단계에서 예외로 막힌다.

### 2.5 EasyOCR 온디바이스 반입 경로 (상세)

```
[PC / Python]                                    [Flutter 앱]
easyocr (Apache-2.0)
 ├ CRAFT detector  ──▶ (생략)  ← ROI 가이드 박스로 대체
 └ CRNN recognizer ──▶ 7-세그먼트 fine-tune ──▶ ONNX export ──▶ assets/models/
   (None-VGG-BiLSTM-CTC)                                              │
                                                                      ▼
                                                     flutter_onnxruntime 1.8.3
                                                     (android/ios 지원 확인 완료)
                                                                      │
                                                                      ▼
                                                          CTC greedy decode (Dart)
```

**핵심 최적화 3가지**
1. **Detector 생략** — 사용자가 혈당기 화면을 가이드 박스에 맞추므로 텍스트 위치 탐지가 불필요합니다. CRAFT를 빼면 추론 비용이 절반 이하로 떨어집니다. (가이드 박스 없는 자유 인식은 백로그)
2. **문자집합 축소** — 출력 클래스를 `0123456789.` (+ 필요 시 `-`, `H`, `L`) 11~14개로 줄입니다. 최종 FC 레이어가 작아져 모델 크기와 오독 후보가 동시에 감소합니다.
3. **입력 규격 고정** — grayscale 1×32×W. 동적 width 대신 고정 width로 export하면 모바일 런타임 최적화가 잘 적용됩니다.

**학습 데이터 전략 (`tools/easyocr_train/`)**
- 합성 데이터 5만장: DSEG7 계열 폰트로 숫자 렌더 → LCD 배경 합성 → 증강(원근 왜곡 ±20°, 가우시안 블러, 반사 하이라이트 스팟, 저대비, 배터리 저하로 흐려진 세그먼트, 모션 블러, JPEG 아티팩트).
- **실촬 데이터 500~2,000장**: 보유/지인 혈당기 + 중고 기기 3~5종. 조명 5종 × 각도 5종. 정확도를 좌우하는 진짜 자산이므로 W1부터 상시 수집합니다.
- 학습: EasyOCR의 `trainer/`(deep-text-recognition-benchmark, Apache-2.0) 사용. 합성으로 사전학습 → 실촬로 fine-tune.

**라이선스 확인 항목 (W1에 문서화)**: easyocr Apache-2.0 / CRAFT-pytorch MIT / deep-text-recognition-benchmark Apache-2.0 / DSEG 폰트 SIL OFL. 각 항목의 상업적 사용 가능 여부와 고지 의무를 `docs/LICENSES.md`에 정리합니다.

**플랜 B (fine-tune이 W7 게이트 미달 시)**: 문자집합이 11개뿐이므로, ROI 안에서 자릿수를 분할한 뒤 **소형 CNN 단일 문자 분류기(입력 32×32, 파라미터 <200K)** 로 교체합니다. CRNN보다 학습이 훨씬 쉽고 빠릅니다. 플러그인 구조 덕분에 이 교체는 `OcrEngine` 구현 1개 추가로 끝납니다 — **이것이 D-1을 선택한 실질적 이유입니다.**

### 2.6 벤치마크 하네스와 골든 데이터셋

```
tools/ocr_bench/            # Dart CLI
  bin/bench.dart            # 등록된 모든 엔진 × 골든셋 → 리포트
assets_dev/golden/
  images/0001.jpg …
  labels.jsonl              # {"file":"0001.jpg","value":"138","unit":"mgdl",
                            #  "device":"Accu-Chek Guide","light":"dim","angle":25}
```

리포트 출력 항목: 완전일치 정확도 / **치명적 오독률**(자릿수가 달라진 오독, `95→195` 유형) / 미인식률 / p50·p95 지연 / 모델 크기. 조명·각도·기기별 분해 결과도 함께 출력해 약점을 특정합니다.

CI(GitHub Actions)에서 PR마다 실행해 회귀를 차단합니다.

### 2.7 엔진 승격 게이트 (이 수치를 넘겨야 기본 엔진이 됨)

| 지표 | 기준 |
|------|------|
| 완전일치 정확도 | ≥ 98.0% (골든셋 전체) |
| 치명적 오독률 | ≤ 0.2% |
| 미인식률(3초 내 미확정) | ≤ 5% |
| p95 지연 (중급 Android, Galaxy A54급) | ≤ 400ms |
| 모델 에셋 크기 | ≤ 20MB |

---

## 3. 프로젝트 구조

```
lib/
  main.dart
  app/
    app.dart                    # MaterialApp.router, 테마, 로컬라이제이션
    router.dart                 # go_router 라우트 정의
    theme/                      # 라이트/다크 토큰
  core/
    result.dart                 # Result<T, E>
    errors.dart
    logging.dart
    extensions/
  l10n/
    app_en.arb  app_ko.arb  app_de.arb  app_es.arb  app_ja.arb
  domain/
    models/
      glucose_reading.dart
      glucose_unit.dart         # mgdl / mmoll + 변환
      measurement_tag.dart      # fasting/preMeal/postMeal/postExercise/bedtime/random
      reading_source.dart       # ocr/manual/ble/healthSync/import
    services/
      tag_suggester.dart        # 순수 함수 (F-2)
      ea1c_calculator.dart      # ADAG 공식 (F-5)
      glucose_validator.dart
      glucose_statistics.dart   # 평균/표준편차/목표범위내비율(TIR)
  data/
    local/
      database.dart             # Drift
      tables/
      daos/
    remote/
      supabase_client.dart
      reading_api.dart
      dto/
    sync/
      sync_engine.dart          # push(outbox) + pull(delta)
      outbox_repository.dart
      conflict_resolver.dart
    health/
      health_repository.dart    # HealthKit / Health Connect
  ocr/                          # ★ 격리 모듈
    ocr.dart                    # 공개 표면: GlucoseScanner + ScanOutcome + OcrFrame
    testing.dart                # 테스트 전용 표면 (FakeOcrEngine 등)
    src/                        # 이 아래는 모듈 밖으로 나가지 않는다
      scanner/
        glucose_scanner.dart    # 파사드. 앱이 접촉하는 유일한 지점
        scan_outcome.dart
      correction/
        reading_normalizer.dart # 단위 제거 → HI/LO → 글자 교정
        reading_stabilizer.dart # 프레임 간 합의
      pipeline/
        frame_throttler.dart
      engine/                   # §2.2.1 인터페이스 + 레지스트리
      engines/
        easyocr_onnx/
        mlkit/
        tesseract/
        fake/                   # 테스트용
      ocr_bootstrap.dart        # 엔진을 등록하는 유일한 지점
  features/
    scan/       dashboard/      history/      stats/
    report/     settings/       onboarding/   auth/
tools/
  ocr_bench/                    # Dart CLI 벤치마크
  easyocr_train/                # Python: 합성데이터·학습·ONNX export
  easyocr_server/               # Python: FastAPI 개발 서버
docs/
  IMPLEMENTATION_PLAN.md        # 이 문서
  LICENSES.md  PRIVACY.md  SECURITY.md
supabase/
  migrations/                   # SQL 마이그레이션
test/            integration_test/
```

---

## 4. 의존성

> **아래는 계획 시점의 목표 목록이다. 실제로 `flutter pub get` 이 통과한 확정
> 버전과 그 과정에서 발견한 3건의 제약은 §15 구현 로그를 참조할 것.**

```yaml
environment:
  sdk: ^3.12.0
  flutter: ">=3.44.0"

dependencies:
  flutter: {sdk: flutter}
  flutter_localizations: {sdk: flutter}

  # 상태관리 / 라우팅
  flutter_riverpod: ^3.4.2
  riverpod_annotation: ^3.0.0        # riverpod_generator와 짝 버전 확인
  go_router: ^17.5.0

  # 카메라 / OCR
  camera: ^0.12.0+2
  flutter_onnxruntime: ^1.8.3        # android·ios·macos·windows·linux·web 지원 확인
  google_mlkit_text_recognition: ^0.17.1
  opencv_core: ^1.4.5                # 전처리(선택, 성능 병목 시 도입)
  image: ^4.9.2

  # 저장 / 동기화
  drift: ^2.34.3
  drift_flutter: ^0.3.1              # ※ sqlite3_flutter_libs는 EOL → drift_flutter 사용
  supabase_flutter: ^2.17.2
  connectivity_plus: ^7.3.1

  # 헬스 연동
  health: ^13.3.2
  flutter_blue_plus: ^2.3.12         # Phase 4

  # 리포트 / 차트
  fl_chart: ^1.2.0
  pdf: ^3.13.0
  printing: ^5.15.0
  csv: ^8.0.0
  share_plus: ^13.3.0

  # 인증 / 보안 / 기타
  google_sign_in: ^7.2.0
  sign_in_with_apple: ^8.1.0
  flutter_secure_storage: ^11.0.0
  permission_handler: ^13.0.1
  path_provider: ^2.1.6
  flutter_local_notifications: ^22.3.0
  timezone: ^0.11.1
  flutter_timezone: ^5.1.0
  intl: ^0.20.3
  uuid: ^4.6.0
  sentry_flutter: ^9.27.0            # PII 스크러빙 필수 설정

dev_dependencies:
  flutter_test: {sdk: flutter}
  integration_test: {sdk: flutter}
  build_runner: ^2.16.0
  riverpod_generator: ^4.0.8
  drift_dev: ^2.34.3
  json_serializable: ^6.14.1
  freezed: ^3.2.5
  flutter_lints: ^6.0.0
  mocktail: ^1.0.5
```

**주의 (W0에 검증)**
- `sqlite3_flutter_libs`는 EOL 표기 → **`drift_flutter`가 네이티브 라이브러리를 포함**하므로 직접 의존하지 않습니다.
- `camera` 0.12.x는 API 변경이 있으므로 `startImageStream` 시그니처를 실기기에서 먼저 확인합니다.
- DB 암호화가 필요하면 `sqlcipher_flutter_libs`도 EOL이므로, **DB 파일은 앱 샌드박스에 두고 민감 키만 `flutter_secure_storage`** 로 관리하는 방식을 기본으로 합니다(§10).

---

## 5. 도메인 모델 · 단위 · 시간 규격

### 5.1 단위 (F-3)

```dart
enum GlucoseUnit { mgdl, mmoll }

const kMgdlPerMmoll = 18.0182;      // 근사치 18 사용 금지 — 왕복 오차 누적

double mmollToMgdl(double v) => v * kMgdlPerMmoll;
double mgdlToMmoll(double v) => v / kMgdlPerMmoll;
```

**저장 규칙 (중요)**
- 정본은 **`value_mgdl` (numeric)** 하나. 모든 계산·통계·동기화는 이 값 기준.
- 동시에 **`entered_unit` + `entered_value` 원본을 함께 보존**합니다. mmol/L로 `7.6`을 입력한 사용자에게 왕복 변환 후 `7.5`를 보여주지 않기 위함입니다. 표시할 때 `entered_unit`이 현재 표시 단위와 같으면 원본을 그대로 씁니다.
- 표시 반올림: mg/dL은 정수, mmol/L은 소수 1자리.

**로케일 기본 단위**: `mmol/L` = GB, CA, AU, NZ, IE, SE, NO, DK, FI, NL, CN, RU 등 / `mg/dL` = US, KR, JP, DE, FR, ES, IT, BR, IN 등. 온보딩에서 자동 선택 후 **반드시 사용자에게 확인**받습니다(단위 오설정은 이 앱에서 가장 위험한 UX 버그).

### 5.2 시간 규격

`measured_at`(UTC, ISO 8601) + `tz_name`(IANA, 예 `Asia/Seoul`) + `utc_offset_minutes`를 함께 저장합니다.
UTC만 저장하면 **여행/서머타임 중 "공복" 태깅과 일별 그래프가 어긋납니다.** 태깅 규칙과 일별 집계는 항상 로컬 시각 기준으로 계산합니다.

### 5.3 스마트 자동 태깅 (F-2)

`TagSuggester`는 부작용 없는 순수 함수로 구현하고 100% 유닛테스트합니다.

| 조건 (로컬 시각 기준) | 추천 태그 |
|---|---|
| 04:00–10:00 && 직전 8시간 내 식사 기록 없음 | `fasting` |
| 식사 기록 후 60–150분 | `postMeal` |
| **예정된** 식사 시각까지 30분 이내 | `preMeal` |
| 운동 기록 후 0–120분 | `postExercise` |
| 21:00–03:00 | `bedtime` |
| 그 외 | 직전 태그 → 없으면 `random` |

추천은 **선택 칩(chip)이 미리 선택된 상태**로 노출하고, 사용자가 1탭으로 바꿀 수 있게 합니다. 자동 확정하지 않습니다.

> **식전 규칙 정정**: "식전"은 과거 식사 기록으로 추론할 수 없습니다(먹기 전에는 기록 자체가 없음). 그래서 `TagContext.nextScheduledMealAt`(사용자가 설정한 식사 알림 시각)을 별도 입력으로 받고, 그 정보가 없으면 식전을 추천하지 않습니다.

### 5.4 eA1c (F-5)

ADAG 공식: `A1c(%) = (평균혈당[mg/dL] + 46.7) / 28.7`

**표시 조건 (미달 시 숨김 + 사유 안내)**: 최근 14일 중 측정일 10일 이상 && 총 측정 20회 이상. SMBG는 측정 시점 편향(식후만 측정 등)이 크므로, 표시 시 항상 `추정치` 배지 + "실제 당화혈색소 검사를 대체하지 않습니다" 문구를 붙입니다.

---

## 6. 로컬 DB 스키마 (Drift)

```dart
class GlucoseReadings extends Table {
  TextColumn get id => text()();                          // uuid v4 (클라이언트 생성)
  DateTimeColumn get measuredAtUtc => dateTime()();
  TextColumn get tzName => text()();
  IntColumn get utcOffsetMinutes => integer()();
  RealColumn get valueMgdl => real()();
  TextColumn get enteredUnit => textEnum<GlucoseUnit>()();
  RealColumn get enteredValue => real()();
  TextColumn get tag => textEnum<MeasurementTag>()();
  TextColumn get source => textEnum<ReadingSource>()();
  TextColumn get ocrEngineId => text().nullable()();
  RealColumn get ocrConfidence => real().nullable()();
  TextColumn get ocrRawText => text().nullable()();
  TextColumn get photoPath => text().nullable()();        // 로컬 전용, 업로드 안 함
  TextColumn get note => text().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();
  DateTimeColumn get deletedAt => dateTime().nullable()(); // 소프트 삭제
  IntColumn get syncState => intEnum<SyncState>()();       // pending/synced/conflict
  @override Set<Column> get primaryKey => {id};
}

class SyncOutbox extends Table {
  IntColumn get seq => integer().autoIncrement()();
  TextColumn get entity => text()();      // 'glucose_readings'
  TextColumn get entityId => text()();
  TextColumn get op => text()();          // upsert / delete
  TextColumn get payload => text()();     // JSON
  DateTimeColumn get createdAt => dateTime()();
  IntColumn get attempts => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();
}
```

인덱스: `(measuredAtUtc DESC)`, `(syncState)`, `(deletedAt)`.
**id는 클라이언트가 uuid로 생성**합니다 → 오프라인 생성 레코드가 서버 왕복 없이 즉시 정체성을 가집니다(동기화 설계의 전제).

---

## 7. Supabase 설계

### 7.1 스키마 (`supabase/migrations/0001_init.sql`)

```sql
create type glucose_unit as enum ('mgdl','mmoll');
create type measurement_tag as enum
  ('fasting','pre_meal','post_meal','post_exercise','bedtime','random');
create type reading_source as enum ('ocr','manual','ble','health_sync','import');

create table public.glucose_readings (
  id                  uuid primary key,
  user_id             uuid not null references auth.users(id) on delete cascade,
  measured_at         timestamptz not null,
  tz_name             text not null,
  utc_offset_minutes  int  not null,
  value_mgdl          numeric(6,2) not null check (value_mgdl between 10 and 900),
  entered_unit        glucose_unit not null,
  entered_value       numeric(8,3) not null,
  tag                 measurement_tag not null default 'random',
  source              reading_source  not null default 'ocr',
  ocr_engine_id       text,
  ocr_confidence      real,
  note                text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  deleted_at          timestamptz
);

alter table public.glucose_readings enable row level security;

create policy "owner_all" on public.glucose_readings
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create index on public.glucose_readings (user_id, measured_at desc);
create index on public.glucose_readings (user_id, updated_at);   -- 델타 pull용
```

`updated_at` 자동 갱신 트리거(`before update ... execute function touch_updated_at()`)를 함께 둡니다.

**주의**: OCR 원문(`ocr_raw_text`)과 식사 사진은 **서버로 올리지 않습니다.** 로컬에만 보관합니다(수집 최소화 원칙, §10).

**GDPR 완전 삭제**: 소프트 삭제(`deleted_at`)는 동기화용일 뿐입니다. 계정 탈퇴 시 Edge Function이 hard delete + `auth.users` 삭제를 수행하고 완료 시각을 감사 로그에 남깁니다.

### 7.2 오프라인 우선 동기화

```
[로컬 쓰기]  Drift 트랜잭션 { readings upsert + outbox insert }   ← 원자적
                        │
[Push]  온라인 && 로그인 → outbox 배치 200건 → supabase.upsert()
                        │  성공: outbox 삭제 + syncState=synced
                        │  실패: attempts++, 지수 백오프(최대 6회), 이후 사용자 알림
[Pull]  supabase.select().gt('updated_at', lastPulledAt).order('updated_at')
                        │  커서(lastPulledAt)를 secure storage에 보관
[충돌]  Last-Write-Wins (updated_at 비교), 동률이면 로컬 우선
```

혈당 기록은 사실상 append-only라 충돌이 드뭅니다. LWW로 충분하며, CRDT 같은 과설계는 하지 않습니다.

**익명 → 계정 전환**: Supabase 익명 로그인으로 시작해 `user_id`를 처음부터 부여합니다. 나중에 Google/Apple 계정을 연결(link)하면 기존 데이터가 그대로 승계됩니다. "가입 없이 바로 스캔"과 "다기기 동기화"를 동시에 만족시키는 방법입니다.

**인증**: Google Sign-In / Sign in with Apple(iOS 필수) → Supabase OAuth. **FIDO2 패스키는 Phase 4 이후**로 미룹니다(Supabase 측 지원 상태를 그때 재확인).

---

## 8. 기능별 구현 상세

### F-1 카메라 OCR 스캐너
- `camera` 패키지로 `ResolutionPreset.high` + `startImageStream`. Android는 YUV420, iOS는 BGRA8888 → 포맷 차이는 `OcrFrame.format`이 흡수.
- 가이드 박스: 화면 중앙 고정 비율(혈당기 LCD 종횡비 ≈ 2:1). 박스 밖은 딤 처리.
- 인식 상태 3단계 UI: `탐색 중`(회색 테두리) → `읽는 중`(파란 테두리 + 후보값 흐리게) → `확정`(초록 테두리 + 햅틱 + 확인 시트).
- 3초간 미확정 시 "수동 입력" 버튼을 시트 상단으로 승격.
- 촬영 사진은 기본 저장하지 않음(설정에서 켤 수 있으며 로컬 전용).

### F-4 헬스 연동
- `health` 13.3.2, 타입 `HealthDataType.BLOOD_GLUCOSE`.
- **Android Health Connect 함정 (일정에 여유 필요)**: `AndroidManifest.xml` 권한 선언 + 권한 설명 액티비티(`ACTION_SHOW_PERMISSIONS_RATIONALE` 인텐트 필터) + **Google Play Console의 헬스 데이터 접근 선언 심사**. 심사에 실무상 1~3주가 걸리므로 베타 제출 3주 전에 착수합니다.
- 동기화 방향: 기본 **앱 → OS 단방향(write)**. OS → 앱 읽기는 중복 레코드 위험이 있어 사용자가 명시적으로 켜야 하며, `source`를 `health_sync`로 구분하고 중복 제거 키(측정시각 ±2분 && 동일 값)를 적용합니다.

### F-4b BLE (Phase 4, 백로그)
Bluetooth SIG Glucose Service `0x1808` / Measurement `0x2A18` / RACP `0x2A52`. Measurement는 **SFLOAT(IEEE-11073 16bit)** 디코딩이 필요하고 단위 플래그(kg/L vs mol/L)를 반드시 해석해야 합니다. 페어링·본딩 처리 포함 최소 2주.

### F-5 리포트
- PDF: `pdf` + `printing`. **CJK/키릴 폰트를 반드시 임베딩**(Noto Sans KR/JP/SC)해야 한글·일본어 리포트에서 글자가 깨지지 않습니다. 에셋이 커지므로 필요한 폰트만 지연 로드.
- 리포트 구성: 기간 요약(평균/최고/최저/측정횟수) · eA1c · 태그별 평균 표 · 일별 추이 그래프 · 전체 기록 표 · 하단 고정 의료 면책 문구.
- CSV: RFC 4180, UTF-8 **BOM 포함**(Excel 호환). 컬럼: `measured_at_iso8601, tz, value, unit, value_mgdl, tag, source, note`.

---

## 9. UI/IA 및 국제화

- **IA**: 하단 탭 4개 — 홈(대시보드) / 기록 / 통계 / 설정. 스캔은 홈의 중앙 FAB(어디서든 2탭 이내 도달).
- **텍스트 확장 대응**: 독일어·스페인어는 영문 대비 20~40% 길어집니다. 버튼 라벨에 고정 width 금지, `Text`는 가능한 한 줄바꿈을 허용하고 말줄임은 최후 수단으로만 씁니다. 최초 5개 언어: en, ko, de, es, ja.
- **의사 로케일 테스트**: `flutter run --dart-define=PSEUDO_LOC=true`로 모든 문자열을 40% 늘려 렌더해 레이아웃 깨짐을 조기 발견합니다.
- **다크 모드**: Material 3 `ColorScheme.fromSeed` 기반 라이트/다크 동시 정의. 스캔 화면은 카메라 프리뷰 특성상 항상 다크 계열 오버레이.
- **접근성**: 혈당 수치 텍스트 최소 대비 4.5:1, 동적 폰트 200%까지 레이아웃 유지, 모든 아이콘 버튼에 semanticLabel.

---

## 10. 보안 · 컴플라이언스 체크리스트

| 항목 | 조치 | 시점 |
|---|---|---|
| 데이터 수집 최소화 | 사진·OCR 원문·정밀 위치는 **서버 미전송** | 설계 시 |
| 전송 보안 | TLS 1.3 (Supabase 기본), 릴리스 빌드에서 cleartext 트래픽 차단 | W9 |
| 저장 보안 | DB는 앱 샌드박스, 토큰/동기화 커서는 `flutter_secure_storage`(Keystore/Keychain) | W9 |
| 인증 | Google / Apple OAuth. 앱 자체 비밀번호 저장 없음 | W9 |
| GDPR/CCPA | 데이터 내보내기(CSV/JSON) + 계정 즉시 삭제(Edge Function hard delete) + 처리 목적 고지 | W16 |
| 동의 | 온보딩에서 헬스데이터 처리 동의를 **분리 동의**로 수집(일괄 동의 금지) | W16 |
| 크래시 리포팅 | Sentry `beforeSend`에서 혈당값·이메일 스크러빙, PII 전송 비활성 | W9 |
| **SaMD 회피** | 인슐린 용량 계산·진단·치료 권고 기능 **금지**. "정상/위험" 같은 진단성 문구 대신 "목표 범위 내/밖" 같은 서술적 표현만 사용 | 상시 |
| 의료 면책 | 온보딩·리포트 하단·설정에 상시 노출 | W16 |
| 스토어 심사 | Apple 가이드라인 1.4.1(의료 앱 정확성), Google Play 건강 앱 정책 및 Health Connect 데이터 선언 | W16~17 |

> **SaMD 관련 실무 주의**: "General Wellness"는 문구 하나로 확보되지 않습니다. **기능이 치료 결정을 유도하는 순간** 분류가 바뀝니다. 예를 들어 "혈당이 높으니 ○○하세요" 같은 액션 권고는 넣지 않습니다. 이 원칙을 기능 백로그 리뷰 체크리스트에 고정 항목으로 넣습니다.

---

## 11. 테스트 전략

| 계층 | 대상 | 도구 |
|---|---|---|
| 유닛 (커버리지 90%+) | `TagSuggester`, `Ea1cCalculator`, 단위 변환(왕복 오차), `GlucoseValidator`, `ReadingNormalizer`, `ReadingStabilizer`, `ConflictResolver` | `flutter_test` |
| 모듈 경계 | `GlucoseScanner` 가 앱에 넘기는 `ScanOutcome` 만으로 계약 검증 — 앱이 결과를 믿어도 되는지 | `flutter_test` |
| 골든 벤치마크 | OCR 엔진 정확도/지연 (§2.6) | `tools/ocr_bench` + CI |
| 위젯 | 확인 시트, 태그 칩, 단위 전환, 의사 로케일 레이아웃 | `flutter_test` |
| 통합 | 스캔 → 저장 → 동기화 → 리포트 전 경로 (엔진은 `FakeOcrEngine`으로 대체) | `integration_test` |
| 수동 | 실기기 3종 × 혈당기 5종 × 조명 3종 매트릭스 | 체크리스트 |

`FakeOcrEngine`은 `OcrEngine`을 구현해 지정된 값을 지정된 지연 후 반환합니다 — 플러그인 구조가 테스트에서도 바로 이득을 냅니다.

---

## 12. 로드맵 (1인 풀타임 기준, 주 단위)

### Phase 1 — OCR 코어 검증 (W1~W7) ★ 최대 리스크 구간

| 주 | 산출물 |
|---|---|
| W1 | `flutter create` + 프로젝트 골격 + Riverpod/go_router/테마. `OcrEngine` 인터페이스·레지스트리·`ManualEngine` 완성. **실촬 데이터 수집 개시(상시)**. 라이선스 검토 문서화 |
| W2 | 카메라 프리뷰 + 가이드 박스 + 프레임 스로틀러 + 전처리. `RemoteDebugEngine`(EasyOCR FastAPI) 연결 → **baseline 정확도 측정**. 골든셋 300장 라벨링 |
| W3 | `tools/ocr_bench` 하네스 완성. `MlKitEngine` 붙여 비교군 확보. 합성 데이터 생성 파이프라인 |
| W4 | EasyOCR recognizer ONNX export → `flutter_onnxruntime` 온디바이스 추론 성공(정확도 무관, **동작 확인이 목표**) + CTC 디코더 |
| W5 | 7-세그먼트 fine-tune 1차. 골든셋 800장으로 확장. `Stabilizer` 구현 및 튜닝 |
| W6 | fine-tune 2차 + 문자집합 축소 + 양자화. 성능 최적화(isolate, 입력 크기) |
| W7 | **승격 게이트 판정(§2.7)**. 미달 시 플랜 B(소형 CNN 분류기) 전환 결정 |

> **W7 게이트가 이 프로젝트의 진짜 마일스톤입니다.** 여기를 통과하지 못하면 이후 일정 전체가 무의미하므로, W7까지는 다른 기능에 손대지 않습니다.

### Phase 2 — 기록 · 동기화 (W8~W12)

| 주 | 산출물 |
|---|---|
| W8 | Drift 스키마 + DAO + 확인 시트 + `TagSuggester` + 기록 목록/편집/삭제 |
| W9 | Supabase 프로젝트(EU 리전) + 스키마/RLS + 익명 로그인 + Google/Apple OAuth + secure storage |
| W10 | 동기화 엔진(outbox push + 델타 pull + LWW) + 오프라인/충돌 시나리오 테스트 |
| W11 | 대시보드(최근 수치 카드, 추이 그래프) + 단위 변환 시스템(F-3) + 온보딩 |
| W12 | 통계 화면(태그별 필터·TIR·평균) + eA1c |

### Phase 3 — 연동 · 리포트 · 글로벌화 (W13~W18)

| 주 | 산출물 |
|---|---|
| W13 | Health Connect 연동 + 권한 UX. **Play Console 헬스데이터 선언 제출(리드타임 확보)** |
| W14 | PDF/CSV 리포트(CJK 폰트 임베딩 포함) + 공유 |
| W15 | i18n 5개 언어 + 의사 로케일 레이아웃 수정 + 다크모드 + 접근성 |
| W16 | 식후 알림(local notification) + 컴플라이언스(면책·동의·데이터 내보내기·계정 삭제) |
| W17 | 안정화: 크래시 수정, 성능 프로파일링, Sentry PII 스크러빙, 스토어 자산(스크린샷·설명 5개 언어) |
| W18 | **Android 클로즈드 베타 출시** (Play Console 내부 테스트 → 공개 테스트) |

### Phase 4 — iOS 및 확장 (W19~W26)

| 주 | 산출물 |
|---|---|
| W19~20 | iOS 카메라 프레임(BGRA) 대응 + ONNX iOS 검증 + 실기기 성능 튜닝 |
| W21 | HealthKit 연동 + Sign in with Apple + 권한 문구 |
| W22 | iOS UI 대응(SafeArea, 다이내믹 아일랜드, 제스처) + TestFlight |
| W23 | App Store 심사 대응(1.4.1 의료 정확성 소명 자료) → **iOS 출시** |
| W24~26 | 베타 피드백 반영 · BLE Glucose Profile(F-4b) · 게이미피케이션(스트릭/배지) |

**요약**: Android 베타 ≈ 4.5개월(W18), iOS 포함 정식 ≈ 6개월(W23). PRD의 9개월보다 앞서지만, 이는 **BLE·게이미피케이션·패스키를 Phase 4 이후로 미룬 결과**이며 W7 OCR 게이트 통과를 전제로 합니다.

---

## 13. 리스크 레지스터

| # | 리스크 | 영향 | 완화책 |
|---|---|---|---|
| R-1 | **7-세그먼트 OCR 정확도 미달** | 치명적 (제품 존재 이유) | W7 게이트로 조기 판정 · 플러그인 구조로 엔진 즉시 교체 · 플랜 B(소형 CNN) 준비 · 실촬 데이터 상시 수집 |
| R-2 | LCD 반사·저대비로 특정 기기에서 실패 | 높음 | 벤치마크를 기기별로 분해 · 문제 기기용 전처리 프로파일 · 실패 시 수동 입력 1탭 |
| R-3 | 중저가 Android에서 프레임 지연 | 중 | in-flight 1 스로틀링 · 양자화 · 해상도 하향 · 저사양 감지 시 단발 촬영 모드 |
| R-4 | Play Console 헬스데이터 선언 심사 지연 | 중 | W13에 조기 제출 · 미승인 시 Health Connect 없이 베타 선출시 |
| R-5 | App Store 의료 앱 심사 반려 | 중 | 진단성 문구 전면 배제 · 면책 상시 노출 · 소명 자료 사전 준비 |
| R-6 | 모델/폰트 라이선스 문제 | 중 | W1에 `docs/LICENSES.md` 작성 · 상업 사용 불가 자산 사용 금지 |
| R-7 | 단위 오설정으로 인한 수치 오해 | 높음 | 온보딩 명시적 확인 · 설정 변경 시 경고 · 리포트에 단위 항상 병기 |
| R-8 | 1인 개발 번아웃 / 일정 지연 | 중 | Phase 경계에서 백로그 재협상 · BLE·게이미피케이션은 언제든 잘라낼 수 있게 의존성 분리 |

---

## 14. Week 0 착수 체크리스트

```bash
flutter create --org com.sugarscan --project-name sugarscan --platforms=android,ios .
```

1. 위 명령으로 현재 디렉터리에 프로젝트 생성
2. `pubspec.yaml`에 §4 의존성 반영 후 `flutter pub get` — 버전 충돌 즉시 확인
3. `analysis_options.yaml`에 `flutter_lints` + `prefer_relative_imports` 등 규칙 강화
4. `docs/LICENSES.md` 작성 (easyocr / CRAFT / DSEG 폰트 / Noto 폰트)
5. Supabase 프로젝트 생성 — **리전은 EU (Frankfurt)** 로 지정
6. 실촬 데이터 수집 시작: 보유 혈당기로 조명·각도 조합 촬영 (하루 20장 목표)
7. `tools/easyocr_server/` FastAPI 도커 구성 → 라벨링 반자동화
8. Git 저장소 초기화(현재 이 디렉터리는 git repo가 아님) + `.gitignore`에 `assets_dev/`, `*.onnx`, `*.pth` 추가 (모델·데이터는 Git LFS 또는 별도 스토리지)

---

## 15. 구현 로그

### W1 (2026-08-20) — 프로젝트 골격

`flutter create` ~ 도메인·OCR 인터페이스 계층 완료. `flutter analyze` 무경고,
유닛/위젯 테스트 **93개 전부 통과**(재구조화 이후 기준).

**의존성 해결에서 나온 제약 3건** — Flutter 3.44.7 SDK 가 `meta 1.18.0`,
`test_api 0.7.11`, `matcher 0.12.19` 를 고정하는 데서 모두 파생됐다.

| 계획 | 실제 | 이유 |
|---|---|---|
| `intl: ^0.20.3` | `intl: 0.20.2` (정확히 고정) | `flutter_localizations` 가 0.20.2 를 못 박음 |
| `build_runner: ^2.16.0` | `build_runner: ^2.4.0` (2.15.1 해결) | 2.15.2+ 는 `analyzer >=13.3` → `meta ^1.18.3` 요구 |
| `drift_dev: ^2.34.5` | `drift_dev: ^2.34.0` (2.34.0 해결) | 2.34.1+1 부터 `analyzer ^13` 요구 |

**Riverpod 코드 생성을 뺐다.** `riverpod_generator` 는 4.0.6 미만이 `analyzer ≤12`,
4.0.6 이상이 `analyzer ^13` 을 요구해 `drift_dev` 와 어느 쪽으로도 공존하지
못한다. Drift 코드젠은 대체 불가지만 Riverpod 코드젠은 편의 기능이라, **프로바이더는
수동으로 작성**하기로 했다. analyzer 생태계가 정리되면 재도입한다.

목표 목록에서 뺀 패키지: `opencv_core`(전처리 성능 병목이 실측될 때 도입),
`flutter_blue_plus`(Phase 4), `sentry_flutter`(W9), `freezed`/`json_serializable`
(코드젠 부담 대비 이득이 작아 평범한 클래스로 작성).

### 구현 중 발견한 안전 이슈: `LO` → `10` 오독

7-세그먼트 글자 교정(`L→1`, `O→0`)을 문자열 전체에 적용하면, 혈당계가 저혈당을
알리는 `LO` 표시가 **`10` 이라는 값으로 둔갑**한다. 사용자가 실제로는 위험한
저혈당 상태인데 앱에는 평범한 숫자가 남는다. 같은 이유로 `mg/dL` 의 D·L 이
교정되어 `138 mg/dL` 이 `13801` 이 되는 버그도 함께 있었다.

→ `GlucoseValidator` 의 처리 순서를 **① 단위 표기 제거 → ② `HI`/`LO` 판정 →
③ 글자 교정** 으로 고정하고, `meterRangeIndicator` 실패 종류를 별도로 두었다.
회귀 테스트로 고정해 둠.

### W1-b — OCR 모듈 격리로 재구조화

초기 구현은 검증(`GlucoseValidator`)과 안정화(`Stabilizer`)를 OCR **바깥**에 두어
앱이 OCR 결과를 판정하는 구조였다. 이를 뒤집어 **보정까지 끝난 값만 앱으로
넘기는** 구조로 바꿨다.

| | 이전 | 이후 |
|---|---|---|
| 앱이 받는 것 | `OcrResult`(후보 문자열 + 확신도) | `ScanOutcome`(확정된 `double` + 단위 + 정본 mg/dL) |
| 보정 위치 | 앱 쪽 파이프라인 | 모듈 내부 `ReadingNormalizer` |
| 검증 위치 | 앱 쪽 파이프라인 | 모듈이 `domain` 규칙을 내부에서 호출 |
| 공개 타입 | 엔진·레지스트리·안정화기 전부 | `GlucoseScanner`, `ScanOutcome`, `OcrFrame` 뿐 |
| 네트워크 엔진 | `allowNetworkEngines` 플래그로 조건부 허용 | **항상 등록 거부** (플래그 삭제) |
| 수동 입력 | `ManualEngine`(가짜 엔진) | 엔진이 아님. `ScanUnavailable` 신호 → 앱이 안내 |

`lib/ocr/src/` 로 내부를 감추고 배럴 두 개만 남겼다 — 앱용 `ocr.dart`, 테스트용
`testing.dart`. 앱 코드가 `src/` 를 import하면 그건 경계를 넘은 것이다.

`GlucoseScanner.offer()` 는 **절대 예외를 던지지 않는다.** 앱이 이 모듈을
신뢰하는 구조인 이상, 그 신뢰가 엔진 구현의 성실함에 의존해서는 안 되므로
엔진 호출을 try/catch 로 감싸 `ScanUnavailable(engineError)` 로 변환한다.

### W1-c — 7-세그먼트 CNN 엔진 부착

GitHub에서 **[Kazuhito00/7segment-display-reader](https://github.com/Kazuhito00/7segment-display-reader)** (Apache-2.0)의 사전학습 TFLite 모델을 첫 실엔진으로 붙였다.

| | |
|---|---|
| 모델 | `7seg_classifier.tflite`, 596 KB |
| 입력 | `[1, 96, 96, 3]` float32 RGB, 0~1 정규화 |
| 출력 | 클래스 0~9 + "표시 없음" |
| 방식 | ROI 를 자릿수만큼 등분 → 셀별 분류 → 결합 |
| 학습 데이터 | OpenCV 로 그린 합성 이미지 48,000장 |

**"표시 없음" 클래스가 앞자리 공백 문제를 그대로 해결한다.** 혈당계는 95 를
`  95` 처럼 앞자리를 비워 표시하는데, 이 클래스 덕분에 별도 처리 없이 빈 셀이
걸러진다.

**이 모델이 강제한 아키텍처 변경 2건**

1. **`OcrEngineDescriptor.supportedUnits` 추가.** 이 모델에는 소수점 클래스가
   없어서 mmol/L 의 `7.6` 을 `76` 으로 읽는다. **10배 어긋난 값이 정상 범위
   안에 들어앉기 때문에 검증기도 안정화기도 이 오류를 잡지 못한다.** 그래서
   엔진이 지원 단위를 선언하고, 스캐너가 `start()` 에서 걸러
   `ScanUnavailable(unitNotSupported)` 를 낸다. 잘못 읽느니 수동 입력으로 보낸다.
2. **`OcrEngine.isReady` 추가.** 모델 에셋이 없는 빌드에서도 엔진 객체는
   만들어진다. 이걸 첫 프레임에서야 알면 사용자는 반응 없는 스캐너를 들여다보게
   되므로, `start()` 시점에 확인해 곧바로 `modelUnavailable` 을 낸다.

**신뢰도는 가장 약한 자리를 따른다.** 평균을 쓰면 한 자리가 흔들려도 나머지가
가려 주는데, 혈당값은 자리 하나가 틀리면 값 자체가 달라진다(95 vs 195).

**설계상 유의점**
- TFLite 런타임은 `DigitClassifier` 인터페이스 뒤에 숨겼다. 덕분에 셀 분할·자릿수
  결합·신뢰도 산출을 **실제 모델 파일 없이** 유닛테스트한다(14개 케이스).
- 합성 데이터로만 학습된 모델이라 실촬 사진(반사·기울기·저대비)에서는 성능이
  떨어질 가능성이 높다. **정본 후보가 아니라 벤치마크 기준선**으로 본다.
  W7 게이트 판정은 골든셋 실측으로 한다.
- 저장소가 2021년 이후 갱신되지 않았다. `.tflite` 는 고정된 가중치 파일이라
  유지보수 부재 자체가 위험은 아니지만, 업스트림 개선은 기대할 수 없다.
- 현재 카메라 프레임 포맷(YUV)은 아직 지원하지 않는다(`unsupportedFormat`).
  W2 전처리 파이프라인에서 연결한다.

### W1-d — 규칙 기반 7-세그먼트 판독기 (기본 엔진)

학습 모델 없이 동작하는 판독기를 직접 구현했다. **이 엔진이 기본 엔진이 되고,
CNN 은 비교군으로 내려간다.**

**왜 모델이 필요 없는가.** 7-세그먼트는 표현 가능한 상태가 2⁷=128가지뿐이고
각 숫자의 구조가 명시적이다. "이 그림이 7인가"를 학습할 필요 없이
`획 7개의 켜짐 여부 → 7비트 → 대응표` 로 결정된다.

| 단계 | 구현 |
|---|---|
| 이진화 | Otsu + **극성 자동 판정**(면적이 적은 쪽이 전경) |
| 샘플링 | 세그먼트마다 점이 아닌 **영역**의 전경 픽셀 비율 |
| 매칭 | 대응표 + 해밍 거리 ≤ 1, 동점이면 판독 포기 |
| 소수점 | 셀 우하단 별도 영역을 독립 검출 |
| 조립 | 셀별 판독 → `98` / `102.5` / `LO` / `HI` |
| 품질 게이트 | 라플라시안 분산(초점) + Otsu 분리도(대비) |

**CNN 대비 실질적 이점 3가지**

1. **소수점을 읽는다.** 별도 영역을 따로 재므로 `102.5` 와 `1025` 를 구분한다.
   덕분에 **mmol/L 을 지원**한다 — CNN 엔진이 못 하는 일이다.
2. **모르는 것을 모른다고 말한다.** 해밍 거리와 동점 여부로 판독 불가를 명시적으로
   판정한다. 분류기는 언제나 가장 그럴듯한 클래스를 내놓는다.
3. 학습 데이터도, 모델 에셋도, 재학습 파이프라인도, 네이티브 런타임도 없다.

**`LO` 가 `10` 이 되지 않게 하는 방법.** `O` 와 `I` 는 각각 `0`, `1` 과 세그먼트
패턴이 **완전히 같다**. 반면 `L`(DEF)과 `H`(BCEFG)는 어떤 숫자와도 겹치지 않는다.
그래서 L·H 를 닻으로 삼아 표시 **전체**를 `LO`/`HI` 로 판정한다. 자리별로만 보면
저혈당 경고가 조용히 `10` 이라는 평범한 숫자가 된다.

**해밍 거리를 1 로 묶은 실측 근거.** 구현 중 확인한 사실 — 두 획이 손상되면
다른 글자로 **정확히 일치**해 버리는 경우가 흔하다.

```
8(1111111) − A,D  →  0110111 = H   (거리 0 으로 일치)
8(1111111) − B,E  →  1011011 = 5   (거리 0 으로 일치)
```

거리 2 까지 허용하면 이건 "복구"가 아니라 조용한 오독이 된다. 1 로 묶고, 그
이상 망가진 프레임은 읽지 않는다.

**검증 방식.** 디코더와 같은 기하 정의를 공유하되 **샘플 영역보다 넓은 실제 획**을
그리는 합성 렌더러를 만들어 사진 없이 전 구간을 돌린다. 0~9 전부, 소수점,
`LO`/`HI`, 백라이트(극성 반전), 초점 흐림 거부까지 커버한다. 실촬 정확도는
여기서 알 수 없으므로 골든셋으로 따로 측정한다.

**순수 Dart 로 간 이유.** ROI 가 480×160(7.7만 픽셀) 규모라 Dart 로도 5~10fps 는
충분하고, `flutter test` 에서 알고리즘 전체가 돌아간다. C++/FFI 는 OpenCV 바이너리,
NDK/CMake, iOS podspec 비용을 지금 치를 이유가 없다. 프로파일링에서 병목이
확인되면 같은 `OcrEngine` 인터페이스 뒤에서 네이티브로 교체한다 — 앱은 영향받지 않는다.

**미구현 (계획된 순서)**
- 원근 보정: 현재는 정면 촬영 가정. 비스듬히 찍으면 셀 경계가 어긋난다.
- 자동 LCD 검출: 사용자가 가이드 박스에 맞추는 전제.
- CLAHE / 다중 임계값 후보: Otsu 단일 임계값으로 시작.
- 기종별 `MeterProfile`: 현재는 균등 분할 기본 프로파일만.

**참고 구현** (알고리즘만 참고, 코드 미사용): [SSOCR](https://github.com/jiweibo/SSOCR)(GPL-3.0),
[SegoDec](https://github.com/scottmudge/SegoDec), [seven-segment-ocr](https://github.com/suyashkumar/seven-segment-ocr).
SSOCR 은 GPL-3.0 이라 상용 앱에 코드를 가져올 수 없어 자체 구현했다.

### W2 — 카메라 → 스캐너 연결, 확인 시트

라이브 카메라 프레임이 OCR 모듈로 들어가고 확정값이 확인 시트를 거쳐 나온다.
테스트 176개 통과.

**YUV 변환이 공짜였다.** Android 카메라의 YUV420 프레임에서 **Y 평면이 곧
휘도**다. 색을 버리는 손실 변환이 아니라, 7-세그먼트 판독이 필요로 하는 바로
그 값을 그대로 얻는다. UV 평면은 읽지도 않으므로 프레임당 복사량이 3분의 1로
줄어든다. RGB 변환 비용을 걱정했는데 애초에 치를 필요가 없는 비용이었다.

**로우 스트라이드가 진짜 함정이다.** 카메라는 정렬을 위해 각 행 끝에 패딩을
넣는다. 이걸 무시하고 `width` 만큼 읽으면 행이 조금씩 밀려 화면이 비스듬히
기울어 보이고 세그먼트 샘플 영역이 통째로 어긋난다. 실기기에서 "왜 인식이
안 되지"로 며칠 잡아먹기 좋은 버그라, 변환기를 플러그인 타입에서 떼어내
`CameraFrameConverter` 로 만들고 회전(0/90/180/270)까지 포함해 16개 테스트로
고정했다.

| 파일 | 역할 |
|---|---|
| `camera_frame_converter.dart` | 순수 함수. Y 평면 추출·스트라이드 제거·회전 |
| `camera_image_adapter.dart` | `package:camera` 를 아는 **유일한** 파일 |
| `scan_screen.dart` | 프리뷰 + 가이드 박스 + 상태 표시 |
| `confirm_sheet.dart` | 값 확인·±보정·태그 선택 |
| `scan_entry.dart` | 확인된 기록. W8 에 `GlucoseReading.fromEntry` 입력이 된다 |

**화면은 판정하지 않는다.** `scan_screen` 이 하는 일은 프레임을 밀어 넣고 돌아온
`ScanOutcome` 을 그리는 것뿐이다. 유량 제어조차 스캐너가 하므로 화면은 프레임이
버려졌는지도 모른다.

**테스트가 드러낸 제품 결함: 카메라 무한 대기.** 스모크 테스트가
`pumpAndSettle` 에서 멈췄다. 원인은 카메라 초기화가 응답하지 않을 때 진행
표시기가 영원히 도는 것 — 테스트 환경만의 문제가 아니라 **실기기에서 카메라
서비스가 응답하지 않으면 사용자가 도는 표시기만 보게 되는** 결함이었다.
준비 단계에 6초 타임아웃을 넣고, 넘기면 수동 입력으로 안내한다.

**확인 시트에 남긴 신호 하나**: `ScanEntry.adjustedByUser`. 사용자가 인식값을
손으로 고친 비율은 엔진이 어느 기종에서 틀리고 있는지 알려주는 가장 값싼
지표다. 골든셋을 늘려야 할 곳을 가리킨다.

**권한 고지**: iOS `NSCameraUsageDescription` 추가("이 기기에서 처리하며 업로드하지
않는다"를 명시). Android 는 카메라 플러그인이 매니페스트를 병합한다.

**W2 잔여 과제**
- **가이드 박스와 ROI 정렬**: 프리뷰와 오버레이를 같은 `AspectRatio` 상자에
  겹쳐 그렸지만, 센서 종횡비·회전 보정 때문에 완전히 일치한다고 단정할 수 없다.
  **실기기에서 눈으로 맞춰야 한다.**
- 수동 입력 화면(현재는 화면을 닫기만 한다) — W8
- 저장(현재는 스낵바로 확인만) — W8

### W8 — 로컬 저장, 기록 목록, 직접 입력

스캔·직접 입력이 실제로 저장되고 목록에서 보인다. 테스트 193개 통과.

| 파일 | 역할 |
|---|---|
| `data/local/tables.dart` | 기록 + 아웃박스 테이블 |
| `data/local/converters.dart` | enum 을 **wireName 으로** 저장 |
| `data/repositories/glucose_repository.dart` | 저장·수정·삭제·조회, 아웃박스 등록 |
| `features/scan/manual_entry_sheet.dart` | 직접 입력 |
| `features/history/history_screen.dart` | 목록 + 스와이프 삭제 |
| `app/providers.dart` | Riverpod 배선 |

**enum 을 Drift 기본 방식으로 저장하지 않았다.** `textEnum` 은 Dart 식별자
(`preMeal`)를 그대로 쓴다. 그러면 로컬은 `preMeal`, 서버는 `pre_meal` 로 갈라져
매핑이 하나 더 생기고, Dart 쪽 enum 이름을 바꾸는 순간 저장된 데이터가 깨진다.
`TypeConverter` 로 양쪽이 같은 `wireName` 을 쓰게 했다.

**날짜를 정수가 아니라 ISO-8601 문자열로 저장한다.** Drift 기본값인 유닉스 정수
저장은 읽을 때 **로컬 시각** `DateTime` 을 돌려준다. UTC 를 정본으로 삼는다는
규칙이 저장 계층에서 조용히 깨지는 것이라 `storeDateTimeAsText: true` 로 바꿨다.
회귀 테스트로 고정했다.

**기록 저장과 아웃박스 등록은 한 트랜잭션이다.** 둘이 갈라지면 화면에는 보이는데
서버에는 영원히 안 올라가는(또는 그 반대) 기록이 생기고, 그런 불일치는 나중에
재구성할 방법이 없다. W10 동기화 엔진이 이 큐만 보고 동작한다.

**직접 입력은 스캔과 같은 검증기를 쓴다.** 손으로 넣었다고 물리적으로 불가능한
값이 통과하면 통계와 리포트가 조용히 망가진다. 단위가 정수만 쓰면 소수점 키
자체를 막아, 넣은 뒤 거절당하는 대신 애초에 못 넣게 했다.

**호스트에서 실제 SQLite 로 테스트한다.** `NativeDatabase.memory()` 가 Windows
개발 머신에서 동작하는 것을 확인해, 저장소 15개 테스트가 가짜가 아닌 진짜 DB를
상대한다. 화면 테스트도 `databaseProvider` 를 메모리 DB 로 덮어써 플러그인 없이 돈다.

**위젯 테스트에서 배운 것 두 가지**
- `pumpAndSettle` 을 더는 쓸 수 없다. 무한히 도는 진행 표시기(카메라 준비,
  스트림 첫 방출)가 있으면 영원히 정착하지 않는다. 정해진 만큼만 시계를 넘긴다.
- Drift 스트림은 구독이 끊길 때 `Duration.zero` 타이머를 남긴다. 인자 없는
  `pump()` 는 시계를 **전혀** 진전시키지 않아 그 타이머가 실행되지 않는다.
  트리를 테스트 본문 안에서 내리고 짧게라도 시계를 넘겨야 한다.

**W8 잔여 과제**
- 기록 편집 화면(저장소에 `update` 는 있으나 UI 미연결)
- 삭제 되돌리기 — 소프트 삭제라 복구는 가능하지만 삭제 전파(W10)와 함께 다뤄야 한다
- 표시 단위가 아직 로케일 추정값이다. 온보딩 확인은 W11

### W1 산출물

- `lib/ocr/` — `GlucoseScanner` 파사드, `ReadingNormalizer`, `ReadingStabilizer`,
  `FrameThrottler`, 엔진 인터페이스·레지스트리(네트워크 엔진 등록 차단), `FakeOcrEngine`
- `lib/domain/` — 단위 변환, 검증, 태그 추천, eA1c, 통계 (모두 Flutter 비의존)
- `lib/app/` — go_router 셸(4탭 + 전체화면 스캔), 라이트/다크 테마
- `lib/l10n/` — en·ko ARB + 생성 코드, 의료 면책 문구 포함
- `docs/LICENSES.md` — 라이선스 검토 초안(미해결 4건)

**남은 W1 과제**: 실촬 데이터 수집 개시, `tools/easyocr_server/` FastAPI 구성.

---

## 부록 A. 이 계획에서 의도적으로 **하지 않는** 것

- 인슐린 용량 계산기 (SaMD Class II 진입 → 규제 비용)
- 진단·치료 권고 문구 ("정상", "위험", "○○하세요")
- 서버 측 OCR 처리 (온디바이스 원칙 · 프라이버시)
- 식사 사진의 서버 업로드 (수집 최소화)
- CRDT 기반 동기화 (append-only 데이터에 과설계)
- Phase 1~3의 BLE·패스키·게이미피케이션 (Phase 4 이후)

---

*본 문서는 개발 계획서입니다. sugarScan은 일반 건강 관리 보조 도구이며 의학적 진단을 대체하지 않습니다. 치료 결정 시 반드시 전문 의료진과 상담해야 합니다.*
