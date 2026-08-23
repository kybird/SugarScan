// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for French (`fr`).
class AppLocalizationsFr extends AppLocalizations {
  AppLocalizationsFr([String locale = 'fr']) : super(locale);

  @override
  String get appTitle => 'SugarScan';

  @override
  String get navHome => 'Accueil';

  @override
  String get navHistory => 'Historique';

  @override
  String get navStats => 'Statistiques';

  @override
  String get navSettings => 'Réglages';

  @override
  String get scanCta => 'Scanner le lecteur';

  @override
  String get scanTitle => 'Scannez votre lecteur';

  @override
  String get scanGuideHint => 'Placez l\'écran du lecteur dans le cadre';

  @override
  String get manualEntryCta => 'Saisie manuelle';

  @override
  String get scanImportPhotoCta => 'Charger une photo';

  @override
  String get scanImportPickTitle => 'Choisir une image';

  @override
  String get scanImportNoImages => 'Aucun fichier PNG dans ce dossier.';

  @override
  String get ea1cLabel => 'A1c estimée';

  @override
  String get ea1cEstimateBadge => 'Estimation';

  @override
  String ea1cInsufficientData(int readings, int days) {
    return 'Il faut $readings mesures sur $days jours pour l\'estimer';
  }

  @override
  String get tagFasting => 'À jeun';

  @override
  String get tagPreMeal => 'Avant le repas';

  @override
  String get tagPostMeal => 'Après le repas';

  @override
  String get tagPostExercise => 'Après l\'effort';

  @override
  String get tagBedtime => 'Au coucher';

  @override
  String get tagRandom => 'Non précisé';

  @override
  String get scanReading => 'Lecture…';

  @override
  String get scanConfirmTitle => 'Confirmez la valeur';

  @override
  String get scanTagQuestion => 'Quand a été prise cette mesure ?';

  @override
  String get actionSave => 'Enregistrer';

  @override
  String get actionCancel => 'Annuler';

  @override
  String get meterShowsHigh =>
      'Le lecteur affiche HI — au-dessus de sa plage mesurable.';

  @override
  String get meterShowsLow =>
      'Le lecteur affiche LO — en dessous de sa plage mesurable.';

  @override
  String get scanUnavailable =>
      'Le scan n\'est pas disponible sur cet appareil. Vous pouvez saisir la valeur manuellement.';

  @override
  String get cameraPermissionRequired =>
      'L\'accès à la caméra est nécessaire pour scanner votre lecteur.';

  @override
  String readingSaved(String value, String unit) {
    return 'Enregistré : $value $unit';
  }

  @override
  String get manualEntryTitle => 'Saisir la valeur';

  @override
  String get valueLabel => 'Glycémie';

  @override
  String get invalidValueEmpty => 'Saisissez une valeur';

  @override
  String get invalidValueFormat => 'Saisissez un nombre';

  @override
  String get invalidValueDecimals => 'Cette unité n\'utilise pas de décimales';

  @override
  String get invalidValueRange =>
      'C\'est en dehors de ce qu\'un lecteur peut afficher';

  @override
  String get historyEmpty =>
      'Aucune mesure pour l\'instant. Scannez votre lecteur ou saisissez une valeur.';

  @override
  String get readingsLoadFailed => 'Impossible de charger vos mesures.';

  @override
  String get actionDelete => 'Supprimer';

  @override
  String get actionUndo => 'Annuler';

  @override
  String get readingDeleted => 'Mesure supprimée';

  @override
  String get recentReadings => 'Récentes';

  @override
  String get sourceOcr => 'Scannée';

  @override
  String get sourceManual => 'Manuelle';

  @override
  String get sourceBle => 'Bluetooth';

  @override
  String get sourceHealthSync => 'App Santé';

  @override
  String get sourceImport => 'Importée';

  @override
  String get onboardingUnitTitle => 'Quelle unité utilise votre lecteur ?';

  @override
  String get onboardingUnitBody =>
      'Regardez l\'écran de votre lecteur et choisissez l\'unité qu\'il affiche.';

  @override
  String get onboardingUnitWarning =>
      'C\'est important : le même nombre signifie des choses très différentes selon l\'unité. Une valeur de 40 est très basse en mg/dL, et très élevée en mmol/L.';

  @override
  String get unitExampleMgdl => 'Les mesures ressemblent à ceci : 138';

  @override
  String get unitExampleMmoll => 'Les mesures ressemblent à ceci : 7.6';

