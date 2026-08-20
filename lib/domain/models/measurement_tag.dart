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

  static MeasurementTag fromWireName(String value) =>
      values.firstWhere((e) => e.wireName == value,
          orElse: () => MeasurementTag.random);
}
