import '../../domain/models/measurement_tag.dart';
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
