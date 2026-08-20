import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/models/glucose_unit.dart';
import '../../l10n/generated/app_localizations.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final unit = ref.watch(displayUnitProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.navSettings)),
      body: ListView(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              l10n.settingsUnitSection,
              style: theme.textTheme.titleSmall,
            ),
          ),
          RadioGroup<GlucoseUnit>(
            groupValue: unit,
            onChanged: (value) => _change(context, ref, value),
            child: Column(
              children: [
                for (final option in GlucoseUnit.values)
                  RadioListTile<GlucoseUnit>(
                    value: option,
                    title: Text(option.symbol),
                    subtitle: Text(
                      option == GlucoseUnit.mgdl
                          ? l10n.unitExampleMgdl
                          : l10n.unitExampleMmoll,
                    ),
                  ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              // 단위를 바꿔도 저장된 기록은 그대로다. 정본이 mg/dL 이라
              // 표시만 바뀌며, 각 기록은 입력 당시 단위를 간직한다.
              l10n.settingsUnitNote,
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
          ),
          const Divider(),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              l10n.medicalDisclaimer,
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _change(
    BuildContext context,
    WidgetRef ref,
    GlucoseUnit? unit,
  ) async {
    if (unit == null) return;
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);

    await ref.read(settingsRepositoryProvider).confirmUnit(unit);

    messenger.showSnackBar(
      SnackBar(content: Text(l10n.settingsUnitChanged(unit.symbol))),
    );
  }
}
