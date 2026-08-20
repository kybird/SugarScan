/// OCR 모듈의 공개 표면.
///
/// 앱이 볼 수 있는 것은 여기 있는 것이 전부다.
///
/// - 프레임을 [GlucoseScanner.offer] 에 넘긴다.
/// - [ScanConfirmed] 가 나오면 그 값을 **그대로 쓴다.** 재검증하지 않는다.
///   글자 보정, 값 검증, 프레임 간 합의는 모듈 안에서 이미 끝났다.
///
/// 엔진 인터페이스·레지스트리·안정화기 같은 부품은 `src/` 안에 있고 export
/// 하지 않는다. 앱이 그것들을 알게 되는 순간 엔진 교체 비용이 앱으로 번진다.
library;

export 'src/engine/ocr_frame.dart' show OcrFrame, OcrImageFormat, NormalizedRect;
export 'src/ocr_bootstrap.dart' show buildGlucoseScanner;
export 'src/scanner/glucose_scanner.dart' show GlucoseScanner;
export 'src/scanner/scan_outcome.dart';
