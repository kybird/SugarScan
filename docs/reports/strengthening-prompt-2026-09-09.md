# 혈당측정기 혈당 수치 인식 시스템 — 상용 수준 인식률 강화 및 CV/CNN 파이프라인 구축

## 0. 역할

당신은 모바일/임베디드 Edge Vision, OCR, 객체검출, 경량 CNN, ONNX Runtime, Android/iOS 모바일 추론 최적화 경험이 있는 Senior Computer Vision Engineer다.

현재 프로젝트는 스마트폰 카메라로 혈당측정기의 LCD 화면을 촬영하고, 화면에 표시된 혈당 수치를 자동 인식하는 것을 목표로 한다.

이 시스템은 단순 OCR 데모가 아니라 실제 사용자 환경에서 동작하는 것을 목표로 한다.

지원해야 하는 현실적인 문제는 다음과 같다.

* 제조사별 혈당측정기 외형 차이
* 세로형 / 가로형 / 슬림 와이드형 / 비정형 폼팩터
* LCD 크기 및 위치 차이
* 숫자 폰트 및 7-segment 형태 차이
* mg/dL / mmol/L 단위
* mmol/L의 소수점
* LO / HI / Error 코드
* 화면 일부 손가림
* 반사광(glare)
* 저조도
* 과노출
* motion blur
* 촬영 각도
* 화면 기울기
* 기기 회전
* LCD 일부가 카메라 프레임에서 잘린 경우
* LCD가 꺼진 경우
* 숫자의 일부 획이 반사광에 의해 가려진 경우
* 아주 작은 소수점이 resize 과정에서 사라지는 문제
* 비슷한 7-segment 패턴의 혼동
* 프레임마다 인식 결과가 달라지는 문제

핵심 목표는 "항상 숫자를 억지로 출력하는 것"이 아니라 다음 세 가지를 동시에 달성하는 것이다.

1. 정상적인 화면에서는 높은 인식률
2. 잘못 읽을 가능성이 높은 상황에서는 잘못된 숫자를 출력하지 않고 UNKNOWN/RETAKE 판정
3. 여러 프레임을 이용할 수 있는 모바일 카메라 환경에서는 temporal consensus를 이용하여 안정적인 최종 결과 도출

---

# 1. 가장 중요한 설계 원칙

## 1.1 일반 OCR에 문제를 맡기지 않는다

이 프로젝트는 일반 문서 OCR 문제가 아니다.

혈당측정기의 LCD는 다음 특성을 갖는다.

* 문자 종류가 제한적
* 숫자 중심
* 7-segment 또는 이에 가까운 폰트
* 소수점이 매우 작음
* 표시 위치가 제한적
* 단위 및 상태 코드의 형태가 제한적

따라서 Tesseract, 일반 Scene Text OCR, 대형 OCR Transformer 등에 전체 문제를 맡기는 구조를 기본값으로 사용하지 않는다.

우선순위는 다음과 같다.

```text
Display ROI Detection
        ↓
Padded Crop
        ↓
Orientation Normalization
        ↓
Glyph Detection / Segmentation
        ↓
Tiny CNN Glyph Classification
        ↓
Sequence Reconstruction
        ↓
Unit / Status Detection
        ↓
Domain Validation
        ↓
Temporal Consensus
        ↓
Final Result or RETAKE
```

일반 OCR은 비교 대상 또는 fallback으로만 검토한다.

---

# 2. Perspective Transform 사용 원칙

LCD의 네 모서리를 keypoint 4개로 정확하게 찾은 다음 perspective transform을 수행하는 구조를 기본 파이프라인으로 채택하지 않는다.

이 방식은 다음 문제에 취약하다.

* 한 점만 잘못 검출되어도 전체 warp가 틀어짐
* glare로 LCD corner가 사라짐
* 손가락으로 corner가 가려짐
* 곡면 LCD
* 비정형 기기
* LCD 외곽선이 명확하지 않은 기기
* 약간의 reflection 때문에 corner 위치가 흔들리는 경우

기본 구조는 다음으로 한다.

```text
Full Camera Frame
        ↓
Display Detector
        ↓
Display BBox
        ↓
Padded BBox Crop
```

padding은 너무 작게 잡지 않는다.

LCD 외곽선과 숫자 주변 문맥을 보존하면서도 불필요한 배경을 과도하게 포함하지 않는 범위를 실험을 통해 결정한다.

Perspective Transform은 필요할 경우 선택적인 보조 경로로만 설계한다.

즉:

```text
Default:
BBox → Padding → Crop

Optional:
BBox → Rotation Correction

Conditional:
BBox → Perspective Correction
```

