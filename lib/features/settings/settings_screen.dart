import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../data/sync/sync_engine.dart';
import '../../domain/models/glucose_unit.dart';
import '../../domain/models/target_range_preset.dart';
import '../../l10n/generated/app_localizations.dart';
import '../shared/tag_labels.dart';

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
          const _TargetRangeSection(),
          const Divider(),
          const _SyncSection(),
          const Divider(),
          const _AccountSection(),
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

/// 계정. 로그인한 상태에서만 보인다.
///
/// 서버 미설정 빌드나 로그인하지 않은(세션 만료 후 로컬 모드) 상태에서는
/// 통째로 감춘다. 누를 수 없는 항목을 보여줄 이유가 없다.
class _AccountSection extends ConsumerWidget {
  const _AccountSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final signedIn = ref.watch(signedInProvider).value ?? false;
    if (!signedIn) return const SizedBox.shrink();

    final email = ref.watch(authRepositoryProvider).currentEmail;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            l10n.authAccountSection,
            style: theme.textTheme.titleSmall,
          ),
        ),
        ListTile(
          title: Text(l10n.authSignOut),
          subtitle: email == null ? null : Text(l10n.authSignedInAs(email)),
          onTap: () => ref.read(signOutProvider)(),
        ),
      ],
    );
  }
}

/// 동기화 상태. 서버가 설정된 빌드에서만 보인다.
///
/// 배너와 달리 여기서는 **평상시에도 숫자를 보여준다.** 사용자가 "지금 어떤
/// 상태인가"를 확인하러 오는 곳이라, 아무것도 없으면 기능이 없는 것처럼 보인다.
class _SyncSection extends ConsumerWidget {
  const _SyncSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    if (!ref.watch(remoteBackendProvider).isReady) {
      return const SizedBox.shrink();
    }

    final status = ref.watch(syncStatusProvider);
    final failedLast =
        ref.watch(syncReportProvider).value?.outcome == SyncOutcome.failed;

    final summary = switch (status) {
      SyncStatusBlocked(:final count) => l10n.syncBlocked(count),
      SyncStatusSignedOut() => l10n.syncSignedOut,
      SyncStatusPending(:final count) => l10n.syncPending(count),
      SyncStatusIdle() =>
        failedLast ? l10n.syncLastFailed : l10n.syncUpToDate,
    };

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(l10n.syncSection, style: theme.textTheme.titleSmall),
        ),
        ListTile(
          title: Text(summary),
          subtitle: status is SyncStatusBlocked
              ? Text(l10n.syncBlockedHint)
              : null,
          trailing: TextButton(
            // 막힌 항목은 시도 횟수를 되돌려야 다시 집힌다. 그냥 한 회차 더
            // 돌리는 것으로는 아무 일도 일어나지 않는다.
            onPressed: () => status is SyncStatusBlocked
                ? ref.read(retrySyncProvider)()
                : ref.read(syncSchedulerProvider).now(),
            child: Text(
              status is SyncStatusBlocked ? l10n.syncRetry : l10n.syncNow,
            ),
          ),
        ),
      ],
    );
  }
}

/// 목표 범위 선택.
///
/// **직접 입력을 받지 않는다.** 임의의 숫자를 넣게 하면 앱이 근거 없는 범위로
/// "범위 안 73%" 를 계속 그리게 되는데, 화면은 똑같이 그럴듯해 보인다.
/// 근거 있는 몇 개 중에서만 고르게 하고, 그 근거를 함께 적는다.
class _TargetRangeSection extends ConsumerWidget {
  const _TargetRangeSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final unit = ref.watch(displayUnitProvider);
    final selected =
        ref.watch(targetRangePresetProvider).value ?? TargetRangePreset.fallback;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            l10n.settingsTargetSection,
            style: theme.textTheme.titleSmall,
          ),
        ),
        RadioGroup<TargetRangePreset>(
          groupValue: selected,
          onChanged: (value) => _change(context, ref, value, unit),
          child: Column(
            children: [
              for (final preset in TargetRangePreset.values)
                RadioListTile<TargetRangePreset>(
                  value: preset,
                  title: Text(
                    // 범위 숫자를 이름과 함께 보여 준다. 이름만으로는 무엇을
                    // 고르는지 알 수 없다.
                    '${preset.label(l10n)}  ${preset.labelFor(unit)} '
                    '${unit.symbol}',
                  ),
                  subtitle: Text(preset.note(l10n)),
                ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(16),
          // 앱이 목표를 권하는 것처럼 읽히지 않게 하는 문구다. 지우지 말 것.
          child: Text(
            l10n.settingsTargetNote,
            style: theme.textTheme.bodySmall
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ),
      ],
    );
  }

  Future<void> _change(
    BuildContext context,
    WidgetRef ref,
    TargetRangePreset? preset,
    GlucoseUnit unit,
  ) async {
    if (preset == null) return;
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);

    await ref.read(settingsRepositoryProvider).setTargetRange(preset);

    messenger.showSnackBar(
      SnackBar(
        content: Text(
          l10n.settingsTargetChanged(
            '${preset.labelFor(unit)} ${unit.symbol}',
          ),
        ),
      ),
    );
  }
}
