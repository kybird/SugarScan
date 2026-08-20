import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/router.dart';
import '../../domain/models/glucose_unit.dart';
import '../../l10n/generated/app_localizations.dart';
import '../scan/scan_entry.dart';

/// 홈 대시보드.
///
/// W11 에 최근 수치 카드·추이 그래프·eA1c 로 채운다. 지금은 스캔 진입점과
/// 상시 노출해야 하는 의료 면책 문구만 자리를 잡아 둔다.
class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  /// 스캔 화면이 돌려준 기록을 받는다.
  ///
  /// 저장 계층이 아직 없어(W8) 확인만 보여 준다. Drift 가 붙으면 이 자리에서
  /// `GlucoseReading.fromEntry` 로 바꿔 저장한다.
  Future<void> _openScanner(BuildContext context) async {
    final entry = await context.pushNamed<ScanEntry>(AppRoute.scan.name);
    if (entry == null || !context.mounted) return;

    final l10n = AppLocalizations.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          l10n.readingSaved(
            entry.unit.format(entry.value),
            entry.unit.symbol,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.appTitle)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l10n.ea1cLabel, style: theme.textTheme.labelLarge),
                  const SizedBox(height: 8),
                  Text(
                    l10n.ea1cInsufficientData(20, 10),
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
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
        onPressed: () => _openScanner(context),
        icon: const Icon(Icons.center_focus_strong),
        label: Text(l10n.scanCta),
      ),
    );
  }
}
