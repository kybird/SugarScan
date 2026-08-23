// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for German (`de`).
class AppLocalizationsDe extends AppLocalizations {
  AppLocalizationsDe([String locale = 'de']) : super(locale);

  @override
  String get appTitle => 'SugarScan';

  @override
  String get navHome => 'Start';

  @override
  String get navHistory => 'Verlauf';

  @override
  String get navStats => 'Statistik';

  @override
  String get navSettings => 'Einstellungen';

  @override
  String get scanCta => 'Messgerät scannen';

  @override
  String get scanTitle => 'Messgerät einscannen';

  @override
  String get scanGuideHint =>
      'Passe das Display des Messgeräts in den Rahmen ein';

  @override
  String get manualEntryCta => 'Manuell eingeben';

  @override
  String get scanImportPhotoCta => 'Foto laden';

  @override
  String get scanImportPickTitle => 'Bild auswählen';

  @override
  String get scanImportNoImages => 'Keine PNG-Dateien in diesem Ordner.';

  @override
  String get ea1cLabel => 'Geschätzter A1c-Wert';

  @override
  String get ea1cEstimateBadge => 'Schätzwert';

  @override
  String ea1cInsufficientData(int readings, int days) {
    return 'Für eine Schätzung sind $readings Messungen über $days Tage nötig';
  }

  @override
  String get tagFasting => 'Nüchtern';

  @override
  String get tagPreMeal => 'Vor der Mahlzeit';

  @override
  String get tagPostMeal => 'Nach der Mahlzeit';

  @override
  String get tagPostExercise => 'Nach dem Sport';

  @override
  String get tagBedtime => 'Vor dem Schlafengehen';

  @override
  String get tagRandom => 'Unbestimmt';

  @override
  String get scanReading => 'Lesen…';

  @override
  String get scanConfirmTitle => 'Messwert bestätigen';

  @override
  String get scanTagQuestion => 'Wann wurde gemessen?';

  @override
  String get actionSave => 'Speichern';

  @override
  String get actionCancel => 'Abbrechen';

  @override
  String get meterShowsHigh =>
      'Das Messgerät zeigt HI — über seinem messbaren Bereich.';

  @override
  String get meterShowsLow =>
      'Das Messgerät zeigt LO — unter seinem messbaren Bereich.';

  @override
  String get scanUnavailable =>
      'Das Scannen ist auf diesem Gerät nicht verfügbar. Du kannst den Wert manuell eingeben.';

  @override
  String get cameraPermissionRequired =>
      'Zum Scannen deines Messgeräts wird Kamerazugriff benötigt.';

  @override
  String readingSaved(String value, String unit) {
    return 'Gespeichert: $value $unit';
  }

  @override
  String get manualEntryTitle => 'Messwert eingeben';

  @override
  String get valueLabel => 'Blutzucker';

  @override
  String get invalidValueEmpty => 'Gib einen Wert ein';

  @override
  String get invalidValueFormat => 'Gib eine Zahl ein';

  @override
  String get invalidValueDecimals =>
      'Diese Einheit verwendet keine Dezimalstellen';

  @override
  String get invalidValueRange =>
      'Das liegt außerhalb dessen, was ein Messgerät anzeigen kann';

  @override
  String get historyEmpty =>
      'Noch keine Messwerte. Scanne dein Messgerät oder gib einen Wert ein.';

  @override
  String get readingsLoadFailed =>
      'Deine Messwerte konnten nicht geladen werden.';

  @override
  String get actionDelete => 'Löschen';

  @override
  String get actionUndo => 'Rückgängig';

  @override
  String get readingDeleted => 'Messwert gelöscht';

  @override
  String get recentReadings => 'Zuletzt';

  @override
  String get sourceOcr => 'Gescannt';

  @override
  String get sourceManual => 'Manuell';

  @override
  String get sourceBle => 'Bluetooth';

  @override
  String get sourceHealthSync => 'Health-App';

  @override
  String get sourceImport => 'Importiert';

  @override
  String get onboardingUnitTitle => 'Welche Einheit verwendet dein Messgerät?';

  @override
  String get onboardingUnitBody =>
      'Schau auf das Display deines Messgeräts und wähle die angezeigte Einheit.';

  @override
  String get onboardingUnitWarning =>
      'Das ist wichtig: Dieselbe Zahl bedeutet in jeder Einheit etwas ganz anderes. Ein Wert von 40 ist in mg/dL sehr niedrig, und in mmol/L sehr hoch.';

  @override
  String get unitExampleMgdl => 'Messwerte sehen so aus: 138';

  @override
  String get unitExampleMmoll => 'Messwerte sehen so aus: 7.6';

  @override
  String get actionContinue => 'Weiter';

  @override
  String get settingsUnitSection => 'Anzeigeeinheit';

