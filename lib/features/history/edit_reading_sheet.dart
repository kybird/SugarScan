import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/result.dart';
import '../../domain/models/glucose_reading.dart';
import '../../domain/models/glucose_unit.dart';
import '../../domain/models/measurement_tag.dart';
import '../../domain/services/glucose_validator.dart';
import '../../l10n/generated/app_localizations.dart';
import '../shared/tag_labels.dart';

/// 편집 결과. 저장하지 않고 닫으면 null 이다.
class ReadingEdit {
  const ReadingEdit({
    required this.value,
    required this.unit,
    required this.tag,
    required this.note,
  });

  final double value;
  final GlucoseUnit unit;
  final MeasurementTag tag;

  /// 메모. **빈 문자열은 "지움"** 이다. 저장소가 null(바꾸지 않음)과 구분한다.
  final String note;
}

/// 기록 수정 시트.
///
/// 값을 **기록에 남아 있는 입력 단위**로 보여 준다. 화면 표시 단위로 보여 주면
/// mmol/L 로 넣은 7.6 이 mg/dL 사용자에게 137 로 보이고, 그걸 고쳐 저장하는
/// 순간 원본이 사라진다. 왕복 오차를 막으려고 `enteredUnit`/`enteredValue` 를
/// 따로 남겨 둔 의미가 없어진다.
Future<ReadingEdit?> showEditReadingSheet(
  BuildContext context, {
  required GlucoseReading reading,
}) {
  return showModalBottomSheet<ReadingEdit>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => _EditReadingSheet(reading: reading),
  );
}

class _EditReadingSheet extends StatefulWidget {
  const _EditReadingSheet({required this.reading});

  final GlucoseReading reading;

  @override
  State<_EditReadingSheet> createState() => _EditReadingSheetState();
}

class _EditReadingSheetState extends State<_EditReadingSheet> {
  static const _validator = GlucoseValidator();

  late final _controller = TextEditingController(
    text: widget.reading.enteredUnit.format(widget.reading.enteredValue),
  );
  late final _noteController =
      TextEditingController(text: widget.reading.note ?? '');

  late GlucoseUnit _unit = widget.reading.enteredUnit;
  late MeasurementTag _tag = widget.reading.tag;

  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    _noteController.dispose();
    super.dispose();
  }

  bool get _unitChanged => _unit != widget.reading.enteredUnit;

  /// 지금 입력값을 반대 단위로 환산한 문구.
  ///
  /// 단위를 잘못 고른 것을 사용자가 **눈으로** 알아채게 하는 장치다. mmol/L 값
  /// 7.6 을 mg/dL 로 두면 "0.4 mmol/L 에 해당"이 뜨는데, 자기 혈당계를 아는
  /// 사람에게는 이 줄이 즉시 이상하게 보인다. 앱이 옳고 그름을 판정하지
  /// 않으면서 사용자가 판단할 근거만 보여 주는 방식이다.
  String? _equivalentText(AppLocalizations l10n) {
    final parsed = _validator.parse(_controller.text, _unit);
    if (parsed is! Ok<double, GlucoseValidationFailure>) return null;

    final other = _unit == GlucoseUnit.mgdl
        ? GlucoseUnit.mmoll
        : GlucoseUnit.mgdl;
    final mgdl = _unit.toMgdl(parsed.value);
    return l10n.editEquivalent(other.format(other.fromMgdl(mgdl)), other.symbol);
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
    // 저장 경로와 **같은 검증기**를 쓴다. 수정으로 들어온 값이라고 해서
    // 물리적으로 불가능한 값이 통과하면 통계와 리포트가 조용히 망가진다.
    final result = _validator.parse(_controller.text, _unit);

    switch (result) {
      case Err(:final error):
        setState(() => _error = _messageFor(error, l10n));
      case Ok(:final value):
        Navigator.of(context).pop(
          ReadingEdit(
            value: value,
            unit: _unit,
            tag: _tag,
            note: _noteController.text.trim(),
          ),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final equivalent = _equivalentText(l10n);

    return SafeArea(
      child: SingleChildScrollView(
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
              l10n.editReadingTitle,
              style: theme.textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _controller,
              textAlign: TextAlign.center,
              style: theme.textTheme.displaySmall?.copyWith(
                fontWeight: FontWeight.w600,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
              keyboardType: TextInputType.numberWithOptions(
                decimal: _unit.displayFractionDigits > 0,
              ),
              inputFormatters: [
                FilteringTextInputFormatter.allow(
                  _unit.displayFractionDigits > 0
                      ? RegExp(r'[0-9.,]')
                      : RegExp(r'[0-9]'),
                ),
              ],
              decoration: InputDecoration(
                labelText: l10n.valueLabel,
                suffixText: _unit.symbol,
                errorText: _error,
                border: const OutlineInputBorder(),
              ),
              onChanged: (_) => setState(() => _error = null),
              onSubmitted: (_) => _submit(),
            ),
            if (equivalent != null) ...[
              const SizedBox(height: 8),
              Text(
                equivalent,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
            const SizedBox(height: 24),
            Text(l10n.editEnteredUnitLabel, style: theme.textTheme.labelLarge),
            const SizedBox(height: 8),
            SegmentedButton<GlucoseUnit>(
              segments: [
                for (final unit in GlucoseUnit.values)
                  ButtonSegment(value: unit, label: Text(unit.symbol)),
              ],
              selected: {_unit},
              onSelectionChanged: (selection) => setState(() {
                _unit = selection.first;
                _error = null;
              }),
            ),
            if (_unitChanged) ...[
              const SizedBox(height: 8),
              Text(
                l10n.editUnitWarning,
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.error),
              ),
            ],
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
            TextField(
              controller: _noteController,
              maxLines: 2,
              decoration: InputDecoration(
                labelText: l10n.noteLabel,
                border: const OutlineInputBorder(),
              ),
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
