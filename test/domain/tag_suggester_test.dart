import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/services/tag_suggester.dart';

void main() {
  const suggester = TagSuggester();

  DateTime at(int hour, [int minute = 0]) =>
      DateTime(2026, 3, 15, hour, minute);

  group('공복', () {
    test('이른 아침 + 최근 식사 없음 → 공복', () {
      final tag = suggester.suggest(TagContext(localNow: at(7)));
      expect(tag, MeasurementTag.fasting);
    });

    test('이른 아침이어도 8시간 안에 식사가 있으면 공복이 아니다', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(7),
        lastMealAt: at(2), // 5시간 전
      ));
      expect(tag, isNot(MeasurementTag.fasting));
    });

    test('정확히 8시간이 지나면 공복으로 본다', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(9),
        lastMealAt: at(1),
      ));
      expect(tag, MeasurementTag.fasting);
    });

    test('아침 창 밖(10시 이후)이면 식사가 없어도 공복이 아니다', () {
      final tag = suggester.suggest(TagContext(localNow: at(11)));
      expect(tag, isNot(MeasurementTag.fasting));
    });
  });

  group('식전', () {
    test('예정된 식사가 30분 이내면 식전', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(12, 40),
        nextScheduledMealAt: at(13),
      ));
      expect(tag, MeasurementTag.preMeal);
    });

    test('예정 식사가 아직 멀면 식전이 아니다', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(12),
        nextScheduledMealAt: at(13),
      ));
      expect(tag, isNot(MeasurementTag.preMeal));
    });

    test('예정 식사 정보가 없으면 식전을 추천하지 않는다', () {
      // 과거 식사 기록만으로는 "먹기 전"을 알 수 없다.
      final tag = suggester.suggest(TagContext(
        localNow: at(12),
        lastMealAt: at(11, 50),
      ));
      expect(tag, isNot(MeasurementTag.preMeal));
    });
  });

  group('식후', () {
    test('식사 90분 후 → 식후', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(13, 30),
        lastMealAt: at(12),
      ));
      expect(tag, MeasurementTag.postMeal);
    });

    test('식사 30분 후는 아직 식후 창이 아니다', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(12, 30),
        lastMealAt: at(12),
      ));
      expect(tag, isNot(MeasurementTag.postMeal));
    });

    test('식사 3시간 후는 식후 창을 벗어난다', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(15),
        lastMealAt: at(12),
      ));
      expect(tag, isNot(MeasurementTag.postMeal));
    });

    test('식후와 운동 후가 겹치면 식후가 이긴다', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(13, 30),
        lastMealAt: at(12),
        lastExerciseAt: at(13),
      ));
      expect(tag, MeasurementTag.postMeal);
    });
  });

  group('운동 후', () {
    test('운동 1시간 후 → 운동 후', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(16),
        lastExerciseAt: at(15),
      ));
      expect(tag, MeasurementTag.postExercise);
    });

    test('운동 3시간 후는 창을 벗어난다', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(18),
        lastExerciseAt: at(15),
      ));
      expect(tag, isNot(MeasurementTag.postExercise));
    });
  });

  group('취침 전', () {
    test('22시 → 취침 전', () {
      expect(suggester.suggest(TagContext(localNow: at(22))),
          MeasurementTag.bedtime);
    });

    test('자정 넘어 1시도 취침 전', () {
      expect(suggester.suggest(TagContext(localNow: at(1))),
          MeasurementTag.bedtime);
    });

    test('새벽 4시는 공복 창이라 취침 전이 아니다', () {
      expect(suggester.suggest(TagContext(localNow: at(4))),
          MeasurementTag.fasting);
    });
  });

  group('단서 없음', () {
    test('직전 태그를 따라간다', () {
      final tag = suggester.suggest(TagContext(
        localNow: at(15),
        previousTag: MeasurementTag.postMeal,
      ));
      expect(tag, MeasurementTag.postMeal);
    });

    test('직전 태그도 없으면 미지정', () {
      expect(suggester.suggest(TagContext(localNow: at(15))),
          MeasurementTag.random);
    });
  });
}
