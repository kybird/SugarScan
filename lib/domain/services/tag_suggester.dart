import '../models/measurement_tag.dart';

/// 태그 추천에 필요한 입력. 모든 시각은 **로컬 벽시계 기준**이다.
class TagContext {
  const TagContext({
    required this.localNow,
    this.lastMealAt,
    this.nextScheduledMealAt,
    this.lastExerciseAt,
    this.previousTag,
  });

  final DateTime localNow;

  /// 마지막으로 기록된 식사 시각.
  final DateTime? lastMealAt;

  /// 사용자가 설정한 다음 식사 알림 시각.
  ///
  /// "식전"은 과거 식사 기록으로 추론할 수 없다(먹기 전에는 기록이 없다).
  /// 그래서 예정 식사 시각을 별도로 받는다. 없으면 식전 추천은 하지 않는다.
  final DateTime? nextScheduledMealAt;

  final DateTime? lastExerciseAt;

  /// 직전 기록의 태그. 아무 단서도 없을 때 사용자의 습관을 따라간다.
  final MeasurementTag? previousTag;
}

/// 시간대·행동 기반 태그 추천(F-2).
///
/// 부작용 없는 순수 함수로 유지한다. 추천 결과는 UI 에서 미리 선택된 칩으로만
/// 노출하고 자동 확정하지 않는다.
class TagSuggester {
  const TagSuggester();

  static const Duration fastingGap = Duration(hours: 8);
  static const int fastingStartHour = 4;
  static const int fastingEndHour = 10;
  static const int bedtimeStartHour = 21;
  static const int bedtimeEndHour = 3;

  static const Duration preMealWindow = Duration(minutes: 30);
  static const Duration postMealMin = Duration(minutes: 60);
  static const Duration postMealMax = Duration(minutes: 150);
  static const Duration postExerciseWindow = Duration(minutes: 120);

  MeasurementTag suggest(TagContext ctx) {
    final now = ctx.localNow;
    final hour = now.hour;

    // 1. 공복: 이른 아침이면서 최근 8시간 안에 식사 기록이 없을 때.
    final sinceMeal =
        ctx.lastMealAt == null ? null : now.difference(ctx.lastMealAt!);
    final inMorningWindow = hour >= fastingStartHour && hour < fastingEndHour;
    if (inMorningWindow && (sinceMeal == null || sinceMeal >= fastingGap)) {
      return MeasurementTag.fasting;
    }

    // 2. 식전: 예정된 식사가 30분 이내로 다가왔을 때.
    final untilMeal = ctx.nextScheduledMealAt?.difference(now);
    if (untilMeal != null &&
        !untilMeal.isNegative &&
        untilMeal <= preMealWindow) {
      return MeasurementTag.preMeal;
    }

    // 3. 식후: 식사 60~150분 후. 혈당 스파이크 관측 구간이라 운동보다 우선한다.
    if (sinceMeal != null &&
        sinceMeal >= postMealMin &&
        sinceMeal <= postMealMax) {
      return MeasurementTag.postMeal;
    }

    // 4. 운동 후: 운동 종료 2시간 이내.
    final sinceExercise = ctx.lastExerciseAt == null
        ? null
        : now.difference(ctx.lastExerciseAt!);
    if (sinceExercise != null &&
        !sinceExercise.isNegative &&
        sinceExercise <= postExerciseWindow) {
      return MeasurementTag.postExercise;
    }

    // 5. 취침 전: 21시 ~ 익일 3시.
    if (hour >= bedtimeStartHour || hour < bedtimeEndHour) {
      return MeasurementTag.bedtime;
    }

    // 6. 단서 없음 → 직전 습관을 따르고, 그것도 없으면 미지정.
    return ctx.previousTag ?? MeasurementTag.random;
  }
}
