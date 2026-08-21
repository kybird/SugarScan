import '../../domain/models/measurement_tag.dart';
import '../../domain/models/reading_source.dart';
import '../../domain/models/target_range_preset.dart';
import '../../l10n/generated/app_localizations.dart';

extension MeasurementTagLabel on MeasurementTag {
  String label(AppLocalizations l10n) => switch (this) {
        MeasurementTag.fasting => l10n.tagFasting,
        MeasurementTag.preMeal => l10n.tagPreMeal,
        MeasurementTag.postMeal => l10n.tagPostMeal,
        MeasurementTag.postExercise => l10n.tagPostExercise,
        MeasurementTag.bedtime => l10n.tagBedtime,
        MeasurementTag.random => l10n.tagRandom,
      };
}

extension ReadingSourceLabel on ReadingSource {
  String label(AppLocalizations l10n) => switch (this) {
        ReadingSource.ocr => l10n.sourceOcr,
        ReadingSource.manual => l10n.sourceManual,
        ReadingSource.ble => l10n.sourceBle,
        ReadingSource.healthSync => l10n.sourceHealthSync,
        ReadingSource.import => l10n.sourceImport,
      };
}

/// 목표 범위 프리셋의 이름과 근거 한 줄.
///
/// 문구를 모델이 아니라 표시 계층에 둔다. `TargetRangePreset` 은 순수 Dart 라
/// l10n 을 알지 못하고, 알게 되는 순간 도메인이 UI 에 묶인다.
extension TargetRangePresetLabels on TargetRangePreset {
  String label(AppLocalizations l10n) => switch (this) {
        TargetRangePreset.observation => l10n.targetObservation,
        TargetRangePreset.preMeal => l10n.targetPreMeal,
        TargetRangePreset.tight => l10n.targetTight,
      };

  String note(AppLocalizations l10n) => switch (this) {
        TargetRangePreset.observation => l10n.targetObservationNote,
        TargetRangePreset.preMeal => l10n.targetPreMealNote,
        TargetRangePreset.tight => l10n.targetTightNote,
      };
}
