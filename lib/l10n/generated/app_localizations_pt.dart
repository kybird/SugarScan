// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Portuguese (`pt`).
class AppLocalizationsPt extends AppLocalizations {
  AppLocalizationsPt([String locale = 'pt']) : super(locale);

  @override
  String get appTitle => 'SugarScan';

  @override
  String get navHome => 'Início';

  @override
  String get navHistory => 'Histórico';

  @override
  String get navStats => 'Estatísticas';

  @override
  String get navSettings => 'Configurações';

  @override
  String get scanCta => 'Escanear glicosímetro';

  @override
  String get scanTitle => 'Escaneie seu glicosímetro';

  @override
  String get scanGuideHint =>
      'Encaixe a tela do glicosímetro dentro da moldura';

  @override
  String get manualEntryCta => 'Digitar manualmente';

  @override
  String get scanImportPhotoCta => 'Carregar foto';

  @override
  String get scanImportPickTitle => 'Escolher uma imagem';

  @override
  String get scanImportNoImages => 'Não há arquivos PNG nesta pasta.';

  @override
  String get scanImportNoReading =>
      'Não foi possível ler um valor desta imagem. Tente outra.';

  @override
  String get ea1cLabel => 'A1c estimada';

  @override
  String get ea1cEstimateBadge => 'Estimativa';

  @override
  String ea1cInsufficientData(int readings, int days) {
    return 'São necessárias $readings medições ao longo de $days dias para estimar';
  }

  @override
  String get tagFasting => 'Em jejum';

  @override
  String get tagPreMeal => 'Antes da refeição';

  @override
  String get tagPostMeal => 'Depois da refeição';

  @override
  String get tagPostExercise => 'Depois do exercício';

  @override
  String get tagBedtime => 'Antes de dormir';

  @override
  String get tagRandom => 'Não especificado';

  @override
  String get scanReading => 'Lendo…';

  @override
  String get scanConfirmTitle => 'Confirme a leitura';

  @override
  String get scanTagQuestion => 'Quando isso foi medido?';

  @override
  String get actionSave => 'Salvar';

  @override
  String get actionCancel => 'Cancelar';

  @override
  String get meterShowsHigh =>
      'O glicosímetro exibe HI — está acima da faixa que ele consegue medir.';

  @override
  String get meterShowsLow =>
      'O glicosímetro exibe LO — está abaixo da faixa que ele consegue medir.';

  @override
  String get scanUnavailable =>
      'A digitalização não está disponível neste aparelho. Você pode digitar o valor manualmente.';

  @override
  String get cameraPermissionRequired =>
      'É preciso acesso à câmera para escanear seu glicosímetro.';

  @override
  String readingSaved(String value, String unit) {
    return 'Salvo: $value $unit';
  }

  @override
  String get manualEntryTitle => 'Digitar leitura';

  @override
  String get valueLabel => 'Glicemia';

  @override
  String get invalidValueEmpty => 'Digite um valor';

  @override
  String get invalidValueFormat => 'Digite um número';

  @override
  String get invalidValueDecimals => 'Esta unidade não usa decimais';

  @override
  String get invalidValueRange =>
      'Isso está fora do que um glicosímetro consegue exibir';

  @override
  String get historyEmpty =>
      'Ainda não há leituras. Escaneie seu glicosímetro ou digite um valor.';

  @override
  String get readingsLoadFailed => 'Não foi possível carregar suas leituras.';

  @override
  String get actionDelete => 'Excluir';

  @override
  String get actionUndo => 'Desfazer';

  @override
  String get readingDeleted => 'Leitura excluída';

  @override
  String get recentReadings => 'Recentes';

  @override
  String get sourceOcr => 'Digitalizado';

  @override
  String get sourceManual => 'Manual';

  @override
  String get sourceBle => 'Bluetooth';

  @override
  String get sourceHealthSync => 'App de saúde';

  @override
  String get sourceImport => 'Importado';

  @override
  String get onboardingUnitTitle => 'Qual unidade o seu glicosímetro usa?';

  @override
  String get onboardingUnitBody =>
      'Olhe a tela do seu glicosímetro e escolha a unidade que ela mostra.';

  @override
  String get onboardingUnitWarning =>
      'Isso importa: o mesmo número significa coisas muito diferentes em cada unidade. Uma leitura de 40 é muito baixa em mg/dL, e muito alta em mmol/L.';

  @override
  String get unitExampleMgdl => 'As leituras ficam assim: 138';

