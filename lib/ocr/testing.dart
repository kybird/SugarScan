/// 테스트 전용 표면.
///
/// 프로덕션 코드는 이 라이브러리를 import 하지 않는다. 통합 테스트가 실제
/// 카메라·모델 없이 스캔 경로를 돌리거나, 유닛 테스트가 모듈 내부 부품을
/// 직접 검증할 때만 쓴다.
library;

export 'src/correction/reading_normalizer.dart';
export 'src/correction/reading_stabilizer.dart';
export 'src/engine/ocr_engine.dart';
export 'src/engine/ocr_engine_registry.dart';
export 'src/engine/ocr_result.dart';
export 'src/engines/fake/fake_engine.dart';
export 'src/engines/segment_rule/display_assembler.dart';
export 'src/engines/segment_rule/frame_quality.dart';
export 'src/engines/segment_rule/gray_image.dart';
export 'src/engines/segment_rule/lcd_binarizer.dart';
export 'src/engines/segment_rule/meter_profile.dart';
export 'src/engines/segment_rule/segment_geometry.dart';
export 'src/engines/segment_rule/segment_patterns.dart';
export 'src/engines/segment_rule/segment_rule_engine.dart';
export 'src/engines/segment_rule/segment_sampler.dart';
export 'src/engines/sevenseg_cnn/cell_splitter.dart';
export 'src/engines/sevenseg_cnn/digit_classifier.dart';
export 'src/engines/sevenseg_cnn/seven_seg_cnn_engine.dart';
export 'src/pipeline/frame_throttler.dart';
