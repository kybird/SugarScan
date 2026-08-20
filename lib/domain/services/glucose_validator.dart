import '../../core/result.dart';
import '../models/glucose_unit.dart';

enum GlucoseValidationFailure {
  /// 값이 비어 있다.
  empty,

  /// 숫자로 해석할 수 없다.
  notANumber,

  /// 단위가 허용하지 않는 소수 자릿수. mg/dL 은 정수만 나온다.
  unexpectedDecimals,

  /// 물리적으로 나올 수 없는 값.
  outOfRange,
}

/// 혈당값이 값으로서 성립하는지 판정한다.
///
/// 여기에는 **혈당이라는 도메인 지식만** 둔다. 7-세그먼트 글자 오인식이나
/// 단위 표기 제거 같은 OCR 특유의 보정은 OCR 모듈 안(`ReadingNormalizer`)에
/// 있다. 그래야 인식 엔진을 바꿔도 이 규칙이 흔들리지 않고, 수동 입력 경로와
/// 스캔 경로가 같은 기준을 공유한다.
class GlucoseValidator {
  const GlucoseValidator();

  /// 혈당계가 표시할 수 있는 물리적 범위. 임상 목표 범위가 아니라
  /// "이 값이 나올 수 있는가"만 판정한다.
  static const double mgdlMin = 10;
  static const double mgdlMax = 900;
  static const double mmollMin = 0.6;
  static const double mmollMax = 50;

  static final RegExp _shape = RegExp(r'^\d{1,3}(\.\d{1,2})?$');

  Result<double, GlucoseValidationFailure> parse(String text, GlucoseUnit unit) {
    final trimmed = text.trim().replaceAll(',', '.');
    if (trimmed.isEmpty) {
      return const Err(GlucoseValidationFailure.empty);
    }
    if (!_shape.hasMatch(trimmed)) {
      return const Err(GlucoseValidationFailure.notANumber);
    }

    final dotIndex = trimmed.indexOf('.');
    final decimals = dotIndex == -1 ? 0 : trimmed.length - dotIndex - 1;
    if (decimals > unit.displayFractionDigits) {
      return const Err(GlucoseValidationFailure.unexpectedDecimals);
    }

    final value = double.tryParse(trimmed);
    if (value == null) {
      return const Err(GlucoseValidationFailure.notANumber);
    }
    if (!isInPhysicalRange(value, unit)) {
      return const Err(GlucoseValidationFailure.outOfRange);
    }
    return Ok(value);
  }

  bool isInPhysicalRange(double value, GlucoseUnit unit) => switch (unit) {
        GlucoseUnit.mgdl => value >= mgdlMin && value <= mgdlMax,
        GlucoseUnit.mmoll => value >= mmollMin && value <= mmollMax,
      };
}
