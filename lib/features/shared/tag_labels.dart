import '../../domain/models/measurement_tag.dart';
import '../../domain/models/reading_source.dart';
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
