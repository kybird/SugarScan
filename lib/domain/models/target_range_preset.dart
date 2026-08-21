import 'glucose_unit.dart';

/// 사용자가 고를 수 있는 목표 범위 후보.
///
/// **직접 입력을 받지 않는다.** 임의의 숫자를 넣게 하면 앱이 그 범위를 근거로
/// "범위 안 73%" 같은 숫자를 계속 보여 주게 되는데, 그 범위에 아무 근거가 없어도
/// 화면은 똑같이 그럴듯해 보인다. 근거 있는 몇 개 중에서만 고르게 한다.
///
/// **단위별 표시값을 명시적으로 박아 둔다.** 지침이 두 단위로 직접 발표한 쌍이고,
/// 마침 기계적 변환 결과와도 일치한다(70 → 3.885 → 3.9). 그래도 계산에 맡기지
/// 않는 것은 반올림 규칙이 바뀌어도 지침 숫자가 흔들리지 않게 하기 위해서다.
///
/// 비교는 언제나 [lowMgdl]/[highMgdl] 로 한다. 정본이 mg/dL 이라 여기서 갈라지면
/// 같은 기록이 사용자 단위에 따라 다르게 판정된다.
enum TargetRangePreset {
  /// CGM 국제 합의의 Time in Range 구간. 치료 목표가 아니라 관찰 범위다.
  observation(
    wireName: 'observation',
    lowMgdl: 70,
    highMgdl: 180,
    mgdlLabel: '70–180',
    mmollLabel: '3.9–10.0',
  ),

  /// ADA Standards of Care 의 비임신 성인 식전 목표.
  preMeal(
    wireName: 'pre_meal',
    lowMgdl: 80,
    highMgdl: 130,
    mgdlLabel: '80–130',
    mmollLabel: '4.4–7.2',
  ),

  /// Time in Tight Range. 당뇨가 없는 사람이 대부분의 시간을 보내는 구간이다.
  tight(
    wireName: 'tight',
    lowMgdl: 70,
    highMgdl: 140,
    mgdlLabel: '70–140',
    mmollLabel: '3.9–7.8',
  );

  const TargetRangePreset({
    required this.wireName,
    required this.lowMgdl,
    required this.highMgdl,
    required this.mgdlLabel,
    required this.mmollLabel,
  });

  /// 저장·직렬화용 식별자. Dart enum 이름을 바꿔도 저장된 설정이 안 깨진다.
  final String wireName;

  final double lowMgdl;
  final double highMgdl;

  final String mgdlLabel;
  final String mmollLabel;

  /// 기본값은 **관찰 범위**다. 치료 목표를 기본으로 두면 앱이 그 목표를
  /// 권하는 것처럼 읽힌다.
  static const TargetRangePreset fallback = TargetRangePreset.observation;

  static TargetRangePreset fromWireName(String value) => values.firstWhere(
        (e) => e.wireName == value,
        orElse: () => fallback,
      );

  /// 주어진 단위로 보여 줄 범위 표기.
  String labelFor(GlucoseUnit unit) => switch (unit) {
        GlucoseUnit.mgdl => mgdlLabel,
        GlucoseUnit.mmoll => mmollLabel,
      };
}