  @override
  String get unitExampleMmoll => 'As leituras ficam assim: 7.6';

  @override
  String get actionContinue => 'Continuar';

  @override
  String get settingsUnitSection => 'Unidade de exibição';

  @override
  String settingsUnitChanged(String unit) {
    return 'Unidade de exibição alterada para $unit';
  }

  @override
  String get settingsUnitNote =>
      'Mudar isso afeta apenas como as leituras são exibidas. As leituras salvas mantêm a unidade em que foram digitadas.';

  @override
  String get medicalDisclaimer =>
      'O SugarScan não fornece diagnóstico médico. Consulte sempre um profissional de saúde antes de tomar decisões sobre tratamento.';

  @override
  String get authSignInTitle => 'Mantenha suas leituras em segurança';

  @override
  String get authSignInBody =>
      'Entre na sua conta para que suas leituras tenham backup e fiquem disponíveis nos seus outros aparelhos.';

  @override
  String get authSignInGoogle => 'Continuar com o Google';

  @override
  String get authSignInFailed => 'Não foi possível entrar. Tente novamente.';

  @override
  String get authSignInUnavailable =>
      'O login não está disponível nesta versão.';

  @override
  String get authSignOut => 'Sair';

  @override
  String authSignedInAs(String email) {
    return 'Conectado como $email';
  }

  @override
  String get authAccountSection => 'Conta';

  @override
  String get syncSection => 'Sincronização';

  @override
  String get syncUpToDate => 'Está tudo com backup';

  @override
  String syncPending(int count) {
    return '$count aguardando para subir';
  }

  @override
  String syncBlocked(int count) {
    return 'Não foi possível subir $count leituras';
  }

  @override
  String get syncBlockedHint => 'Elas continuam salvas neste aparelho.';

  @override
  String get syncSignedOut =>
      'O backup está pausado porque você saiu da conta.';

  @override
  String get syncRetry => 'Tentar novamente';

  @override
  String get syncNow => 'Sincronizar agora';

  @override
  String get syncLastFailed => 'A última tentativa falhou.';

  @override
  String get editReadingTitle => 'Editar leitura';

  @override
  String get editEnteredUnitLabel => 'Digitada em';

  @override
  String get editUnitWarning =>
      'Mudar isso interpreta novamente o número que você digitou — ele não é convertido.';

  @override
  String editEquivalent(String value, String unit) {
    return 'Equivale a $value $unit';
  }

  @override
  String get noteLabel => 'Nota (opcional)';

  @override
  String get readingUpdated => 'Leitura atualizada';

  @override
  String get readingRestored => 'Leitura restaurada';

  @override
  String statsWindowDays(int days) {
    return '$days dias';
  }

  @override
  String get statsEmpty => 'Não há leituras neste período';

  @override
  String statsReadingCount(int count) {
    return '$count leituras';
  }

  @override
  String get statsMean => 'Média';

  @override
  String get statsInRange => 'Dentro da faixa-alvo';

  @override
  String get statsInRangeNote =>
      'Conta medições, não tempo. Um glicosímetro de punção capilar mede momentos isolados, então isso não é o mesmo que o tempo na faixa de um monitor contínuo (MCG).';

  @override
  String statsTargetRange(String range, String unit) {
    return 'Faixa-alvo $range $unit';
  }

  @override
  String get statsByTag => 'Média por categoria';

  @override
  String get statsTrend => 'Leituras ao longo do tempo';

  @override
  String get statsLow => 'Mínimo';

  @override
  String get statsHigh => 'Máximo';

  @override
  String get statsSd => 'DP';

  @override
  String get settingsTargetSection => 'Faixa-alvo';

  @override
  String get targetObservation => 'Faixa de observação';

  @override
  String get targetObservationNote =>
      'A faixa usada no relatório de tempo na faixa-alvo.';

  @override
  String get targetPreMeal => 'Meta antes das refeições';

  @override
  String get targetPreMealNote =>
      'ADA Standards of Care, adultos não gestantes.';

  @override
  String get targetTight => 'Faixa estreita';

  @override
  String get targetTightNote =>
      'Onde pessoas sem diabetes passam a maior parte do tempo.';

  @override
  String get settingsTargetNote =>
      'Estas são faixas de referência, não recomendações. Defina sua própria meta com seu profissional de saúde.';

  @override
  String settingsTargetChanged(String range) {
    return 'Faixa-alvo definida como $range';
  }
}
