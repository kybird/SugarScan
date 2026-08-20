// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'SugarScan';

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
  String get onboardingUnitTitle => 'Which unit does your meter use?';

  @override
  String get onboardingUnitBody =>
      'Look at your meter\'s display. Pick the unit it shows.';

  @override
  String get onboardingUnitWarning =>
      'This matters: the same number means very different things in each unit. A reading of 40 is very low in mg/dL, and very high in mmol/L.';

  @override
  String get unitExampleMgdl => 'Readings look like 138';

  @override
  String get unitExampleMmoll => 'Readings look like 7.6';

  @override
  String get actionContinue => 'Continue';

  @override
  String get settingsUnitSection => 'Display unit';

  @override
  String settingsUnitChanged(String unit) {
    return 'Display unit changed to $unit';
  }

  @override
  String get settingsUnitNote =>
      'Changing this only affects how readings are shown. Saved readings keep the unit they were entered in.';

  @override
  String get medicalDisclaimer =>
      'SugarScan does not provide a medical diagnosis. Always consult a healthcare professional before making treatment decisions.';

  @override
  String comingSoon(String phase) {
    return 'Coming in $phase';
  }

  @override
  String get authSignInTitle => 'Keep your readings safe';

  @override
  String get authSignInBody =>
      'Sign in so your readings are backed up and available on your other devices.';

  @override
  String get authSignInGoogle => 'Continue with Google';

  @override
  String get authSignInFailed => 'Couldn\'t sign in. Please try again.';

  @override
  String get authSignInUnavailable => 'Sign-in is not available in this build.';

  @override
  String get authSignOut => 'Sign out';

  @override
  String authSignedInAs(String email) {
    return 'Signed in as $email';
  }

  @override
  String get authAccountSection => 'Account';

  @override
  String get syncSection => 'Sync';

  @override
  String get syncUpToDate => 'Everything is backed up';

  @override
  String syncPending(int count) {
    return '$count waiting to upload';
  }

  @override
  String syncBlocked(int count) {
    return 'Couldn\'t upload $count readings';
  }

  @override
  String get syncBlockedHint => 'They are still saved on this device.';

  @override
  String get syncSignedOut => 'Backup is paused because you are signed out.';

  @override
  String get syncRetry => 'Try again';

  @override
  String get syncNow => 'Sync now';

  @override
  String get syncLastFailed => 'Last attempt failed.';

  @override
  String get editReadingTitle => 'Edit reading';

  @override
  String get editEnteredUnitLabel => 'Entered in';

  @override
  String get editUnitWarning =>
      'Changing this reinterprets the number you typed — it does not convert it.';

  @override
  String editEquivalent(String value, String unit) {
    return 'Same as $value $unit';
  }

  @override
  String get noteLabel => 'Note (optional)';

  @override
  String get readingUpdated => 'Reading updated';

  @override
  String get readingRestored => 'Reading restored';
}
