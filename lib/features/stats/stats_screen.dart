import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../app/providers.dart';
import '../../domain/models/glucose_reading.dart';
import '../../domain/models/glucose_unit.dart';
import '../../domain/models/target_range_preset.dart';
import '../../domain/services/glucose_statistics.dart';
import '../../l10n/generated/app_localizations.dart';
import '../shared/tag_labels.dart';

/// 통계 화면.
///
/// **판정하지 않는다.** 값에 "정상/높음/위험" 같은 이름이나 색을 붙이지 않고,
/// 목표 범위도 사용자가 정한 관찰 구간으로만 다룬다. 붙이는 순간 이 앱은
/// 일반 건강관리 도구가 아니라 진단 보조 기기 쪽으로 넘어간다.
class StatsScreen extends ConsumerWidget {
  const StatsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final unit = ref.watch(displayUnitProvider);
    final days = ref.watch(statsWindowProvider);
    final summary = ref.watch(statsSummaryProvider);
    final readings = ref.watch(statsReadingsProvider).value ?? const [];

    return Scaffold(
      appBar: AppBar(title: Text(l10n.navStats)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          SegmentedButton<int>(
            segments: [
              for (final option in StatsWindow.options)
                ButtonSegment(
                  value: option,
                  label: Text(l10n.statsWindowDays(option)),
                ),
            ],
            selected: {days},
            onSelectionChanged: (selection) =>
                ref.read(statsWindowProvider.notifier).select(selection.first),
          ),
          const SizedBox(height: 24),
          if (summary == null)
            _Empty(message: l10n.statsEmpty)
          else ...[
            _SummaryCard(summary: summary, unit: unit),
            const SizedBox(height: 12),
            _InRangeCard(summary: summary, unit: unit),
            const SizedBox(height: 24),
            Text(l10n.statsTrend, style: theme.textTheme.titleSmall),
            const SizedBox(height: 12),
            _TrendChart(readings: readings, unit: unit),
            const SizedBox(height: 24),
            _ByTagList(summary: summary, unit: unit),
          ],
          const SizedBox(height: 24),
          Text(
            l10n.medicalDisclaimer,
            style: theme.textTheme.bodySmall
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ],
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 48),
      child: Column(
        children: [
          Icon(Icons.insights_outlined, size: 48, color: scheme.outline),
          const SizedBox(height: 16),
          Text(
            message,
            textAlign: TextAlign.center,
            style: Theme.of(context)
                .textTheme
                .bodyLarge
                ?.copyWith(color: scheme.onSurfaceVariant),
          ),
        ],
      ),
    );
  }
}

/// 기간 요약 한 장.
///
/// 평균을 크게 두고 나머지는 그 아래 한 줄로 붙인다. 카드를 넷으로 쪼개면
/// 세로로 쌓이면서 정작 그래프가 첫 화면 밖으로 밀려난다. 숫자를 보러 온
/// 사람이 스크롤부터 해야 하는 화면이 된다.
class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.summary, required this.unit});

  final GlucoseSummary summary;
  final GlucoseUnit unit;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;

    // 정본은 mg/dL 이고 표시할 때만 사용자의 단위로 옮긴다.
    String show(double mgdl) => unit.format(unit.fromMgdl(mgdl));

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: scheme.surfaceContainerHighest,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(l10n.statsMean, style: theme.textTheme.titleSmall),
                    const SizedBox(height: 4),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          show(summary.meanMgdl),
                          style: theme.textTheme.displaySmall?.copyWith(
                            fontWeight: FontWeight.w600,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          unit.symbol,
                          style: theme.textTheme.bodySmall
                              ?.copyWith(color: scheme.onSurfaceVariant),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Text(
                l10n.statsReadingCount(summary.count),
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: scheme.onSurfaceVariant),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _Minor(label: l10n.statsLow, value: show(summary.minMgdl)),
              _Minor(label: l10n.statsHigh, value: show(summary.maxMgdl)),
              _Minor(
                label: l10n.statsSd,
                value: show(summary.standardDeviation),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Minor extends StatelessWidget {
  const _Minor({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;

    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: theme.textTheme.bodySmall
                ?.copyWith(color: scheme.onSurfaceVariant),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: theme.textTheme.titleMedium?.copyWith(
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
        ],
      ),
    );
  }
}

/// 목표 범위 안에 들어온 비율.
///
/// 비율 자체에 색을 입히지 않는다. 높으면 초록, 낮으면 빨강 같은 처리는 곧
/// 판정이고, 이 앱이 하지 않기로 한 일이다.
class _InRangeCard extends ConsumerWidget {
  const _InRangeCard({required this.summary, required this.unit});

  final GlucoseSummary summary;
  final GlucoseUnit unit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final preset =
        ref.watch(targetRangePresetProvider).value ?? TargetRangePreset.fallback;
    final percent = (summary.inRangeRatio * 100).round();

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: scheme.surfaceContainerHighest,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l10n.statsInRange, style: theme.textTheme.titleSmall),
          const SizedBox(height: 8),
          Text(
            '$percent%',
            style: theme.textTheme.displaySmall?.copyWith(
              fontWeight: FontWeight.w600,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: summary.inRangeRatio,
            minHeight: 6,
            borderRadius: BorderRadius.circular(3),
          ),
          const SizedBox(height: 12),
          Text(
            // 지침이 발표한 표기를 그대로 쓴다. 여기서 변환해 다시 만들면
            // 설정 화면과 통계 화면의 숫자가 반올림에 따라 갈릴 수 있다.
            l10n.statsTargetRange(preset.labelFor(unit), unit.symbol),
            style: theme.textTheme.bodySmall
                ?.copyWith(color: scheme.onSurfaceVariant),
          ),
          const SizedBox(height: 4),
          // CGM 의 TIR 과 혼동하면 임상적으로 잘못 읽힌다. 매번 붙여 둔다.
          Text(
            l10n.statsInRangeNote,
            style: theme.textTheme.bodySmall
                ?.copyWith(color: scheme.onSurfaceVariant),
          ),
        ],
      ),
    );
  }
}

