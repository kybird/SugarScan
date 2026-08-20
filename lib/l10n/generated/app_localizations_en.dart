// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'sugarScan';

  @override
  String get navHome => 'Home';

  @override
  String get navHistory => 'History';

  @override
  String get navStats => 'Stats';

  @override
  String get navSettings => 'Settings';

  @override
  String get scanCta => 'Scan meter';

  @override
  String get scanTitle => 'Scan your meter';

  @override
  String get scanGuideHint => 'Fit the meter display inside the frame';

  @override
  String get manualEntryCta => 'Enter manually';

  @override
  String get unitLabel => 'Unit';

  @override
  String get unitMgdl => 'mg/dL';

  @override
  String get unitMmoll => 'mmol/L';

  @override
  String get ea1cLabel => 'Estimated A1c';

  @override
  String get ea1cEstimateBadge => 'Estimate';

  @override
  String ea1cInsufficientData(int readings, int days) {
    return 'Need $readings readings across $days days to estimate';
  }

  @override
  String get tagFasting => 'Fasting';

  @override
  String get tagPreMeal => 'Before meal';

  @override
  String get tagPostMeal => 'After meal';

  @override
  String get tagPostExercise => 'After exercise';

  @override
  String get tagBedtime => 'Bedtime';

  @override
  String get tagRandom => 'Unspecified';

  @override
  String get scanReading => 'Reading…';

  @override
  String get scanConfirmTitle => 'Confirm reading';

  @override
  String get scanTagQuestion => 'When was this measured?';

  @override
  String get actionSave => 'Save';

  @override
  String get actionCancel => 'Cancel';

  @override
  String get actionRetry => 'Scan again';

  @override
  String get meterShowsHigh =>
      'The meter shows HI — above its measurable range.';

  @override
  String get meterShowsLow =>
      'The meter shows LO — below its measurable range.';

  @override
  String get scanUnavailable =>
      'Scanning is not available on this device. You can enter the value manually.';

  @override
  String get cameraPermissionRequired =>
      'Camera access is needed to scan your meter.';

  @override
  String readingSaved(String value, String unit) {
    return 'Saved $value $unit';
  }

  @override
  String get manualEntryTitle => 'Enter reading';

  @override
  String get valueLabel => 'Blood glucose';

  @override
  String get invalidValueEmpty => 'Enter a value';

  @override
  String get invalidValueFormat => 'Enter a number';

  @override
  String get invalidValueDecimals => 'This unit does not use decimals';

  @override
  String get invalidValueRange => 'That is outside what a meter can show';

  @override
  String get historyEmpty =>
      'No readings yet. Scan your meter or enter a value.';

  @override
  String get actionDelete => 'Delete';

  @override
  String get actionUndo => 'Undo';

  @override
  String get readingDeleted => 'Reading deleted';

  @override
  String get recentReadings => 'Recent';

  @override
  String get sourceOcr => 'Scanned';

  @override
  String get sourceManual => 'Manual';

  @override
  String get sourceBle => 'Bluetooth';

  @override
  String get sourceHealthSync => 'Health app';

  @override
  String get sourceImport => 'Imported';

  @override
  String get medicalDisclaimer =>
      'sugarScan does not provide a medical diagnosis. Always consult a healthcare professional before making treatment decisions.';

  @override
  String comingSoon(String phase) {
    return 'Coming in $phase';
  }
}