  @override
  String get actionContinue => 'Continuer';

  @override
  String get settingsUnitSection => 'Unité d\'affichage';

  @override
  String settingsUnitChanged(String unit) {
    return 'Unité d\'affichage changée en $unit';
  }

  @override
  String get settingsUnitNote =>
      'Changer ceci affecte uniquement l\'affichage des mesures. Les mesures enregistrées conservent l\'unité dans laquelle elles ont été saisies.';

  @override
  String get medicalDisclaimer =>
      'SugarScan ne fournit pas de diagnostic médical. Consultez toujours un professionnel de santé avant de prendre des décisions de traitement.';

  @override
  String get authSignInTitle => 'Gardez vos mesures en sécurité';

  @override
  String get authSignInBody =>
      'Connectez-vous pour que vos mesures soient sauvegardées et disponibles sur vos autres appareils.';

  @override
  String get authSignInGoogle => 'Continuer avec Google';

  @override
  String get authSignInFailed => 'Connexion impossible. Veuillez réessayer.';

  @override
  String get authSignInUnavailable =>
      'La connexion n\'est pas disponible dans cette version.';

  @override
  String get authSignOut => 'Se déconnecter';

  @override
  String authSignedInAs(String email) {
    return 'Connecté en tant que $email';
  }

  @override
  String get authAccountSection => 'Compte';

  @override
  String get syncSection => 'Synchronisation';

  @override
  String get syncUpToDate => 'Tout est sauvegardé';

  @override
  String syncPending(int count) {
    return '$count en attente d\'envoi';
  }

  @override
  String syncBlocked(int count) {
    return '$count mesures n\'ont pas pu être envoyées';
  }

  @override
  String get syncBlockedHint => 'Elles restent enregistrées sur cet appareil.';

  @override
  String get syncSignedOut =>
      'La sauvegarde est en pause car vous êtes déconnecté.';

  @override
  String get syncRetry => 'Réessayer';

  @override
  String get syncNow => 'Synchroniser maintenant';

  @override
  String get syncLastFailed => 'La dernière tentative a échoué.';

  @override
  String get editReadingTitle => 'Modifier la mesure';

  @override
  String get editEnteredUnitLabel => 'Saisie en';

  @override
  String get editUnitWarning =>
      'Changer ceci réinterprète le nombre saisi — il n\'est pas converti.';

  @override
  String editEquivalent(String value, String unit) {
    return 'Équivaut à $value $unit';
  }

  @override
  String get noteLabel => 'Note (facultatif)';

  @override
  String get readingUpdated => 'Mesure mise à jour';

  @override
  String get readingRestored => 'Mesure restaurée';

  @override
  String statsWindowDays(int days) {
    return '$days jours';
  }

  @override
  String get statsEmpty => 'Aucune mesure sur cette période';

  @override
  String statsReadingCount(int count) {
    return '$count mesures';
  }

  @override
  String get statsMean => 'Moyenne';

  @override
  String get statsInRange => 'Dans la plage cible';

  @override
  String get statsInRangeNote =>
      'Compte des mesures, pas du temps. Un lecteur de glycémie à piqûre mesure des moments isolés, ce n\'est donc pas la même chose que le temps passé dans la cible d\'un capteur continu (MCG).';

  @override
  String statsTargetRange(String range, String unit) {
    return 'Plage cible $range $unit';
  }

  @override
  String get statsByTag => 'Moyenne par catégorie';

  @override
  String get statsTrend => 'Mesures dans le temps';

  @override
  String get statsLow => 'Minimum';

  @override
  String get statsHigh => 'Maximum';

  @override
  String get statsSd => 'ET';

  @override
  String get settingsTargetSection => 'Plage cible';

  @override
  String get targetObservation => 'Plage d\'observation';

  @override
  String get targetObservationNote =>
      'La plage utilisée pour le rapport de temps dans la cible.';

  @override
  String get targetPreMeal => 'Cible avant les repas';

  @override
  String get targetPreMealNote =>
      'ADA Standards of Care, adultes non enceintes.';

  @override
  String get targetTight => 'Plage serrée';

  @override
  String get targetTightNote =>
      'Là où les personnes sans diabète passent la plupart de leur temps.';

  @override
  String get settingsTargetNote =>
      'Ce sont des plages de référence, pas des conseils. Définissez votre propre cible avec votre professionnel de santé.';

  @override
  String settingsTargetChanged(String range) {
    return 'Plage cible définie sur $range';
  }
}
