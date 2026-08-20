import 'dart:math' as math;

import '../models/glucose_reading.dart';
import '../models/measurement_tag.dart';

/// 사용자가 설정한 목표 범위(mg/dL 정본).
///
/// 임상 지침이 아니라 사용자가 스스로 정하는 관찰 범위다. 기본값은 흔히 쓰이는
/// 참고 구간이며, 앱은 이 범위를 근거로 어떤 권고도 하지 않는다.
class TargetRange {
  const TargetRange({this.lowMgdl = 70, this.highMgdl = 180});

  final double lowMgdl;
  final double highMgdl;

  bool contains(double mgdl) => mgdl >= lowMgdl && mgdl <= highMgdl;
}

class GlucoseSummary {
  const GlucoseSummary({
    required this.count,
    required this.meanMgdl,
    required this.minMgdl,
    required this.maxMgdl,
    required this.standardDeviation,
    required this.inRangeRatio,
    required this.meanByTag,
  });

  final int count;
  final double meanMgdl;
  final double minMgdl;
  final double maxMgdl;
  final double standardDeviation;

  /// 목표 범위 안에 들어온 **측정 건수** 비율(0~1).
  ///
  /// CGM 의 TIR(Time in Range)과 다르다. SMBG 는 시간이 아니라 시점 표본이므로
  /// 같은 이름을 쓰면 임상적으로 오해를 부른다.
  final double inRangeRatio;

  final Map<MeasurementTag, double> meanByTag;
}

class GlucoseStatistics {
  const GlucoseStatistics();

  GlucoseSummary? summarize(
    List<GlucoseReading> readings, {
    TargetRange target = const TargetRange(),
  }) {
    final active = readings.where((r) => !r.isDeleted).toList(growable: false);
    if (active.isEmpty) return null;

    final values = active.map((r) => r.valueMgdl).toList(growable: false);
    final mean = values.reduce((a, b) => a + b) / values.length;

    // 표본분산(n-1). 측정값은 모집단이 아니라 표본이다.
    final variance = values.length < 2
        ? 0.0
        : values
                .map((v) => math.pow(v - mean, 2).toDouble())
                .reduce((a, b) => a + b) /
            (values.length - 1);

    final byTag = <MeasurementTag, List<double>>{};
    for (final r in active) {
      byTag.putIfAbsent(r.tag, () => <double>[]).add(r.valueMgdl);
    }

    return GlucoseSummary(
      count: values.length,
      meanMgdl: mean,
      minMgdl: values.reduce(math.min),
      maxMgdl: values.reduce(math.max),
      standardDeviation: math.sqrt(variance),
      inRangeRatio:
          values.where(target.contains).length / values.length,
      meanByTag: {
        for (final entry in byTag.entries)
          entry.key: entry.value.reduce((a, b) => a + b) / entry.value.length,
      },
    );
  }
}
