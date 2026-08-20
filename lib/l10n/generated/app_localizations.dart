import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ko.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ko'),
  ];

  /// Application name. Not translated.
  ///
  /// In en, this message translates to:
  /// **'SugarScan'**
  String get appTitle;

  /// No description provided for @navHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get navHome;

  /// No description provided for @navHistory.
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get navHistory;

  /// No description provided for @navStats.
  ///
  /// In en, this message translates to:
  /// **'Stats'**
  String get navStats;

  /// No description provided for @navSettings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get navSettings;

  /// Primary action that opens the camera scanner.
  ///
  /// In en, this message translates to:
  /// **'Scan meter'**
  String get scanCta;

  /// No description provided for @scanTitle.
  ///
  /// In en, this message translates to:
  /// **'Scan your meter'**
  String get scanTitle;

  /// No description provided for @scanGuideHint.
  ///
  /// In en, this message translates to:
  /// **'Fit the meter display inside the frame'**
  String get scanGuideHint;

  /// No description provided for @manualEntryCta.
  ///
  /// In en, this message translates to:
  /// **'Enter manually'**
  String get manualEntryCta;

  /// No description provided for @unitLabel.
  ///
  /// In en, this message translates to:
  /// **'Unit'**
  String get unitLabel;

  /// No description provided for @unitMgdl.
  ///
  /// In en, this message translates to:
  /// **'mg/dL'**
  String get unitMgdl;

  /// No description provided for @unitMmoll.
  ///
  /// In en, this message translates to:
  /// **'mmol/L'**
  String get unitMmoll;

  /// No description provided for @ea1cLabel.
  ///
  /// In en, this message translates to:
  /// **'Estimated A1c'**
  String get ea1cLabel;

  /// No description provided for @ea1cEstimateBadge.
  ///
  /// In en, this message translates to:
  /// **'Estimate'**
  String get ea1cEstimateBadge;

  /// No description provided for @ea1cInsufficientData.
  ///
  /// In en, this message translates to:
  /// **'Need {readings} readings across {days} days to estimate'**
  String ea1cInsufficientData(int readings, int days);

  /// No description provided for @tagFasting.
  ///
  /// In en, this message translates to:
  /// **'Fasting'**
  String get tagFasting;

  /// No description provided for @tagPreMeal.
  ///
  /// In en, this message translates to:
  /// **'Before meal'**
  String get tagPreMeal;

  /// No description provided for @tagPostMeal.
  ///
  /// In en, this message translates to:
  /// **'After meal'**
  String get tagPostMeal;

  /// No description provided for @tagPostExercise.
  ///
  /// In en, this message translates to:
  /// **'After exercise'**
  String get tagPostExercise;

  /// No description provided for @tagBedtime.
  ///
  /// In en, this message translates to:
  /// **'Bedtime'**
  String get tagBedtime;

  /// No description provided for @tagRandom.
  ///
  /// In en, this message translates to:
  /// **'Unspecified'**
  String get tagRandom;

  /// No description provided for @scanReading.
  ///
  /// In en, this message translates to:
  /// **'Reading…'**
  String get scanReading;

  /// No description provided for @scanConfirmTitle.
  ///
  /// In en, this message translates to:
  /// **'Confirm reading'**
  String get scanConfirmTitle;

  /// No description provided for @scanTagQuestion.
  ///
  /// In en, this message translates to:
  /// **'When was this measured?'**
  String get scanTagQuestion;

  /// No description provided for @actionSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get actionSave;

  /// No description provided for @actionCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get actionCancel;

  /// No description provided for @actionRetry.
  ///
  /// In en, this message translates to:
  /// **'Scan again'**
  String get actionRetry;

  /// No description provided for @meterShowsHigh.
  ///
  /// In en, this message translates to:
  /// **'The meter shows HI — above its measurable range.'**
  String get meterShowsHigh;

  /// Descriptive only. Never advise the user what to do about it.
  ///
  /// In en, this message translates to:
  /// **'The meter shows LO — below its measurable range.'**
  String get meterShowsLow;

  /// No description provided for @scanUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Scanning is not available on this device. You can enter the value manually.'**
  String get scanUnavailable;

  /// No description provided for @cameraPermissionRequired.
  ///
  /// In en, this message translates to:
  /// **'Camera access is needed to scan your meter.'**
  String get cameraPermissionRequired;

  /// No description provided for @readingSaved.
  ///
  /// In en, this message translates to:
  /// **'Saved {value} {unit}'**
  String readingSaved(String value, String unit);

  /// No description provided for @manualEntryTitle.
  ///
  /// In en, this message translates to:
  /// **'Enter reading'**
  String get manualEntryTitle;

  /// No description provided for @valueLabel.
  ///
  /// In en, this message translates to:
  /// **'Blood glucose'**
  String get valueLabel;

  /// No description provided for @invalidValueEmpty.
  ///
  /// In en, this message translates to:
  /// **'Enter a value'**
  String get invalidValueEmpty;

  /// No description provided for @invalidValueFormat.
  ///
  /// In en, this message translates to:
  /// **'Enter a number'**
  String get invalidValueFormat;

  /// No description provided for @invalidValueDecimals.
  ///
  /// In en, this message translates to:
  /// **'This unit does not use decimals'**
  String get invalidValueDecimals;

  /// No description provided for @invalidValueRange.
  ///
  /// In en, this message translates to:
  /// **'That is outside what a meter can show'**
  String get invalidValueRange;

  /// No description provided for @historyEmpty.
  ///
  /// In en, this message translates to:
  /// **'No readings yet. Scan your meter or enter a value.'**
  String get historyEmpty;

  /// No description provided for @actionDelete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get actionDelete;

  /// No description provided for @actionUndo.
  ///
  /// In en, this message translates to:
  /// **'Undo'**
  String get actionUndo;

  /// No description provided for @readingDeleted.
  ///
  /// In en, this message translates to:
  /// **'Reading deleted'**
  String get readingDeleted;

  /// No description provided for @recentReadings.
  ///
  /// In en, this message translates to:
  /// **'Recent'**
  String get recentReadings;

  /// No description provided for @sourceOcr.
  ///
  /// In en, this message translates to:
  /// **'Scanned'**
  String get sourceOcr;

  /// No description provided for @sourceManual.
  ///
  /// In en, this message translates to:
  /// **'Manual'**
  String get sourceManual;

  /// No description provided for @sourceBle.
  ///
  /// In en, this message translates to:
  /// **'Bluetooth'**
  String get sourceBle;

  /// No description provided for @sourceHealthSync.
  ///
  /// In en, this message translates to:
  /// **'Health app'**
  String get sourceHealthSync;

  /// No description provided for @sourceImport.
  ///
  /// In en, this message translates to:
  /// **'Imported'**
  String get sourceImport;

  /// No description provided for @onboardingUnitTitle.
  ///
  /// In en, this message translates to:
  /// **'Which unit does your meter use?'**
  String get onboardingUnitTitle;

  /// No description provided for @onboardingUnitBody.
  ///
  /// In en, this message translates to:
  /// **'Look at your meter\'s display. Pick the unit it shows.'**
  String get onboardingUnitBody;

  /// Descriptive, not alarming. States the fact without telling the user what to do about it.
  ///
  /// In en, this message translates to:
  /// **'This matters: the same number means very different things in each unit. A reading of 40 is very low in mg/dL, and very high in mmol/L.'**
  String get onboardingUnitWarning;

  /// No description provided for @unitExampleMgdl.
  ///
  /// In en, this message translates to:
  /// **'Readings look like 138'**
  String get unitExampleMgdl;

  /// No description provided for @unitExampleMmoll.
  ///
  /// In en, this message translates to:
  /// **'Readings look like 7.6'**
  String get unitExampleMmoll;

  /// No description provided for @actionContinue.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get actionContinue;

  /// No description provided for @settingsUnitSection.
  ///
  /// In en, this message translates to:
  /// **'Display unit'**
  String get settingsUnitSection;

  /// No description provided for @settingsUnitChanged.
  ///
  /// In en, this message translates to:
  /// **'Display unit changed to {unit}'**
  String settingsUnitChanged(String unit);

  /// No description provided for @settingsUnitNote.
  ///
  /// In en, this message translates to:
  /// **'Changing this only affects how readings are shown. Saved readings keep the unit they were entered in.'**
  String get settingsUnitNote;

  /// Required notice. Must stay visible on onboarding, reports and settings.
  ///
  /// In en, this message translates to:
  /// **'SugarScan does not provide a medical diagnosis. Always consult a healthcare professional before making treatment decisions.'**
  String get medicalDisclaimer;

  /// No description provided for @authSignInTitle.
  ///
  /// In en, this message translates to:
  /// **'Keep your readings safe'**
  String get authSignInTitle;

  /// No description provided for @authSignInBody.
  ///
  /// In en, this message translates to:
  /// **'Sign in so your readings are backed up and available on your other devices.'**
  String get authSignInBody;

  /// No description provided for @authSignInGoogle.
  ///
  /// In en, this message translates to:
  /// **'Continue with Google'**
  String get authSignInGoogle;

  /// No description provided for @authSignInFailed.
  ///
  /// In en, this message translates to:
  /// **'Couldn\'t sign in. Please try again.'**
  String get authSignInFailed;

  /// Shown when the Google client ID or Supabase URL was not injected at build time.
  ///
  /// In en, this message translates to:
  /// **'Sign-in is not available in this build.'**
  String get authSignInUnavailable;

  /// No description provided for @authSignOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get authSignOut;

  /// No description provided for @authSignedInAs.
  ///
  /// In en, this message translates to:
  /// **'Signed in as {email}'**
  String authSignedInAs(String email);

  /// No description provided for @authAccountSection.
  ///
  /// In en, this message translates to:
  /// **'Account'**
  String get authAccountSection;

  /// No description provided for @syncSection.
  ///
  /// In en, this message translates to:
  /// **'Sync'**
  String get syncSection;

  /// No description provided for @syncUpToDate.
  ///
  /// In en, this message translates to:
  /// **'Everything is backed up'**
  String get syncUpToDate;

  /// No description provided for @syncPending.
  ///
  /// In en, this message translates to:
  /// **'{count} waiting to upload'**
  String syncPending(int count);

  /// Shown when entries exhausted their retry attempts. Must make clear nothing was lost.
  ///
  /// In en, this message translates to:
  /// **'Couldn\'t upload {count} readings'**
  String syncBlocked(int count);

  /// No description provided for @syncBlockedHint.
  ///
  /// In en, this message translates to:
  /// **'They are still saved on this device.'**
  String get syncBlockedHint;

  /// No description provided for @syncSignedOut.
  ///
  /// In en, this message translates to:
  /// **'Backup is paused because you are signed out.'**
  String get syncSignedOut;

  /// No description provided for @syncRetry.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get syncRetry;

  /// No description provided for @syncNow.
  ///
  /// In en, this message translates to:
  /// **'Sync now'**
  String get syncNow;

  /// No description provided for @syncLastFailed.
  ///
  /// In en, this message translates to:
  /// **'Last attempt failed.'**
  String get syncLastFailed;

  /// No description provided for @editReadingTitle.
  ///
  /// In en, this message translates to:
  /// **'Edit reading'**
  String get editReadingTitle;

  /// No description provided for @editEnteredUnitLabel.
  ///
  /// In en, this message translates to:
  /// **'Entered in'**
  String get editEnteredUnitLabel;

  /// Shown when the user switches the unit of an existing reading. The same digits mean opposite things in the two units, so this must not read like a conversion.
  ///
  /// In en, this message translates to:
  /// **'Changing this reinterprets the number you typed — it does not convert it.'**
  String get editUnitWarning;

  /// No description provided for @editEquivalent.
  ///
  /// In en, this message translates to:
  /// **'Same as {value} {unit}'**
  String editEquivalent(String value, String unit);

  /// No description provided for @noteLabel.
  ///
  /// In en, this message translates to:
  /// **'Note (optional)'**
  String get noteLabel;

  /// No description provided for @readingUpdated.
  ///
  /// In en, this message translates to:
  /// **'Reading updated'**
  String get readingUpdated;

  /// No description provided for @readingRestored.
  ///
  /// In en, this message translates to:
  /// **'Reading restored'**
  String get readingRestored;

  /// No description provided for @statsWindowDays.
  ///
  /// In en, this message translates to:
  /// **'{days} days'**
  String statsWindowDays(int days);

  /// No description provided for @statsEmpty.
  ///
  /// In en, this message translates to:
  /// **'No readings in this period'**
  String get statsEmpty;

  /// No description provided for @statsReadingCount.
  ///
  /// In en, this message translates to:
  /// **'{count} readings'**
  String statsReadingCount(int count);

  /// No description provided for @statsMean.
  ///
  /// In en, this message translates to:
  /// **'Average'**
  String get statsMean;

  /// Share of readings inside the user-set target range. Purely descriptive: never phrase this as normal, safe, or good.
  ///
  /// In en, this message translates to:
  /// **'Within target range'**
  String get statsInRange;

  /// No description provided for @statsInRangeNote.
  ///
  /// In en, this message translates to:
  /// **'Counts readings, not time. A finger-prick meter samples moments, so this is not the same as a CGM time-in-range.'**
  String get statsInRangeNote;

  /// No description provided for @statsTargetRange.
  ///
  /// In en, this message translates to:
  /// **'Target range {low}–{high} {unit}'**
  String statsTargetRange(String low, String high, String unit);

  /// No description provided for @statsByTag.
  ///
  /// In en, this message translates to:
  /// **'Average by tag'**
  String get statsByTag;

  /// No description provided for @statsTrend.
  ///
  /// In en, this message translates to:
  /// **'Readings over time'**
  String get statsTrend;

  /// No description provided for @statsLow.
  ///
  /// In en, this message translates to:
  /// **'Low'**
  String get statsLow;

  /// No description provided for @statsHigh.
  ///
  /// In en, this message translates to:
  /// **'High'**
  String get statsHigh;

  /// No description provided for @statsSd.
  ///
  /// In en, this message translates to:
  /// **'SD'**
  String get statsSd;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ko'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ko':
      return AppLocalizationsKo();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
