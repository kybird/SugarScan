import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/result.dart';
import '../../domain/models/glucose_unit.dart';
import '../../domain/models/measurement_tag.dart';
import '../../domain/models/reading_source.dart';
import '../../domain/services/glucose_validator.dart';
import '../../domain/services/tag_suggester.dart';
import '../../l10n/generated/app_localizations.dart';
import '../shared/tag_labels.dart';
import 'scan_entry.dart';

/// 직접 입력 시트.
///
/// 스캔이 어떤 이유로 막히든 — 카메라 권한 거부, 모델 없음, 저사양 기기,
/// 반사가 심한 화면 — 사용자는 항상 기록을 남길 수 있어야 한다. 이 경로가
/// 막히면 앱은 그 사용자에게 아무 쓸모가 없다.
Future<ScanEntry?> showManualEntrySheet(
  BuildContext context, {
  required GlucoseUnit unit,
}) {
  return showModalBottomSheet<ScanEntry>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => _ManualEntrySheet(unit: unit),
  );
}

class _ManualEntrySheet extends StatefulWidget {
  const _ManualEntrySheet({required this.unit});

  final GlucoseUnit unit;

  @override
  State<_ManualEntrySheet> createState() => _ManualEntrySheetState();
}

class _ManualEntrySheetState extends State<_ManualEntrySheet> {
  static const _validator = GlucoseValidator();

  final _controller = TextEditingController();
  final _focusNode = FocusNode();

  late MeasurementTag _tag =
      const TagSuggester().suggest(TagContext(localNow: DateTime.now()));

  String? _error;

  @override
  void initState() {
    super.initState();
    // 시트가 열리자마자 입력할 수 있게 한다. 스캔이 막혀서 온 경로라
    // 여기서 한 번 더 탭하게 만들 이유가 없다.
    WidgetsBinding.instance.addPostFrameCallback((_) => _focusNode.requestFocus());
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  String _messageFor(GlucoseValidationFailure failure, AppLocalizations l10n) =>
      switch (failure) {
        GlucoseValidationFailure.empty => l10n.invalidValueEmpty,
        GlucoseValidationFailure.notANumber => l10n.invalidValueFormat,
        GlucoseValidationFailure.unexpectedDecimals => l10n.invalidValueDecimals,
        GlucoseValidationFailure.outOfRange => l10n.invalidValueRange,
      };

  void _submit() {
    final l10n = AppLocalizations.of(context);
    // 스캔 경로와 **같은 검증기**를 쓴다. 손으로 넣었다고 해서 물리적으로
    // 불가능한 값이 통과하면 통계와 리포트가 조용히 망가진다.
    final result = _validator.parse(_controller.text, widget.unit);

    switch (result) {
      case Err(:final error):
        setState(() => _error = _messageFor(error, l10n));
      case Ok(:final value):
        Navigator.of(context).pop(
          ScanEntry(
            value: value,
            unit: widget.unit,
            tag: _tag,
            source: ReadingSource.manual,
          ),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

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
              l10n.manualEntryTitle,
              style: theme.textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _controller,
              focusNode: _focusNode,
              autofocus: true,
              textAlign: TextAlign.center,
              style: theme.textTheme.displaySmall?.copyWith(
                fontWeight: FontWeight.w600,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
              keyboardType: TextInputType.numberWithOptions(
                decimal: widget.unit.displayFractionDigits > 0,
              ),
              inputFormatters: [
                // 단위가 정수만 쓰면 소수점 자체를 못 넣게 한다. 넣은 뒤
                // 거절당하는 것보다 애초에 못 넣는 편이 낫다.
                FilteringTextInputFormatter.allow(
                  widget.unit.displayFractionDigits > 0
                      ? RegExp(r'[0-9.,]')
                      : RegExp(r'[0-9]'),
                ),
              ],
              decoration: InputDecoration(
                labelText: l10n.valueLabel,
                suffixText: widget.unit.symbol,
                errorText: _error,
                border: const OutlineInputBorder(),
              ),
              onChanged: (_) {
                if (_error != null) setState(() => _error = null);
              },
              onSubmitted: (_) => _submit(),
            ),
            const SizedBox(height: 24),
            Text(l10n.scanTagQuestion, style: theme.textTheme.labelLarge),
            const SizedBox(height: 8),
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
                    onPressed: _submit,
                    child: Text(l10n.actionSave),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
