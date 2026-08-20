import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/domain/services/ea1c_calculator.dart';

void main() {
  final now = DateTime.utc(2026, 3, 15, 12);

  GlucoseReading reading({
    required double mgdl,
    required int daysAgo,
    // 로컬(+09:00)로 옮겨도 날짜가 넘어가지 않는 시각을 기본으로 쓴다.
    int hour = 0,
    int seq = 0,
    bool deleted = false,
  }) {
    final measured = now.subtract(Duration(days: daysAgo)).copyWith(hour: hour);
    return GlucoseReading(
      id: 'r-$daysAgo-$seq',
      measuredAtUtc: measured,
      tzName: 'Asia/Seoul',
      utcOffsetMinutes: 540,
      valueMgdl: mgdl,
      enteredUnit: GlucoseUnit.mgdl,
      enteredValue: mgdl,
      tag: MeasurementTag.random,
      source: ReadingSource.ocr,
      createdAt: measured,
      updatedAt: measured,
      deletedAt: deleted ? measured : null,
    );
  }

  /// 요건을 넉넉히 채우는 기록 집합: 12일 × 2회 = 24회.
  List<GlucoseReading> sufficient({double mgdl = 120}) => [
        for (var d = 0; d < 12; d++) ...[
          reading(mgdl: mgdl, daysAgo: d, hour: 0, seq: 0),
          reading(mgdl: mgdl, daysAgo: d, hour: 6, seq: 1),
        ],
      ];

  group('충분한 데이터', () {
    test('ADAG 공식대로 계산한다', () {
      const calculator = Ea1cCalculator();
      final outcome = calculator.compute(sufficient(mgdl: 120), now: now);

      expect(outcome, isA<Ea1cAvailable>());
      final available = outcome as Ea1cAvailable;
      expect(available.meanMgdl, closeTo(120, 0.001));
      expect(available.percent, closeTo((120 + 46.7) / 28.7, 0.001));
      expect(available.readingCount, 24);
      expect(available.dayCount, 12);
    });
  });

  group('데이터 부족', () {
    test('측정 횟수가 모자라면 표시하지 않는다', () {
      const calculator = Ea1cCalculator();
      final readings = [
        for (var d = 0; d < 11; d++) reading(mgdl: 120, daysAgo: d),
      ];
      final outcome = calculator.compute(readings, now: now);

      expect(outcome, isA<Ea1cInsufficientData>());
      final insufficient = outcome as Ea1cInsufficientData;
      expect(insufficient.readingCount, 11);
      expect(insufficient.requiredReadings, 20);
    });

    test('측정일 수가 모자라면 표시하지 않는다 — 하루에 몰아 재도 소용없다', () {
      const calculator = Ea1cCalculator();
      final readings = [
        for (var i = 0; i < 30; i++)
          reading(mgdl: 120, daysAgo: 1, hour: 8, seq: i),
      ];
      final outcome = calculator.compute(readings, now: now);

      expect(outcome, isA<Ea1cInsufficientData>());
      expect((outcome as Ea1cInsufficientData).dayCount, 1);
    });
  });

  test('윈도우 밖 기록은 제외한다', () {
    const calculator = Ea1cCalculator();
    final readings = [
      ...sufficient(mgdl: 120),
      // 30일 전 기록. 평균을 끌어올리면 안 된다.
      reading(mgdl: 400, daysAgo: 30, seq: 9),
    ];
    final outcome = calculator.compute(readings, now: now) as Ea1cAvailable;
    expect(outcome.meanMgdl, closeTo(120, 0.001));
  });

  test('삭제된 기록은 제외한다', () {
    const calculator = Ea1cCalculator();
    final readings = [
      ...sufficient(mgdl: 120),
      reading(mgdl: 400, daysAgo: 3, seq: 9, deleted: true),
    ];
    final outcome = calculator.compute(readings, now: now) as Ea1cAvailable;
    expect(outcome.meanMgdl, closeTo(120, 0.001));
    expect(outcome.readingCount, 24);
  });
}
