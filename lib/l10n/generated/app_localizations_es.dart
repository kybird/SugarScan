// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Spanish Castilian (`es`).
class AppLocalizationsEs extends AppLocalizations {
  AppLocalizationsEs([String locale = 'es']) : super(locale);

  @override
  String get appTitle => 'SugarScan';

  @override
  String get navHome => 'Inicio';

  @override
  String get navHistory => 'Historial';

  @override
  String get navStats => 'Estadísticas';

  @override
  String get navSettings => 'Ajustes';

  @override
  String get scanCta => 'Escanear glucómetro';

  @override
  String get scanTitle => 'Escanea tu glucómetro';

  @override
  String get scanGuideHint =>
      'Ajusta la pantalla del glucómetro dentro del marco';

  @override
  String get manualEntryCta => 'Introducir a mano';

  @override
  String get scanImportPhotoCta => 'Cargar foto';

  @override
  String get scanImportPickTitle => 'Elegir una imagen';

  @override
  String get scanImportNoImages => 'No hay archivos PNG en esta carpeta.';

  @override
  String get ea1cLabel => 'A1c estimada';

  @override
  String get ea1cEstimateBadge => 'Estimación';

  @override
  String ea1cInsufficientData(int readings, int days) {
    return 'Se necesitan $readings mediciones a lo largo de $days días para estimar';
  }

  @override
  String get tagFasting => 'Ayuno';

  @override
  String get tagPreMeal => 'Antes de comer';

  @override
  String get tagPostMeal => 'Después de comer';

  @override
  String get tagPostExercise => 'Después de hacer ejercicio';

  @override
  String get tagBedtime => 'Al acostarse';

  @override
  String get tagRandom => 'Sin especificar';

  @override
  String get scanReading => 'Leyendo…';

  @override
  String get scanConfirmTitle => 'Confirma la lectura';

  @override
  String get scanTagQuestion => '¿Cuándo se midió?';

  @override
  String get actionSave => 'Guardar';

  @override
  String get actionCancel => 'Cancelar';

  @override
  String get meterShowsHigh =>
      'El glucómetro muestra HI: está por encima de su rango medible.';

  @override
  String get meterShowsLow =>
      'El glucómetro muestra LO: está por debajo de su rango medible.';

  @override
  String get scanUnavailable =>
      'El escaneo no está disponible en este dispositivo. Puedes introducir el valor a mano.';

  @override
  String get cameraPermissionRequired =>
      'Se necesita acceso a la cámara para escanear tu glucómetro.';

  @override
  String readingSaved(String value, String unit) {
    return 'Guardado: $value $unit';
  }

  @override
  String get manualEntryTitle => 'Introducir lectura';

  @override
  String get valueLabel => 'Glucemia';

  @override
  String get invalidValueEmpty => 'Introduce un valor';

  @override
  String get invalidValueFormat => 'Introduce un número';

  @override
  String get invalidValueDecimals => 'Esta unidad no usa decimales';

  @override
  String get invalidValueRange =>
      'Eso está fuera de lo que un glucómetro puede mostrar';

  @override
  String get historyEmpty =>
      'Aún no hay lecturas. Escanea tu glucómetro o introduce un valor.';

  @override
  String get readingsLoadFailed => 'No se pudieron cargar tus lecturas.';

  @override
  String get actionDelete => 'Eliminar';

  @override
  String get actionUndo => 'Deshacer';

  @override
  String get readingDeleted => 'Lectura eliminada';

  @override
  String get recentReadings => 'Recientes';

  @override
  String get sourceOcr => 'Escaneado';

  @override
  String get sourceManual => 'Manual';

  @override
  String get sourceBle => 'Bluetooth';

  @override
  String get sourceHealthSync => 'App de salud';

  @override
  String get sourceImport => 'Importado';

  @override
  String get onboardingUnitTitle => '¿Qué unidad usa tu glucómetro?';

  @override
  String get onboardingUnitBody =>
      'Mira la pantalla de tu glucómetro y elige la unidad que muestra.';

  @override
  String get onboardingUnitWarning =>
      'Esto importa: el mismo número significa cosas muy distintas en cada unidad. Una lectura de 40 es muy baja en mg/dL, y muy alta en mmol/L.';

  @override
  String get unitExampleMgdl => 'Las lecturas se ven así: 138';

  @override
  String get unitExampleMmoll => 'Las lecturas se ven así: 7.6';

  @override
  String get actionContinue => 'Continuar';