  @override
  String settingsUnitChanged(String unit) {
    return 'Anzeigeeinheit auf $unit geändert';
  }

  @override
  String get settingsUnitNote =>
      'Eine Änderung betrifft nur, wie Messwerte angezeigt werden. Gespeicherte Messwerte behalten die Einheit, in der sie eingegeben wurden.';

  @override
  String get medicalDisclaimer =>
      'SugarScan stellt keine medizinische Diagnose. Konsultiere vor Entscheidungen über die Behandlung immer eine Fachperson im Gesundheitswesen.';

  @override
  String get authSignInTitle => 'Sichere deine Messwerte';

  @override
  String get authSignInBody =>
      'Melde dich an, damit deine Messwerte gesichert und auf deinen anderen Geräten verfügbar sind.';

  @override
  String get authSignInGoogle => 'Mit Google fortfahren';

  @override
  String get authSignInFailed =>
      'Anmeldung fehlgeschlagen. Bitte erneut versuchen.';

  @override
  String get authSignInUnavailable =>
      'Die Anmeldung ist in diesem Build nicht verfügbar.';

  @override
  String get authSignOut => 'Abmelden';

  @override
  String authSignedInAs(String email) {
    return 'Angemeldet als $email';
  }

  @override
  String get authAccountSection => 'Konto';

  @override
  String get syncSection => 'Synchronisierung';

  @override
  String get syncUpToDate => 'Alles ist gesichert';

  @override
  String syncPending(int count) {
    return '$count warten auf den Upload';
  }

  @override
  String syncBlocked(int count) {
    return '$count Messwerte konnten nicht hochgeladen werden';
  }

  @override
  String get syncBlockedHint =>
      'Sie sind weiterhin auf diesem Gerät gespeichert.';

  @override
  String get syncSignedOut =>
      'Die Sicherung ist pausiert, da du abgemeldet bist.';

  @override
  String get syncRetry => 'Erneut versuchen';

  @override
  String get syncNow => 'Jetzt synchronisieren';

  @override
  String get syncLastFailed => 'Der letzte Versuch ist fehlgeschlagen.';

  @override
  String get editReadingTitle => 'Messwert bearbeiten';

  @override
  String get editEnteredUnitLabel => 'Eingegeben in';

  @override
  String get editUnitWarning =>
      'Eine Änderung liest die eingegebene Zahl neu ein — sie wird nicht umgerechnet.';

  @override
  String editEquivalent(String value, String unit) {
    return 'Entspricht $value $unit';
  }

  @override
  String get noteLabel => 'Notiz (optional)';

  @override
  String get readingUpdated => 'Messwert aktualisiert';

  @override
  String get readingRestored => 'Messwert wiederhergestellt';

  @override
  String statsWindowDays(int days) {
    return '$days Tage';
  }

  @override
  String get statsEmpty => 'Keine Messwerte in diesem Zeitraum';

  @override
  String statsReadingCount(int count) {
    return '$count Messwerte';
  }

  @override
  String get statsMean => 'Durchschnitt';

  @override
  String get statsInRange => 'Im Zielbereich';

  @override
  String get statsInRangeNote =>
      'Zählt Messungen, nicht Zeit. Ein Blutzuckermesser mit Stechen erfasst einzelne Zeitpunkte und ist daher nicht mit der Time-in-Range eines CGM-Systems zu vergleichen.';

  @override
  String statsTargetRange(String range, String unit) {
    return 'Zielbereich $range $unit';
  }

  @override
  String get statsByTag => 'Durchschnitt je Kategorie';

  @override
  String get statsTrend => 'Messwerte im Zeitverlauf';

  @override
  String get statsLow => 'Tiefstwert';

  @override
  String get statsHigh => 'Höchstwert';

  @override
  String get statsSd => 'SD';

  @override
  String get settingsTargetSection => 'Zielbereich';

  @override
  String get targetObservation => 'Beobachtungsbereich';

  @override
  String get targetObservationNote =>
      'Der Bereich, der für die Time-in-Range-Auswertung verwendet wird.';

  @override
  String get targetPreMeal => 'Zielwert vor den Mahlzeiten';

  @override
  String get targetPreMealNote =>
      'ADA Standards of Care, nichtschwangere Erwachsene.';

  @override
  String get targetTight => 'Enger Bereich';

  @override
  String get targetTightNote =>
      'Der Bereich, in dem Menschen ohne Diabetes die meiste Zeit verbringen.';

  @override
  String get settingsTargetNote =>
      'Dies sind Referenzbereiche, keine Empfehlung. Lege dein eigenes Ziel mit deiner Behandlungsperson fest.';

  @override
  String settingsTargetChanged(String range) {
    return 'Zielbereich auf $range festgelegt';
  }
}
