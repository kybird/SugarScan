import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/models/glucose_unit.dart';
import '../../l10n/generated/app_localizations.dart';

/// 표시 단위 확인 화면.
///
/// 앱의 다른 어떤 화면보다 먼저 뜨고, 답하기 전에는 넘어갈 수 없다.
///
/// 로케일로 단위를 추정할 수는 있지만 그 추정을 확정으로 쓰지 않는 이유:
/// 검증기 범위상 **10~50 사이의 정수는 두 단위 모두에서 통과한다.** 같은 숫자가
/// mg/dL 로는 중증 저혈당, mmol/L 로는 중증 고혈당이다. 단위가 반대로 잡히면
/// 그 구간의 기록이 임상적으로 정반대 의미로 저장되고, 검증기도 안정화기도
/// 이 오류는 잡아내지 못한다. 물어보는 것이 유일한 방어다.
class UnitOnboardingScreen extends ConsumerStatefulWidget {
  const UnitOnboardingScreen({super.key});

  @override
  ConsumerState<UnitOnboardingScreen> createState() =>
      _UnitOnboardingScreenState();
}

class _UnitOnboardingScreenState extends ConsumerState<UnitOnboardingScreen> {
  GlucoseUnit? _selected;
  bool _saving = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    // 로케일 추정값을 미리 선택해 두되, 확정은 사용자의 탭으로만 이뤄진다.
    final GlucoseUnit selected =
        _selected ?? ref.watch(localeUnitGuessProvider);

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              Text(
                l10n.onboardingUnitTitle,
                style: theme.textTheme.headlineSmall
                    ?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              Text(
                l10n.onboardingUnitBody,
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
              const SizedBox(height: 24),
              for (final unit in GlucoseUnit.values) ...[
                _UnitOption(
                  unit: unit,
                  example: unit == GlucoseUnit.mgdl
                      ? l10n.unitExampleMgdl
                      : l10n.unitExampleMmoll,
                  selected: selected == unit,
                  onTap: () => setState(() => _selected = unit),
                ),
                const SizedBox(height: 12),
              ],
              const SizedBox(height: 12),
              _Warning(text: l10n.onboardingUnitWarning),
              const Spacer(),
              FilledButton(
                onPressed: _saving ? null : () => _confirm(selected),
                child: Text(l10n.actionContinue),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _confirm(GlucoseUnit unit) async {
    setState(() => _saving = true);
    await ref.read(settingsRepositoryProvider).confirmUnit(unit);
    // 저장이 끝나면 게이트가 스스로 열린다. 여기서 화면을 밀어내지 않는다.
  }
}

class _UnitOption extends StatelessWidget {
  const _UnitOption({
    required this.unit,
    required this.example,
    required this.selected,
    required this.onTap,
  });

  final GlucoseUnit unit;
  final String example;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final theme = Theme.of(context);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected ? scheme.primary : scheme.outlineVariant,
            width: selected ? 2 : 1,
          ),
          color: selected ? scheme.primaryContainer.withValues(alpha: 0.3) : null,
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    unit.symbol,
                    style: theme.textTheme.titleLarge
                        ?.copyWith(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 4),
                  // 숫자 예시를 보여 주는 것이 단위 이름보다 확실하다.
                  // 사용자는 자기 혈당계 화면과 눈으로 대조하면 된다.
                  Text(
                    example,
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(color: scheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
            Icon(
              selected ? Icons.radio_button_checked : Icons.radio_button_off,
              color: selected ? scheme.primary : scheme.outline,
            ),
          ],
        ),
      ),
    );
  }
}

class _Warning extends StatelessWidget {
  const _Warning({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, size: 20, color: scheme.onSurfaceVariant),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: Theme.of(context)
                  .textTheme
                  .bodySmall
                  ?.copyWith(color: scheme.onSurfaceVariant),
            ),
          ),
        ],
      ),
    );
  }
}
