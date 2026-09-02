import 'wire_name.dart';

/// 측정 시점의 사용자 행동 상태.
///
/// 진단적 의미("정상"/"위험")를 담지 않는다. 상태 서술만 한다.
enum MeasurementTag {
  fasting('fasting'),
  preMeal('pre_meal'),
  postMeal('post_meal'),
  postExercise('post_exercise'),
  bedtime('bedtime'),
  random('random');

  const MeasurementTag(this.wireName);

  final String wireName;

  /// 모르는 값은 **기본값으로 치환하지 않고 던진다.**
  ///
  /// 예전에는 `random` 으로 떨어졌는데, 그러면 구버전 앱이 새 버전의 태그를
  /// `random` 으로 바꿔 저장했다가 그 기록을 수정하는 순간 서버에 덮어써
  /// 원본을 파괴한다. 자세한 이유는 [UnknownWireNameException].
  static MeasurementTag fromWireName(String value) =>
      values.firstWhere((e) => e.wireName == value,
          orElse: () => throw UnknownWireNameException('MeasurementTag', value));
}
