import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/core/result.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/services/glucose_validator.dart';

/// 값으로서의 타당성만 검증한다.
/// OCR 원문 보정(단위 제거, 글자 오인식, HI/LO)은 OCR 모듈의 책임이며
/// `test/ocr/reading_normalizer_test.dart` 에서 다룬다.
void main() {
  const validator = GlucoseValidator();

  double ok(String raw, GlucoseUnit unit) {
    final result = validator.parse(raw, unit);
    expect(result.isOk, isTrue,
        reason: 'parse("$raw") 가 실패했다: ${result.errorOrNull}');
    return (result as Ok<double, GlucoseValidationFailure>).value;
  }

  void fails(String raw, GlucoseUnit unit, GlucoseValidationFailure expected) {
    final result = validator.parse(raw, unit);
    expect(result.isErr, isTrue, reason: 'parse("$raw") 가 통과해버렸다');
    expect(result.errorOrNull, expected);
  }

  group('정상 입력', () {
    test('mg/dL 정수', () {
      expect(ok('138', GlucoseUnit.mgdl), 138);
      expect(ok('95', GlucoseUnit.mgdl), 95);
    });

    test('mmol/L 소수 1자리', () {
      expect(ok('7.6', GlucoseUnit.mmoll), 7.6);
      expect(ok('12.0', GlucoseUnit.mmoll), 12.0);
    });

    test('앞뒤 공백과 쉼표 소수점은 수동 입력에서도 흔하다', () {
      expect(ok(' 138 ', GlucoseUnit.mgdl), 138);
      expect(ok('7,6', GlucoseUnit.mmoll), 7.6);
    });
  });

  group('거부해야 하는 입력', () {
    test('빈 문자열', () {
      fails('', GlucoseUnit.mgdl, GlucoseValidationFailure.empty);
      fails('   ', GlucoseUnit.mgdl, GlucoseValidationFailure.empty);
    });

    test('숫자가 아닌 문자', () {
      fails('abc', GlucoseUnit.mgdl, GlucoseValidationFailure.notANumber);
      fails('13a', GlucoseUnit.mgdl, GlucoseValidationFailure.notANumber);
    });

    test('mg/dL 에 소수점이 오면 거부한다 — 혈당계는 정수만 표시한다', () {
      fails('13.8', GlucoseUnit.mgdl,
          GlucoseValidationFailure.unexpectedDecimals);
    });

    test('mmol/L 소수 2자리는 거부한다', () {
      fails('7.65', GlucoseUnit.mmoll,
          GlucoseValidationFailure.unexpectedDecimals);
    });

    test('물리적 범위 밖', () {
      fails('5', GlucoseUnit.mgdl, GlucoseValidationFailure.outOfRange);
      fails('950', GlucoseUnit.mgdl, GlucoseValidationFailure.outOfRange);
      fails('0.3', GlucoseUnit.mmoll, GlucoseValidationFailure.outOfRange);
    });

    test('자릿수가 4개 이상이면 숫자로 인정하지 않는다', () {
      fails('1380', GlucoseUnit.mgdl, GlucoseValidationFailure.notANumber);
    });
  });

  test('물리 범위 판정은 단위별로 다르다', () {
    expect(validator.isInPhysicalRange(7.6, GlucoseUnit.mmoll), isTrue);
    // 같은 숫자라도 mg/dL 로 보면 나올 수 없는 값이다.
    expect(validator.isInPhysicalRange(7.6, GlucoseUnit.mgdl), isFalse);
  });
}