형태로 구성한다.

---

# 3. 최종 권장 아키텍처

A/B 두 구조만 비교하지 말고 Hybrid 구조를 구현 후보의 기본 아키텍처로 한다.

## Stage 1 — Display Detector

입력:

```text
Camera Frame
```

출력:

```text
display_bbox
display_confidence
```

목표는 LCD 또는 화면 영역을 찾는 것이다.

이 단계에서는 숫자를 읽으려고 하지 않는다.

가능한 경량 detector를 사용한다.

예:

```text
YOLO 계열 lightweight detector
Nano detector
Mobile-friendly detector
anchor-free lightweight detector
```

단, 특정 architecture를 무조건 선택하지 말고 기존 프로젝트의 framework, ONNX 변환성, 모바일 runtime compatibility, 실제 benchmark 결과를 기준으로 결정한다.

---

# 4. Display ROI Padding

검출된 display BBox를 그대로 crop하지 않는다.

다음 처리를 한다.

```text
bbox
→ enlarge / padding
→ crop
→ clip to image boundary
```

padding 비율을 configuration으로 만든다.

예:

```text
padding_x
padding_y
```

를 독립적으로 조절할 수 있게 한다.

이유는 가로형/세로형 기기의 LCD 주변 정보가 다르기 때문이다.

---

# 5. Orientation 처리

전역적으로 이미지 방향을 하나로 가정하지 않는다.

다음 orientation을 지원한다.

```text
0°
90°
180°
270°
```

가능하다면 별도의 lightweight orientation classifier를 사용한다.

다만 orientation classifier가 불필요할 정도로 detector/sequence decoding으로 해결 가능한 경우에는 복잡도를 증가시키지 않는다.

최종 결정은 benchmark 기반으로 한다.

가로형 혈당계가 세로형 이미지로 촬영되는 경우 및 90/180도 회전된 입력도 테스트에 포함한다.

---

# 6. Glyph 인식 구조

숫자를 하나의 전체 문자열로 OCR하는 대신 문자 단위로 해석하는 구조를 우선한다.

기본 후보:

```text
Display ROI
    ↓
Glyph Detector
    ↓
Individual Glyph Crop
    ↓
Tiny CNN Classifier
```

Glyph detector의 목표는 개별 표시 요소의 위치를 찾는 것이다.

초기 클래스는 다음을 고려한다.

```text
digit
dot
minus
status
unit
```

문자 인식은 별도의 Tiny CNN으로 분리하는 것을 우선 검토한다.

---

# 7. Glyph Classifier

Glyph classifier는 가능한 한 작게 만든다.

예상 클래스:

```text
0
1
2
3
4
5
6
7
8
9
E
L
O
H
I
-
unknown
```

필요에 따라 실제 데이터에서 등장하는 문자만 유지할 수 있다.

중요한 점은 "모든 문자를 처음부터 많이 집어넣는 것"이 아니라 실제 혈당측정기 데이터에서 필요한 문자 집합을 분석하여 결정하는 것이다.

7-segment 혼동이 중요한 경우에는 confusion matrix를 반드시 분석한다.

특히 다음 종류의 오류를 별도로 추적한다.

```text
3 ↔ 8
5 ↔ 6
0 ↔ 8
1 ↔ 7
```

단순 accuracy만 보지 말고 class별 precision/recall/confusion matrix를 기록한다.

---

# 8. 소수점(dot)은 특별 취급한다

이 프로젝트에서 가장 중요한 오류 중 하나는 mmol/L의 소수점 유실이다.

예:

```text
5.6
```

이 정상 결과가

```text
56
```

으로 해석되면 매우 큰 오류가 된다.

따라서 dot은 일반 숫자와 동일하게 취급하지 않는다.

반드시 다음을 검증한다.

```text
dot detection recall
dot precision
dot size distribution
dot minimum pixel size
dot confidence
dot-to-digit spatial relationship
```

가능하다면 dot은 별도 detector 또는 segmentation branch로 구현한다.

---

# 9. Sequence Reconstruction

Glyph detection 결과는 반드시 X 좌표를 기준으로 정렬한다.

예:

```text
glyph_1 x=100
dot    x=130
glyph_2 x=155
glyph_3 x=210
```

를 보고 최종 문자열을 재구성한다.

다음 정보를 사용한다.

```text
x-center
y-center
width
height
class
confidence
```

단순히 confidence가 가장 높은 문자만 선택하지 않는다.

공간 구조도 사용한다.

예:

```text
digit → dot → digit
```