  @override
  String get settingsUnitSection => 'Unidad de visualización';

  @override
  String settingsUnitChanged(String unit) {
    return 'Unidad de visualización cambiada a $unit';
  }

  @override
  String get settingsUnitNote =>
      'Cambiar esto solo afecta a cómo se muestran las lecturas. Las lecturas guardadas conservan la unidad con la que se introdujeron.';

  @override
  String get medicalDisclaimer =>
      'SugarScan no proporciona un diagnóstico médico. Consulte siempre a un profesional sanitario antes de tomar decisiones sobre el tratamiento.';

  @override
  String get authSignInTitle => 'Mantén tus lecturas a salvo';

  @override
  String get authSignInBody =>
      'Inicia sesión para que tus lecturas se respalden y estén disponibles en tus otros dispositivos.';

  @override
  String get authSignInGoogle => 'Continuar con Google';

  @override
  String get authSignInFailed =>
      'No se pudo iniciar sesión. Inténtalo de nuevo.';

  @override
  String get authSignInUnavailable =>
      'El inicio de sesión no está disponible en esta compilación.';

  @override
  String get authSignOut => 'Cerrar sesión';

  @override
  String authSignedInAs(String email) {
    return 'Sesión iniciada como $email';
  }

  @override
  String get authAccountSection => 'Cuenta';

  @override
  String get syncSection => 'Sincronización';

  @override
  String get syncUpToDate => 'Todo está respaldado';

  @override
  String syncPending(int count) {
    return '$count en espera de subirse';
  }

  @override
  String syncBlocked(int count) {
    return 'No se pudieron subir $count lecturas';
  }

  @override
  String get syncBlockedHint => 'Sigue guardado en este dispositivo.';

  @override
  String get syncSignedOut =>
      'La copia de seguridad está en pausa porque has cerrado sesión.';

  @override
  String get syncRetry => 'Reintentar';

  @override
  String get syncNow => 'Sincronizar ahora';

  @override
  String get syncLastFailed => 'El último intento falló.';

  @override
  String get editReadingTitle => 'Editar lectura';

  @override
  String get editEnteredUnitLabel => 'Introducida en';

  @override
  String get editUnitWarning =>
      'Cambiar esto interpreta de nuevo el número que escribiste: no lo convierte.';

  @override
  String editEquivalent(String value, String unit) {
    return 'Equivale a $value $unit';
  }

  @override
  String get noteLabel => 'Nota (opcional)';

  @override
  String get readingUpdated => 'Lectura actualizada';

  @override
  String get readingRestored => 'Lectura restaurada';

  @override
  String statsWindowDays(int days) {
    return '$days días';
  }

  @override
  String get statsEmpty => 'No hay lecturas en este periodo';

  @override
  String statsReadingCount(int count) {
    return '$count lecturas';
  }

  @override
  String get statsMean => 'Promedio';

  @override
  String get statsInRange => 'Dentro del rango objetivo';

  @override
  String get statsInRangeNote =>
      'Cuenta mediciones, no tiempo. Un glucómetro de punción capilar toma muestras puntuales, por lo que esto no equivale al tiempo en rango de un sensor continuo (MCG).';

  @override
  String statsTargetRange(String range, String unit) {
    return 'Rango objetivo $range $unit';
  }

  @override
  String get statsByTag => 'Promedio por categoría';

  @override
  String get statsTrend => 'Lecturas en el tiempo';

  @override
  String get statsLow => 'Mínimo';

  @override
  String get statsHigh => 'Máximo';

  @override
  String get statsSd => 'DE';

  @override
  String get settingsTargetSection => 'Rango objetivo';

  @override
  String get targetObservation => 'Rango de observación';

  @override
  String get targetObservationNote =>
      'El rango que se usa para el informe de tiempo en rango.';

  @override
  String get targetPreMeal => 'Objetivo antes de las comidas';

  @override
  String get targetPreMealNote =>
      'ADA Standards of Care, adultos no embarazados.';

  @override
  String get targetTight => 'Rango estrecho';

  @override
  String get targetTightNote =>
      'Donde las personas sin diabetes pasan la mayor parte del tiempo.';

  @override
  String get settingsTargetNote =>
      'Estos son rangos de referencia, no consejos. Acuerda tu propio objetivo con tu profesional sanitario.';

  @override
  String settingsTargetChanged(String range) {
    return 'Rango objetivo fijado en $range';
  }
}