/// 기간 내 기록을 시간축에 흩어 놓는다.
///
/// 점을 선으로 잇지 않는다. 채혈 측정은 **시점 표본**이라 점과 점 사이를 이으면
/// 재지 않은 구간에 없는 정보를 그려 넣는 셈이 된다. CGM 그래프처럼 보이는
/// 순간 사용자는 그 사이 값도 안다고 착각한다.
class _TrendChart extends ConsumerWidget {
  const _TrendChart({required this.readings, required this.unit});

  final List<GlucoseReading> readings;
  final GlucoseUnit unit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final target = ref.watch(targetRangeProvider);
    final locale = Localizations.localeOf(context).toString();

    if (readings.isEmpty) return const SizedBox.shrink();

    // 벽시계 시각을 쓴다. UTC 로 그리면 여행 중 기록이 엉뚱한 날에 찍힌다.
    final points = [
      for (final r in readings)
        FlSpot(
          r.measuredAtLocalWallClock.millisecondsSinceEpoch.toDouble(),
          unit.fromMgdl(r.valueMgdl),
        ),
    ]..sort((a, b) => a.x.compareTo(b.x));

    final values = points.map((p) => p.y).toList();
    final lowest = values.reduce((a, b) => a < b ? a : b);
    final highest = values.reduce((a, b) => a > b ? a : b);
    final low = unit.fromMgdl(target.lowMgdl);
    final high = unit.fromMgdl(target.highMgdl);

    // 목표 범위 띠가 잘리지 않도록 축 범위에 함께 넣는다.
    final minY = (lowest < low ? lowest : low) * 0.9;
    final maxY = (highest > high ? highest : high) * 1.1;

    return SizedBox(
      height: 220,
      child: LineChart(
        LineChartData(
          minY: minY,
          maxY: maxY,
          lineBarsData: [
            LineChartBarData(
              spots: points,
              // 선을 그리지 않는다. 점만 놓는다.
              barWidth: 0,
              color: Colors.transparent,
              dotData: FlDotData(
                getDotPainter: (spot, _, _, _) => FlDotCirclePainter(
                  radius: 3.5,
                  color: scheme.primary,
                  strokeWidth: 0,
                ),
              ),
            ),
          ],
          // 목표 범위는 중립적인 띠 하나로만 표시한다. 안팎을 초록/빨강으로
          // 칠하면 그건 판정이다.
          rangeAnnotations: RangeAnnotations(
            horizontalRangeAnnotations: [
              HorizontalRangeAnnotation(
                y1: low,
                y2: high,
                color: scheme.primary.withValues(alpha: 0.08),
              ),
            ],
          ),
          gridData: FlGridData(
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) => FlLine(
              color: scheme.outlineVariant.withValues(alpha: 0.4),
              strokeWidth: 1,
            ),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(),
            rightTitles: const AxisTitles(),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 44,
                getTitlesWidget: (value, meta) => Text(
                  unit.format(value),
                  style: theme.textTheme.bodySmall
                      ?.copyWith(color: scheme.onSurfaceVariant),
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 28,
                interval: _bottomInterval(points),
                getTitlesWidget: (value, meta) => Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    DateFormat.Md(locale).format(
                      DateTime.fromMillisecondsSinceEpoch(value.toInt()),
                    ),
                    style: theme.textTheme.bodySmall
                        ?.copyWith(color: scheme.onSurfaceVariant),
                  ),
                ),
              ),
            ),
          ),
          lineTouchData: const LineTouchData(enabled: false),
        ),
      ),
    );
  }

  /// 가로축 눈금 간격. 라벨이 겹치지 않을 만큼만 찍는다.
  static double _bottomInterval(List<FlSpot> points) {
    final span = points.last.x - points.first.x;
    return span <= 0 ? 1 : span / 3;
  }
}

class _ByTagList extends StatelessWidget {
  const _ByTagList({required this.summary, required this.unit});

  final GlucoseSummary summary;
  final GlucoseUnit unit;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    if (summary.meanByTag.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(l10n.statsByTag, style: theme.textTheme.titleSmall),
        const SizedBox(height: 8),
        // 기록이 없는 태그는 아예 나오지 않는다. 0 으로 채우면 화면이
        // "공복 평균 0" 이라는 없는 사실을 그린다.
        for (final entry in summary.meanByTag.entries)
          ListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            title: Text(entry.key.label(l10n)),
            trailing: Text(
              '${unit.format(unit.fromMgdl(entry.value))} ${unit.symbol}',
              style: theme.textTheme.bodyLarge?.copyWith(
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ),
      ],
    );
  }
}