은 mmol/L에서 합리적일 수 있지만

```text
dot → digit
```

등 비정상 구조는 낮은 confidence 또는 invalid로 처리한다.

---

# 10. Unit 처리

Unit은 다음 상태를 지원해야 한다.

```text
mg/dL
mmol/L
unknown
not_displayed
```

단위가 항상 화면에 표시된다는 가정을 하지 않는다.

별도의 lightweight classifier 또는 detector를 사용한다.

가능한 구조:

```text
Display ROI
    ├── Numeric Region
    └── Unit Region
```

unit을 object detector class로 직접 검출해도 되지만, 실제 데이터와 모델의 복잡도를 보고 별도의 classifier가 더 적합하면 그렇게 설계한다.

---

# 11. Device Profile

mg/dL 및 mmol/L 범위를 코드에 전역 하드코딩하지 않는다.

장기적으로 기기가 증가할 것을 고려하여 device profile 개념을 도입한다.

예:

```text
DeviceProfile
{
    model_id
    form_factor
    supported_units
    decimal_places
    min_value
    max_value
    supports_lo
    supports_hi
    error_patterns
    numeric_region
    unit_region
}
```

그러나 초기 단계에서는 device identification까지 반드시 구현하지 않아도 된다.

Generic pipeline을 먼저 만들고 device-specific rule을 configuration layer에 추가할 수 있게 구조화한다.

---

# 12. Status / Error 처리

숫자가 아닌 정상적인 결과를 모두 실패로 처리하지 않는다.

최소한 다음 상태를 고려한다.

```text
NORMAL
LOW / LO
HIGH / HI
ERROR
UNKNOWN
RETAKE
```

예:

```text
LO
HI
E-1
E-3
```

등은 숫자가 아니더라도 유효한 기기 출력일 수 있다.

따라서 parser가 다음과 같은 결과를 반환할 수 있어야 한다.

```text
ResultType.NORMAL
ResultType.LOW
ResultType.HIGH
ResultType.ERROR
ResultType.UNKNOWN
```

---

# 13. Domain Validation

시각 인식 결과가 바로 최종 결과가 되어서는 안 된다.

다음 순서로 검증한다.

```text
Raw Recognition
        ↓
Syntax Validation
        ↓
Unit Validation
        ↓
Device Profile Validation
        ↓
Numeric Plausibility
        ↓
Confidence Validation
        ↓
Temporal Consensus
```

예를 들어:

```text
unit = mmol/L
value = 100
```

과 같이 도메인상 비정상적인 결과가 나오면 ACCEPT하지 않는다.

또한:

```text
mmol/L
56
```

처럼 소수점 없이 읽힌 결과도 별도 검증 대상으로 삼는다.

단, 모든 경우를 절대 규칙으로 막지 않는다.

"소수점이 없어야 한다/있어야 한다"는 실제 device profile과 관측 데이터에 따라 판단할 수 있어야 한다.

---

# 14. Unknown / Abstain이 반드시 존재해야 한다

모델은 모르는 상황에서 답을 만들어내면 안 된다.

다음 상황에서는 UNKNOWN 또는 RETAKE가 가능해야 한다.

```text
glare가 숫자를 크게 가림
LCD가 너무 어두움
화면이 꺼져 있음
motion blur가 심함
digit 일부가 사라짐
dot이 너무 작음
display detector confidence가 낮음
glyph detector confidence가 낮음
unit이 판별되지 않음
sequence가 논리적으로 성립하지 않음
frame 간 결과가 계속 충돌함
```

상용 수준에서는 무조건 prediction을 내놓는 것보다 올바르게 abstain하는 것이 더 중요하다.

---

# 15. Input Quality Gate

모델 이전에 입력 품질을 검사한다.

최소한 다음을 검토한다.

```text
brightness
contrast
blur
saturation
highlight clipping
darkness
display size
display confidence
```

특히 glare가 중요하다.

---

# 16. 실시간 Glare Detection

카메라 preview 단계에서 반사광이 심한지 판단할 수 있어야 한다.

단순히 전체 이미지가 밝은지를 보지 않는다.

다음 개념을 사용한다.

```text
high-intensity pixel detection
        ↓
connected component / cluster
        ↓
cluster size
cluster density
location
```

LCD 영역 안에서 큰 포화 픽셀 클러스터가 발생하고 그것이 숫자 영역과 겹치면 재촬영을 유도한다.

예:

```text
display ROI
    ↓
saturated pixel mask
    ↓
connected components
    ↓
glare score
```

glare score가 임계값을 넘으면:

```text
"반사광을 피해 각도를 조정하세요"
```

