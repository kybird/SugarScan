import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/router.dart';
import '../../domain/models/glucose_reading.dart';
import '../../domain/models/glucose_unit.dart';
import '../../domain/services/ea1c_calculator.dart';
import '../../l10n/generated/app_localizations.dart';
import '../scan/scan_entry.dart';
import '../sync/sync_status_banner.dart';
import '../shared/reading_tile.dart';

/// 홈 대시보드.
///
/// 추이 그래프는 W11 에 붙는다. 지금은 스캔 진입점, 최근 기록, eA1c,
/// 그리고 상시 노출해야 하는 의료 면책 문구를 담는다.
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  static const int _previewCount = 5;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final unit = ref.watch(displayUnitProvider);
    final readings = ref.watch(recentReadingsProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.appTitle)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
        children: [
          // 막혔을 때만 나타난다. 평상시에는 높이 0 이라 배치가 흔들리지 않는다.
          const SyncStatusBanner(),
          _Ea1cCard(readings: readings.value ?? const []),
          const SizedBox(height: 24),
          Text(l10n.recentReadings, style: theme.textTheme.titleSmall),
          const SizedBox(height: 8),
          _RecentList(
            readings: readings,
            unit: unit,
            emptyMessage: l10n.historyEmpty,
          ),
          const SizedBox(height: 24),
          Text(
            l10n.medicalDisclaimer,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openScanner(context, ref),
        icon: const Icon(Icons.center_focus_strong),
        label: Text(l10n.scanCta),
      ),
    );
  }

  /// 스캔 화면이 돌려준 기록을 저장한다.
  ///
  /// 스캔이든 직접 입력이든 이 한 경로로 들어온다. 저장 자체는 저장소가
  /// 로컬 트랜잭션으로 끝내므로 네트워크가 없어도 실패하지 않는다.
  Future<void> _openScanner(BuildContext context, WidgetRef ref) async {
    final entry = await context.pushNamed<ScanEntry>(AppRoute.scan.name);
    if (entry == null || !context.mounted) return;

    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);

    await ref.read(glucoseRepositoryProvider).add(
          value: entry.value,
          unit: entry.unit,
          tag: entry.tag,
          source: entry.source,
          ocrEngineId: entry.engineId,
          ocrConfidence: entry.confidence,
          ocrRawText: entry.rawText,
          adjustedByUser: entry.adjustedByUser,
        );

    messenger.showSnackBar(
      SnackBar(
        content: Text(
          l10n.readingSaved(entry.unit.format(entry.value), entry.unit.symbol),
        ),
      ),
    );
  }
}

class _RecentList extends StatelessWidget {
  const _RecentList({
    required this.readings,
    required this.unit,
    required this.emptyMessage,
  });

  final AsyncValue<List<GlucoseReading>> readings;
  final GlucoseUnit unit;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    return readings.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(24),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (error, _) {
        // 원문은 화면이 아니라 로그로 남긴다. 번역되지 않은 예외 문장을
        // 사용자에게 보여 주지 않는다.
        debugPrint('최근 기록 조회 실패: $error');
        return Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            AppLocalizations.of(context).readingsLoadFailed,
            textAlign: TextAlign.center,
          ),
        );
      },
      data: (items) {
        if (items.isEmpty) {
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                emptyMessage,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ),
          );
        }
        return Card(
          child: Column(
            children: [
              for (final reading
                  in items.take(DashboardScreen._previewCount))
                ReadingTile(reading: reading, unit: unit),
            ],
          ),
        );
      },
    );
  }
}

class _Ea1cCard extends StatelessWidget {
  const _Ea1cCard({required this.readings});

  final List<GlucoseReading> readings;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final outcome =
        const Ea1cCalculator().compute(readings, now: DateTime.now());

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(l10n.ea1cLabel, style: theme.textTheme.labelLarge),
                const SizedBox(width: 8),
                if (outcome is Ea1cAvailable)
                  // 추정치라는 사실을 값 옆에 붙여 둔다. 실제 검사 결과로
                  // 오해되면 사용자가 잘못된 안심을 얻는다.
                  Chip(
                    label: Text(l10n.ea1cEstimateBadge),
                    visualDensity: VisualDensity.compact,
                    padding: EdgeInsets.zero,
                  ),
              ],
            ),
            const SizedBox(height: 8),
            switch (outcome) {
              Ea1cAvailable(:final percent) => Text(
                  '${percent.toStringAsFixed(1)}%',
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              Ea1cInsufficientData(
                :final requiredReadings,
                :final requiredDays,
              ) =>
                Text(
                  l10n.ea1cInsufficientData(requiredReadings, requiredDays),
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
            },
          ],
        ),
      ),
    );
  }
}
