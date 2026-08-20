import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';

void main() {
  group('단위 변환', () {
    test('mmol/L → mg/dL 은 정확한 계수를 쓴다', () {
      expect(mmollToMgdl(7.6), closeTo(136.94, 0.01));
      expect(mmollToMgdl(5.0), closeTo(90.09, 0.01));
    });

    test('mg/dL → mmol/L', () {
      expect(mgdlToMmoll(126), closeTo(6.99, 0.01));
      expect(mgdlToMmoll(180), closeTo(9.99, 0.01));
    });

    test('왕복 변환은 표시 자릿수 안에서 값을 보존한다', () {
      for (final input in [4.0, 5.5, 7.6, 11.1, 22.2]) {
        final roundTrip = mgdlToMmoll(mmollToMgdl(input));
        expect(GlucoseUnit.mmoll.roundForDisplay(roundTrip), input);
      }
    });

    test('근사치 18 을 썼다면 발생했을 오차가 없다', () {
      // 18 을 쓰면 20 mmol/L 에서 약 0.4 mg/dL 어긋난다.
      expect(mmollToMgdl(20) - 20 * 18, closeTo(0.364, 0.001));
    });
  });

  group('표시 형식', () {
    test('mg/dL 은 정수로 표시한다', () {
      expect(GlucoseUnit.mgdl.format(136.94), '137');
      expect(GlucoseUnit.mgdl.displayFractionDigits, 0);
    });

    test('mmol/L 은 소수 1자리로 표시한다', () {
      expect(GlucoseUnit.mmoll.format(6.987), '7.0');
      expect(GlucoseUnit.mmoll.format(7.64), '7.6');
    });
  });

  group('국가별 기본 단위', () {
    test('mmol/L 권역', () {
      expect(defaultUnitForCountry('GB'), GlucoseUnit.mmoll);
      expect(defaultUnitForCountry('ca'), GlucoseUnit.mmoll);
      expect(defaultUnitForCountry('AU'), GlucoseUnit.mmoll);
    });

    test('mg/dL 권역', () {
      expect(defaultUnitForCountry('US'), GlucoseUnit.mgdl);
      expect(defaultUnitForCountry('KR'), GlucoseUnit.mgdl);
      expect(defaultUnitForCountry('DE'), GlucoseUnit.mgdl);
    });

    test('알 수 없는 국가는 mg/dL 로 떨어진다', () {
      expect(defaultUnitForCountry(null), GlucoseUnit.mgdl);
      expect(defaultUnitForCountry('ZZ'), GlucoseUnit.mgdl);
    });
  });

  test('wireName 은 직렬화 왕복을 견딘다', () {
    for (final unit in GlucoseUnit.values) {
      expect(GlucoseUnit.fromWireName(unit.wireName), unit);
    }
  });
}