같은 UX signal을 발생시킬 수 있도록 API를 설계한다.

---

# 17. Glare Augmentation

합성 glare는 실제 반사광을 모사해야 한다.

단순한 흰색 원을 그리는 방식으로 끝내지 않는다.

최소한 다음 parameter를 randomize한다.

```text
position
size
aspect_ratio
intensity
opacity
blur
edge_softness
rotation
```

가능하면 복수 highlight도 지원한다.

또한 다음 케이스를 별도로 만든다.

```text
digit 일부를 가림
dot을 가림
unit 일부를 가림
digit 획 중 일부를 가림
LCD 전체의 일부만 가림
```

---

# 18. Gaussian Alpha Glare Overlay

Glare 생성용으로 2D Gaussian kernel 기반의 alpha mask를 사용할 수 있다.

개념:

```text
2D Gaussian
    ↓
normalize
    ↓
alpha mask
    ↓
blend with image
```

중요한 조건:

* RGB 영역에 직접 하드코딩하지 말 것
* alpha mask 기반으로 합성할 것
* edge가 너무 날카롭지 않게 할 것
* intensity clipping을 일부 허용할 것
* 실제 LCD에서 발생하는 saturated highlight 형태를 재현할 것

실제 데이터와 합성 데이터의 차이를 validation set에서 확인한다.

---

# 19. 7-Segment 보존을 위한 Resize 규칙

resize가 인식률에 미치는 영향을 별도로 분석한다.

특히 다음을 측정한다.

```text
digit height before resize
digit height after resize
dot diameter before resize
dot diameter after resize
```

dot이 모델 입력에서 너무 작아지는 경우 해당 입력 크기는 사용하지 않거나 별도의 처리 경로를 고려한다.

주의:

```text
resize
→ blur
→ sharpen
```

등의 연속적인 이미지 처리가 7-segment 획을 과도하게 변형시키지 않도록 한다.

모델 학습 시에도 실제 모바일 inference와 동일한 resize/interpolation 정책을 사용하도록 한다.

---

# 20. 회전 및 종횡비 augmentation

다음 변형을 데이터 증강에 포함한다.

```text
0°
90°
180°
270°
small rotation
aspect-ratio variation
scale variation
perspective-like distortion
```

단, 무작위 변형을 무제한 적용하지 않는다.

실제 혈당측정기의 물리적 촬영 조건에 기반한 범위를 설정한다.

특히 7-segment가 심하게 찌그러지는 augmentation은 오히려 데이터 분포를 왜곡할 수 있으므로 validation 결과로 유지 여부를 판단한다.

---

# 21. mmol/L 부족 데이터 처리

실제 데이터에서 mmol/L가 부족하면 domain-specific augmentation을 사용한다.

우선순위:

```text
Real mmol/L data
        >
real dot crop + photometric augmentation
        >
careful copy-paste
        >
fully synthetic rendering
```

단순하게 임의의 "." 이미지를 붙이지 않는다.

Copy-Paste하는 경우 주변 LCD 배경 특성까지 고려한다.

가능한 변형:

```text
brightness
contrast
blur
opacity
noise
local background statistics
glare
```

을 같이 변형한다.

---

# 22. 데이터 라벨 구조

이미지 단위 metadata:

```text
image_id
device_model
physical_device_id
capture_session
form_factor
orientation
unit
screen_state
lighting_condition
glare_level
blur_level
occlusion
```

object/region label:

```text
display
glyph
dot
minus
unit_text
status_text
```

glyph attribute:

```text
character
confidence / ambiguity status
```

문자 후보:

```text
0-9
E
L
O
H
I
-
unknown
```

필요하지 않은 class는 실제 데이터 분석 후 제거한다.

---

# 23. Annotation Tool

기본 추천은 CVAT를 우선 검토한다.

이유는 object detection 중심 데이터셋 관리와 annotation workflow에 적합하기 때문이다.

그러나 이미 프로젝트에서 Label Studio 또는 Roboflow가 사용되고 있다면 반드시 새 도구로 교체할 필요는 없다.

중요한 것은 도구 이름이 아니라 다음을 지원하는 것이다.

```text
Bounding Box
Image metadata
Object attributes
Review
Quality control
Export
Versioning
```

Annotation tool은 코드 구조에 강하게 결합하지 않는다.

COCO/YOLO 등 표준 포맷으로 export할 수 있도록 한다.

---

# 24. Annotation Guideline

작업자에게 애매한 결과를 억지로 특정 숫자로 지정하도록 하지 않는다.

반드시:

```text
unknown
ambiguous
occluded
unreadable
```

