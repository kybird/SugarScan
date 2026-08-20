import '../models/glucose_reading.dart';

/// eA1c 산출 결과.
sealed class Ea1cOutcome {
  const Ea1cOutcome();
}

/// 표시 가능한 추정치.
final class Ea1cAvailable extends Ea1cOutcome {
  const Ea1cAvailable({
    required this.percent,
    required this.meanMgdl,
    required this.readingCount,
    required this.dayCount,
    required this.windowDays,
  });

  /// 추정 당화혈색소(%). 실제 검사값이 아니다.
  final double percent;
  final double meanMgdl;
  final int readingCount;
  final int dayCount;
  final int windowDays;
}

/// 데이터가 모자라 표시하지 않는다. UI 는 무엇이 얼마나 부족한지 안내한다.
final class Ea1cInsufficientData extends Ea1cOutcome {
  const Ea1cInsufficientData({
    required this.readingCount,
    required this.dayCount,
    required this.requiredReadings,
    required this.requiredDays,
  });

  final int readingCount;
  final int dayCount;
  final int requiredReadings;
  final int requiredDays;
}

/// 평균 혈당으로 당화혈색소를 추정한다(F-5).
///
/// ADAG 공식: `A1c(%) = (평균혈당[mg/dL] + 46.7) / 28.7`
///
/// SMBG 는 측정 시점이 사용자 습관에 따라 크게 치우친다(식후만 재는 등).
/// 그래서 최소 데이터 요건을 두고, 미달이면 잘못된 안심/불안을 주지 않도록
/// 아예 표시하지 않는다.
class Ea1cCalculator {
  const Ea1cCalculator({
    this.windowDays = 14,
    this.minReadings = 20,
    this.minDays = 10,
  });

  final int windowDays;
  final int minReadings;
  final int minDays;

  Ea1cOutcome compute(List<GlucoseReading> readings, {required DateTime now}) {
    final cutoff = now.toUtc().subtract(Duration(days: windowDays));
    final inWindow = readings
        .where((r) => !r.isDeleted && r.measuredAtUtc.toUtc().isAfter(cutoff))
        .toList(growable: false);

    // 측정일 수는 로컬 벽시계 기준으로 센다. UTC 로 세면 여행 중이거나
    // 자정 근처 측정에서 날짜가 어긋난다.
    final days = inWindow
        .map((r) {
          final local = r.measuredAtLocalWallClock;
          return DateTime.utc(local.year, local.month, local.day);
        })
        .toSet();

    if (inWindow.length < minReadings || days.length < minDays) {
      return Ea1cInsufficientData(
        readingCount: inWindow.length,
        dayCount: days.length,
        requiredReadings: minReadings,
        requiredDays: minDays,
      );
    }

    final mean =
        inWindow.map((r) => r.valueMgdl).reduce((a, b) => a + b) / inWindow.length;

    return Ea1cAvailable(
      percent: (mean + 46.7) / 28.7,
      meanMgdl: mean,
      readingCount: inWindow.length,
      dayCount: days.length,
      windowDays: windowDays,
    );
  }
}
