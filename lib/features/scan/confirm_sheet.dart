import 'package:flutter/material.dart';

import '../../domain/models/glucose_unit.dart';
import '../../domain/models/measurement_tag.dart';
import '../../domain/services/glucose_validator.dart';
import '../../l10n/generated/app_localizations.dart';
import '../shared/tag_labels.dart';
import 'scan_entry.dart';

/// 저장 전 확인 시트.
///
/// 인식이 자동이어도 저장은 사용자의 1탭을 거친다. 이건 UX 취향이 아니라
/// 안전 요구사항이다 — 오독이 무확인으로 기록되면 사용자가 잘못된 추이를 보고
/// 행동을 바꿀 수 있고, "측정값을 앱이 판단한다"는 인상은 일반 건강관리 도구
/// 라는 제품 분류의 방어선을 무너뜨린다.
///
/// 값을 의심해서 묻는 것이 아니라, 자기 기록의 최종 결정권을 사용자에게
/// 두기 위해 존재한다.
Future<ScanEntry?> showConfirmSheet(
  BuildContext context, {
  required ScanEntry entry,
}) {
  return showModalBottomSheet<ScanEntry>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => _ConfirmSheet(entry: entry),
  );
}

class _ConfirmSheet extends StatefulWidget {
  const _ConfirmSheet({required this.entry});

  final ScanEntry entry;

  @override
  State<_ConfirmSheet> createState() => _ConfirmSheetState();
}

class _ConfirmSheetState extends State<_ConfirmSheet> {
  static const _validator = GlucoseValidator();

  late double _value = widget.entry.value;
  late MeasurementTag _tag = widget.entry.tag;
  bool _adjusted = false;

  /// 보정 한 걸음. 각 단위의 표시 해상도와 같게 둔다.
  double get _step => switch (widget.entry.unit) {
        GlucoseUnit.mgdl => 1,
        GlucoseUnit.mmoll => 0.1,
      };

  void _adjust(double delta) {
    final next = widget.entry.unit.roundForDisplay(_value + delta);
    if (!_validator.isInPhysicalRange(next, widget.entry.unit)) return;
    setState(() {
      _value = next;
      _adjusted = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final unit = widget.entry.unit;

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          bottom: 20 + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              l10n.scanConfirmTitle,
              style: theme.textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),

            // 값은 크게. 사용자가 확인해야 할 대상이 화면에서 가장 두드러져야 한다.
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton.filledTonal(
                  onPressed: () => _adjust(-_step),
                  icon: const Icon(Icons.remove),
                  tooltip: '-${unit.format(_step)}',
                ),
                Expanded(
                  child: Column(
                    children: [
                      Text(
                        unit.format(_value),
                        textAlign: TextAlign.center,
                        style: theme.textTheme.displayMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                      ),
                      Text(
                        unit.symbol,
                        style: theme.textTheme.labelLarge?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton.filledTonal(
                  onPressed: () => _adjust(_step),
                  icon: const Icon(Icons.add),
                  tooltip: '+${unit.format(_step)}',
                ),
              ],
            ),

            const SizedBox(height: 24),
            Text(l10n.scanTagQuestion, style: theme.textTheme.labelLarge),
            const SizedBox(height: 8),

            // 추천 태그는 미리 선택된 상태로 두되 자동 확정하지 않는다.
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final tag in MeasurementTag.values)
                  ChoiceChip(
                    label: Text(tag.label(l10n)),
                    selected: _tag == tag,
                    onSelected: (_) => setState(() => _tag = tag),
                  ),
              ],
            ),

            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: Text(l10n.actionCancel),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: FilledButton(
                    onPressed: () => Navigator.of(context).pop(
                      widget.entry.copyWith(
                        value: _value,
                        tag: _tag,
                        adjustedByUser: _adjusted,
                      ),
                    ),
                    child: Text(l10n.actionSave),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 16),
            Text(
              l10n.medicalDisclaimer,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