상태를 제공한다.

예:

3과 8의 일부 획이 glare로 가려져 구분할 수 없는 경우 임의로 3 또는 8을 선택하지 않는다.

잘못된 라벨은 모델이 가장 자신 있게 틀리는 원인이 될 수 있다.

---

# 25. Annotation 규칙

다음 규칙을 명확하게 문서화한다.

### digit

문자 전체를 포함하는 BBox.

### dot

소수점 자체만 BBox.

주변 digit과 합쳐 하나의 BBox로 만들지 않는다.

### minus

가능한 경우 독립 glyph로 처리.

### unit

가능하면 전체 unit text 영역을 하나의 region으로 관리.

### status/error

예:

```text
LO
HI
E-1
E-2
```

전체 또는 개별 glyph를 프로젝트 설계에 맞게 일관되게 라벨링한다.

한 프로젝트 내부에서 라벨 기준을 중간에 변경하지 않는다.

---

# 26. 가장 중요한 Dataset Split 규칙

랜덤 이미지 분할을 사용하지 않는다.

같은 혈당측정기에서 연속으로 찍은 사진이 train과 test에 섞이면 데이터 누수가 발생한다.

최소한 다음 단위로 group split한다.

```text
physical_device_id
capture_session
```

가능하면 다음도 분리한다.

```text
device_model
```

평가셋은 최소 두 종류를 만든다.

### Seen Device Test

훈련 데이터에서 동일 모델이 등장했지만 다른 실기기 또는 다른 촬영 session.

### Unseen Device Test

학습 데이터에 존재하지 않는 device model.

상용 글로벌 제품에서 Unseen Device 성능이 매우 중요하다.

---

# 27. Dataset 구성

가능하면 다음 데이터를 균형 있게 확보한다.

```text
device model
orientation
unit
lighting
glare
blur
distance
angle
screen state
occlusion
numeric value
status/error
```

특히 다음 샘플을 별도로 hard-case dataset으로 만든다.

```text
very small dot
partial digit occlusion
glare across dot
glare across digit
low contrast
dark LCD
overexposed LCD
slightly rotated display
90° rotated image
180° rotated image
partial display crop
```

---

# 28. Hard Negative Dataset

잘못 읽기 쉬운 케이스를 별도로 수집한다.

예:

```text
blank LCD
reflections
phone screen reflection
bright background
white object
finger
skin highlight
table reflection
device buttons
non-LCD text
```

이 데이터가 있어야 Display Detector가 숫자가 아닌 것을 LCD 또는 glyph로 오인하는 문제를 줄일 수 있다.

---

# 29. Evaluation Metrics

전체 accuracy 하나만 보고 판단하지 않는다.

최소한 다음을 측정한다.

## Display Detector

```text
IoU
precision
recall
miss rate
false positive rate
```

## Glyph Detector

```text
precision
recall
mAP
dot recall
dot precision
```

특히 dot을 별도로 측정한다.

## Glyph Classifier

```text
accuracy
macro F1
per-class precision
per-class recall
confusion matrix
```

## End-to-End

가장 중요한 지표:

```text
Exact Reading Accuracy
```

예를 들어

```text
124 mg/dL
```

을 정확히

```text
124 mg/dL
```

로 읽었을 때만 성공으로 취급한다.

다음은 모두 실패로 분류한다.

```text
124 → 12
124 → 1240
124 → 174
5.6 → 56
5.6 → 5.8
```

---

# 30. Error Taxonomy

오류를 반드시 단계별로 분리한다.

```text
DISPLAY_DETECTION_ERROR

ORIENTATION_ERROR

GLYPH_DETECTION_ERROR

DOT_DETECTION_ERROR

GLYPH_CLASSIFICATION_ERROR

SEQUENCE_ERROR

UNIT_ERROR

STATUS_ERROR

DOMAIN_VALIDATION_ERROR

TEMPORAL_INSTABILITY

INPUT_QUALITY_ERROR
```

최종적으로 end-to-end accuracy가 낮더라도 어느 단계가 원인인지 즉시 알 수 있어야 한다.

---

# 31. Confidence 설계

각 단계의 confidence를 보존한다.

예:

```text
display_confidence
orientation_confidence
glyph_confidence[]
dot_confidence
unit_confidence
sequence_confidence
validation_score
temporal_score
```

최종 confidence 하나만 저장하지 않는다.

그래야 production에서 실패 원인을 추적할 수 있다.

---

# 32. Temporal Consensus

모바일 카메라 preview에서는 단일 frame 결과에 의존하지 않는다.

예:

