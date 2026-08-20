import 'dart:math' as math;

/// 혈당 표시 단위.
///
/// 저장 정본은 항상 mg/dL 이고, 이 enum 은 표시·입력 계층에서만 쓴다.
enum GlucoseUnit {
  mgdl('mgdl', 'mg/dL'),
  mmoll('mmoll', 'mmol/L');

  const GlucoseUnit(this.wireName, this.symbol);

  /// DB·API 직렬화용 식별자. 표시 문자열(symbol)과 분리해 두어야
  /// 심볼 표기를 바꿔도 저장된 데이터가 깨지지 않는다.
  final String wireName;
  final String symbol;

  static GlucoseUnit fromWireName(String value) =>
      values.firstWhere((e) => e.wireName == value);
}

/// 1 mmol/L 에 해당하는 mg/dL.
///
/// 흔히 쓰는 근사치 18 은 사용하지 않는다. 단위를 왕복 변환하면 오차가 누적되어
/// 사용자가 입력한 값과 다시 보여주는 값이 어긋난다.
const double kMgdlPerMmoll = 18.0182;

double mmollToMgdl(double mmoll) => mmoll * kMgdlPerMmoll;

double mgdlToMmoll(double mgdl) => mgdl / kMgdlPerMmoll;

extension GlucoseUnitConversion on GlucoseUnit {
  /// 이 단위의 값을 정본(mg/dL)으로 변환한다.
  double toMgdl(double value) => switch (this) {
        GlucoseUnit.mgdl => value,
        GlucoseUnit.mmoll => mmollToMgdl(value),
      };

  /// 정본(mg/dL)을 이 단위로 변환한다.
  double fromMgdl(double mgdl) => switch (this) {
        GlucoseUnit.mgdl => mgdl,
        GlucoseUnit.mmoll => mgdlToMmoll(mgdl),
      };

  /// 표시용 반올림 자릿수. mg/dL 은 정수, mmol/L 은 소수 1자리.
  int get displayFractionDigits => switch (this) {
        GlucoseUnit.mgdl => 0,
        GlucoseUnit.mmoll => 1,
      };

  double roundForDisplay(double value) {
    final factor = math.pow(10, displayFractionDigits).toDouble();
    return (value * factor).roundToDouble() / factor;
  }

  /// 단위 기호 없이 숫자만 반환한다. 기호는 위젯에서 별도 스타일로 붙인다.
  String format(double value) =>
      roundForDisplay(value).toStringAsFixed(displayFractionDigits);
}

/// mmol/L 을 기본으로 쓰는 국가(ISO 3166-1 alpha-2).
const Set<String> kMmollCountries = {
  'GB', 'IE', 'CA', 'AU', 'NZ', 'SE', 'NO', 'DK', 'FI', 'IS',
  'NL', 'CH', 'CZ', 'SK', 'HU', 'HR', 'SI', 'EE', 'LV', 'LT',
  'CN', 'HK', 'RU', 'UA', 'ZA',
};

/// 국가 코드로 추정한 기본 단위.
///
/// 온보딩의 *초기값*으로만 쓰고 반드시 사용자 확인을 받는다. 단위 오설정은
/// 이 앱에서 가장 위험한 UX 버그다(mmol/L 7.2 를 mg/dL 7 로 읽는 식).
GlucoseUnit defaultUnitForCountry(String? countryCode) {
  if (countryCode == null) return GlucoseUnit.mgdl;
  return kMmollCountries.contains(countryCode.toUpperCase())
      ? GlucoseUnit.mmoll
      : GlucoseUnit.mgdl;
}
