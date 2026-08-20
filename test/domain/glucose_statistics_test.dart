import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/domain/services/glucose_statistics.dart';

const _stats = GlucoseStatistics();

GlucoseReading reading(
  double mgdl, {
  MeasurementTag tag = MeasurementTag.random,
  DateTime? at,
  bool deleted = false,
}) {
  final measured = at ?? DateTime.utc(2026, 3, 14, 1, 30);
  return GlucoseReading(
    id: 'r-$mgdl-${tag.wireName}-${measured.microsecondsSinceEpoch}',
    measuredAtUtc: measured,
    tzName: 'Asia/Seoul',
    utcOffsetMinutes: 540,
    valueMgdl: mgdl,
    enteredUnit: GlucoseUnit.mgdl,
    enteredValue: mgdl,
    tag: tag,
    source: ReadingSource.manual,
    createdAt: measured,
    updatedAt: measured,
    deletedAt: deleted ? measured : null,
  );
}

void main() {
  test('기록이 없으면 null — 0 으로 채운 요약을 만들지 않는다', () {
    // 0건과 "평균 0" 은 전혀 다른 이야기다. 화면이 둘을 구분할 수 있어야 한다.
    expect(_stats.summarize([]), isNull);
  });

  test('삭제된 기록은 세지 않는다', () {
    final summary = _stats.summarize([
      reading(100),
      reading(200, deleted: true),
    ]);

    expect(summary!.count, 1);
    expect(summary.meanMgdl, 100);
  });

  test('삭제된 것만 있으면 null', () {
    expect(_stats.summarize([reading(100, deleted: true)]), isNull);
  });

  group('기초 통계', () {
    test('평균·최소·최대', () {
      final summary = _stats.summarize([
        reading(100),
        reading(140),
        reading(180),
      ]);

      expect(summary!.count, 3);
      expect(summary.meanMgdl, 140);
      expect(summary.minMgdl, 100);
      expect(summary.maxMgdl, 180);
    });

    // 측정값은 모집단이 아니라 표본이다. n 으로 나누면 흩어짐을 과소평가한다.
    test('표준편차는 표본분산(n-1) 기준이다', () {
      final summary = _stats.summarize([
        reading(100),
        reading(140),
        reading(180),
      ]);

      // n-1: sqrt(((40^2)+(0)+(40^2))/2) = 40
      // n   으로 나눴다면 sqrt(3200/3) ≈ 32.66 이 나온다.
      expect(summary!.standardDeviation, closeTo(40, 0.001));
    });

    test('한 건뿐이면 표준편차는 0 이다', () {
      // n-1 이 0 이라 나눗셈이 무너질 수 있는 자리다.
      final summary = _stats.summarize([reading(120)]);

      expect(summary!.standardDeviation, 0);
      expect(summary.meanMgdl, 120);
    });
  });

  group('목표 범위', () {
    test('경계값은 범위 안이다', () {
      final summary = _stats.summarize([reading(70), reading(180)]);

      expect(summary!.inRangeRatio, 1.0);
    });

    test('경계 바로 밖은 범위 밖이다', () {
      final summary = _stats.summarize([reading(69), reading(181)]);

      expect(summary!.inRangeRatio, 0.0);
    });

    test('비율은 시간이 아니라 건수 기준이다', () {
      // CGM 의 TIR 과 다르다. SMBG 는 시점 표본이라 시간 가중을 할 수 없다.
      final summary = _stats.summarize([
        reading(100),
        reading(100),
        reading(300),
        reading(300),
      ]);

      expect(summary!.inRangeRatio, 0.5);
    });

    test('목표 범위를 바꾸면 비율이 따라 바뀐다', () {
      final readings = [reading(100), reading(150)];

      final wide = _stats.summarize(readings);
      final narrow = _stats.summarize(
        readings,
        target: const TargetRange(lowMgdl: 80, highMgdl: 120),
      );

      expect(wide!.inRangeRatio, 1.0);
      expect(narrow!.inRangeRatio, 0.5);
    });
  });

  group('태그별 평균', () {
    test('태그마다 따로 평균 낸다', () {
      final summary = _stats.summarize([
        reading(100, tag: MeasurementTag.fasting),
        reading(140, tag: MeasurementTag.fasting),
        reading(200, tag: MeasurementTag.postMeal),
      ]);

      expect(summary!.meanByTag[MeasurementTag.fasting], 120);
      expect(summary.meanByTag[MeasurementTag.postMeal], 200);
    });

    test('기록이 없는 태그는 아예 나오지 않는다', () {
      // 없는 것을 0 으로 채우면 화면이 "공복 평균 0" 을 그린다.
      final summary = _stats.summarize([
        reading(100, tag: MeasurementTag.fasting),
      ]);

      expect(summary!.meanByTag.containsKey(MeasurementTag.bedtime), isFalse);
      expect(summary.meanByTag, hasLength(1));
    });

    test('삭제된 기록은 태그별 평균에도 안 들어간다', () {
      final summary = _stats.summarize([
        reading(100, tag: MeasurementTag.fasting),
        reading(900, tag: MeasurementTag.fasting, deleted: true),
      ]);

      expect(summary!.meanByTag[MeasurementTag.fasting], 100);
    });
  });
}