```text
Frame 1 → 124
Frame 2 → 124
Frame 3 → 124
Frame 4 → 124
```

이면 높은 신뢰도로 accept한다.

반대로:

```text
124
184
124
129
```

이면 unstable 상태로 판단한다.

가능하면 최근 N개 프레임을 이용하여:

```text
string voting
confidence weighted voting
stable-count
```

등을 적용한다.

다만 latency가 지나치게 증가하지 않도록 제한한다.

---

# 33. RETAKE 정책

시스템은 다음 상황에서 숫자를 만들어내지 말고 재촬영을 권고할 수 있어야 한다.

예:

```text
display confidence too low
glare too high
blur too high
display too small
digit confidence too low
dot missing
unit/value conflict
frame unstable
screen blank
unknown status
```

최종 상태는 최소한:

```text
SUCCESS
RETAKE
UNKNOWN
ERROR
```

정도로 명확하게 구분한다.

---

# 34. Mobile/NPU 최적화

모델은 모바일에서 실행할 수 있어야 한다.

우선순위:

```text
small model
low memory
low latency
stable ONNX export
minimal operator complexity
```

지원 검토:

```text
ONNX Runtime CPU
Android hardware acceleration / NNAPI 계열
iOS CoreML 계열
```

단, 특정 execution provider가 항상 NPU에서 모든 layer를 실행한다고 가정하지 않는다.

실제 benchmark에서 다음을 기록한다.

```text
model size
parameter count
input resolution
FLOPs if available
memory
cold-start latency
warm inference latency
p50
p95
preprocess time
inference time
postprocess time
end-to-end latency
```

Android/iOS에서 실제 target device를 사용해 측정한다.

---

# 35. Benchmark 규칙

이론적인 FLOPs나 데스크톱 GPU 속도만으로 모델을 선택하지 않는다.

최종 선택 기준은 실제 스마트폰이다.

최소한:

```text
CPU
hardware acceleration path
```

각각을 측정한다.

또한 다음 두 조건을 비교한다.

```text
single frame
continuous preview
```

continuous preview에서는 thermal throttling에 따른 성능 저하도 가능하면 확인한다.

---

# 36. 전처리와 추론의 일관성

학습시 전처리와 모바일 inference의 전처리가 달라지면 안 된다.

다음을 configuration으로 명확하게 정의한다.

```text
image color format
resize method
normalization
channel order
padding
crop
rotation
```

학습 code와 production code 사이에 동일한 preprocessing specification을 유지한다.

---

# 37. False Confidence 방지

다음 상황에서 모델 confidence가 높더라도 결과를 그대로 믿지 않는다.

```text
domain rule conflict
unit conflict
sequence geometry conflict
dot missing
frame instability
glare overlap
blank screen
```

confidence는 하나의 증거일 뿐이며 validation 결과와 함께 판단한다.

---

# 38. Data Leakage 방지

다음과 같은 leakage를 반드시 피한다.

```text
same physical device in train and test
same capture burst in train and test
near-identical frames in train and test
same synthetic base image in train and test
same transformed sample family across split
```

특히 video에서 연속 frame을 독립 이미지로 취급하지 않는다.

---

# 39. Synthetic Data 사용 원칙

합성 데이터는 실제 데이터의 대체품이 아니다.

용도:

```text
rare character
dot
rare unit
rare error code
rare orientation
hard augmentation
```

등으로 제한적으로 사용한다.

Validation/Test는 가능한 한 real capture 위주로 구성한다.

---

# 40. 기존 코드베이스를 먼저 분석하라

코드를 수정하기 전에 반드시 기존 프로젝트를 분석한다.

먼저 확인할 것:

```text
project structure
existing ML code
existing preprocessing
existing image pipeline
existing ONNX models
existing inference code
existing mobile camera code
existing dataset format
existing training scripts
existing configuration
existing test code
```

이미 존재하는 구현을 무조건 갈아엎지 않는다.

현재 코드에서 재사용 가능한 부분을 먼저 식별한다.

---

# 41. 구현 우선순위

다음 순서를 따른다.

### Phase 1

현재 codebase와 데이터 구조 분석.

### Phase 2

현재 모델/알고리즘의 baseline 측정.

### Phase 3

Display ROI detection 추가 또는 개선.

### Phase 4

Padded ROI crop 및 orientation 처리.

### Phase 5

Glyph detection/classification 구조 구현.

### Phase 6

dot 전용 처리 추가.

### Phase 7

unit/status 처리.

### Phase 8

domain validation.

### Phase 9

glare/blur/exposure quality gate.

### Phase 10

temporal consensus.

### Phase 11

실제 모바일 benchmark.

각 단계에서 end-to-end accuracy 변화량을 기록한다.

---

# 42. 무조건 모델을 복잡하게 만들지 않는다

성능 개선이 다음에서 나올 가능성을 우선 검증한다.

```text
better crop
better data
better labeling
better hard negatives
better dot handling
better preprocessing
better validation
```

모델 크기를 키우는 것은 마지막 선택지로 둔다.

예를 들어:

```text
large OCR transformer
```

를 도입해서 1~2% accuracy가 올라가더라도 모바일 latency와 메모리가 크게 증가한다면 적절한 solution이 아니다.

---

# 43. Ablation Study

가능한 경우 다음 실험을 각각 독립적으로 한다.

```text
Baseline
Baseline + ROI detection
ROI + padding
ROI + orientation
ROI + glyph detector
ROI + glyph classifier
ROI + dot specialist
ROI + glare augmentation
ROI + quality gate
ROI + temporal consensus
```

각 실험에 대해:

```text
end-to-end accuracy
dot accuracy
false reading rate
unknown rate
retake rate
latency
memory
```

를 기록한다.

이를 통해 실제로 어느 기능이 인식률을 올리는지 확인한다.

---

# 44. 가장 중요한 지표: False Reading Rate

이 프로젝트에서는 단순 인식률만 높이는 것이 목표가 아니다.

다음 두 값을 별도로 관리한다.

```text
Correct Reading Rate
False Reading Rate
```

특히:

```text
Wrong number + high confidence
```

는 치명적인 실패로 분류한다.

반면:

```text
Unknown / RETAKE
```

는 정확한 숫자를 틀리게 출력하는 것보다 훨씬 낮은 위험의 실패로 본다.

최종 최적화 목표는:

```text
높은 Correct Reading Rate
+
낮은 False Reading Rate
+
합리적인 RETAKE Rate
```

이다.

---

# 45. Acceptance Criteria

구현이 끝났다고 판단하기 전에 최소한 다음을 확인한다.

```text
1. 정상 mg/dL 숫자를 안정적으로 읽는다.

2. 정상 mmol/L 숫자를 소수점 포함 정확하게 읽는다.

3. dot이 사라지는 경우 이를 감지할 수 있다.

4. 90°/180° 회전을 처리한다.

5. 가로형/세로형 device를 모두 처리한다.

6. glare가 강한 경우 무리하게 숫자를 출력하지 않는다.

7. blank LCD를 숫자로 오인하지 않는다.

8. LO/HI를 정상 상태로 처리할 수 있다.

9. Error code를 지원할 수 있다.

10. unit과 value가 충돌할 경우 reject/unknown 할 수 있다.

11. frame 간 결과가 불안정하면 RETAKE/UNKNOWN으로 판단할 수 있다.

12. train/test leakage가 없다.

13. unseen device evaluation이 가능하다.

14. 실제 모바일 환경에서 inference latency와 memory를 측정할 수 있다.

15. 모든 오류가 단계별 error taxonomy로 추적 가능하다.
```

---

# 46. 코드 품질 요구사항

구현 시 모든 핵심 threshold와 정책을 코드에 하드코딩하지 않는다.

예:

```text
glare threshold
blur threshold
display confidence threshold
glyph confidence threshold
dot confidence threshold
temporal stable count
padding ratio
input resolution
```

등은 configuration으로 관리한다.

모델 파일, class list, preprocessing 정보도 코드와 분리한다.

---

# 47. 디버깅 및 시각화

개발 단계에서는 다음 debug output을 만들 수 있어야 한다.

```text
original image
display bbox
padded ROI
orientation
glyph boxes
glyph classes
glyph confidence
dot box
unit box
glare mask
blur score
final reconstructed string
validation result
final confidence
```

특히 잘못 읽은 샘플을 한 번에 분석할 수 있도록 debug visualization을 제공한다.

예:

```text
[Original]
[Display ROI]
[Glyph Detection]
[Classification]
[Parsed Result]
[Validation]
```

형태.

---

# 48. 최종 결과 데이터 구조

최종 inference API는 단순 string을 반환하지 않는다.

가능하면 다음과 같은 구조를 사용한다.

```text
RecognitionResult
{
    status:
        SUCCESS
        RETAKE
        UNKNOWN
        ERROR

    value:
        nullable numeric value

    raw_text:
        nullable string

    unit:
        MG_DL
        MMOL_L
        UNKNOWN

    result_type:
        NORMAL
        LOW
        HIGH
        ERROR
        UNKNOWN

    confidence:

    display_confidence:

    glyph_confidences:

    dot_confidence:

    unit_confidence:

    validation_score:

    temporal_score:

    reason:
        optional failure reason
}
```

이 구조를 사용하면 나중에 UI에서:

```text
반사광이 너무 강합니다.
화면을 조금 기울여 주세요.
숫자를 인식하지 못했습니다.
```

등의 UX를 구현할 수 있다.

---

# 49. 구현 중 반드시 지켜야 할 금지사항

다음 방식으로 문제를 해결하려고 하지 않는다.

```text
일반 OCR 하나로 모든 것을 해결
```

```text
LCD 4개 corner keypoint에 전적으로 의존
```

```text
모델 confidence 하나만으로 결과 확정
```

```text
train/test 랜덤 이미지 분할
```

```text
모든 ambiguous sample을 억지로 숫자로 라벨링
```

```text
소수점을 일반 숫자와 동일하게 취급
```

```text
unit과 숫자 관계를 무시하고 parser 수행
```

```text
glare/blur 문제를 전부 neural network가 해결한다고 가정
```

```text
실제 모바일 benchmark 없이 모델 크기만 키움
```

```text
합성 데이터만으로 높은 validation accuracy를 만드는 것
```

---

# 50. 작업 결과 보고 형식

구현 과정에서 다음 내용을 문서화한다.

## 현재 baseline

```text
model:
dataset:
input size:
accuracy:
dot accuracy:
false reading rate:
latency:
```

## 변경 사항

각 변경마다:

```text
변경 내용
변경 이유
예상 효과
실제 효과
accuracy 변화
false reading 변화
latency 변화
memory 변화
```

를 기록한다.

## 최종 결과

다음 표 형태가 가능하도록 한다.

```text
Metric
--------------------------------
Exact Reading Accuracy
False Reading Rate
Retake Rate
Unknown Rate
Dot Accuracy
Unit Accuracy
Display Detection Recall
Glyph Detection Recall
Seen Device Accuracy
Unseen Device Accuracy
P50 Latency
P95 Latency
Peak Memory
Model Size
```

---

# 51. 최종 기술 방향

현재 프로젝트의 기본 아키텍처는 다음을 우선 채택한다.

```text
Camera
  ↓
Quality Gate
  ↓
Display Detector
  ↓
Padded ROI
  ↓
Orientation Normalization
  ↓
Glyph Detection
  ↓
Tiny CNN Glyph Classifier
  ↓
Dot Specialist
  ↓
Unit / Status Recognition
  ↓
Sequence Reconstruction
  ↓
Domain Validation
  ↓
Temporal Consensus
  ↓
SUCCESS / RETAKE / UNKNOWN
```

다만 현재 코드베이스와 실제 데이터셋을 먼저 분석한 결과 이 구조보다 더 단순한 구조가 동일하거나 더 높은 정확도를 제공한다면 단순한 구조를 선택한다.

목표는 논문 수준의 복잡한 모델이 아니라:

```text
실제 사용자 환경에서 높은 정확도
낮은 false reading
안정적인 dot 인식
낮은 모바일 latency
낮은 memory 사용량
다양한 혈당측정기 대응
실패 상황의 명확한 감지
```

이다.

---

# 52. 최종 개발 원칙

가장 중요한 것은 "모델 정확도"와 "시스템 정확도"를 구분하는 것이다.

모델이 99% accuracy를 기록하더라도,

```text
1%가 잘못된 혈당값
```

이고 그 결과를 confidence 0.99로 사용자에게 보여준다면 상용 시스템으로는 문제가 된다.

반대로

```text
98% 정확
+
잘못된 입력에서 RETAKE
+
temporal consensus
+
domain validation
```

구조로 false reading을 크게 줄이는 것이 더 좋은 시스템일 수 있다.

따라서 모든 구현 및 실험은 다음 우선순위를 따른다.

```text
1. False Reading 최소화
2. Exact Reading Accuracy 향상
3. Dot 인식 안정화
4. 다양한 device 대응
5. RETAKE/UNKNOWN의 합리적 제어
6. 모바일 latency/memory 최적화
7. 모델 복잡도 최소화
```

먼저 기존 프로젝트와 현재 데이터셋을 분석하고, 현재 baseline을 측정한 뒤 위 구조를 실제 코드베이스에 맞게 구현하라.

기존 코드와 데이터가 어떤 상태인지 확인하지 않은 채 새로운 모델이나 프레임워크를 임의로 도입하지 마라.

모든 중요한 변경은 실제 데이터의 정량적 결과로 검증하라.
