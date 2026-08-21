// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Korean (`ko`).
class AppLocalizationsKo extends AppLocalizations {
  AppLocalizationsKo([String locale = 'ko']) : super(locale);

  @override
  String get appTitle => 'SugarScan';

  @override
  String get navHome => '홈';

  @override
  String get navHistory => '기록';

  @override
  String get navStats => '통계';

  @override
  String get navSettings => '설정';

  @override
  String get scanCta => '혈당기 스캔';

  @override
  String get scanTitle => '혈당기를 비춰 주세요';

  @override
  String get scanGuideHint => '혈당기 화면을 가이드 안에 맞춰 주세요';

  @override
  String get manualEntryCta => '직접 입력';

  @override
  String get ea1cLabel => '추정 당화혈색소';

  @override
  String get ea1cEstimateBadge => '추정치';

  @override
  String ea1cInsufficientData(int readings, int days) {
    return '$days일에 걸쳐 $readings회 이상 측정하면 추정할 수 있어요';
  }

  @override
  String get tagFasting => '공복';

  @override
  String get tagPreMeal => '식전';

  @override
  String get tagPostMeal => '식후';

  @override
  String get tagPostExercise => '운동 후';

  @override
  String get tagBedtime => '취침 전';

  @override
  String get tagRandom => '미지정';

  @override
  String get scanReading => '읽는 중…';

  @override
  String get scanConfirmTitle => '이 값이 맞나요?';

  @override
  String get scanTagQuestion => '언제 측정했나요?';

  @override
  String get actionSave => '저장';

  @override
  String get actionCancel => '취소';

  @override
  String get meterShowsHigh => '혈당계가 HI를 표시했습니다 — 측정 가능 범위를 넘었습니다.';

  @override
  String get meterShowsLow => '혈당계가 LO를 표시했습니다 — 측정 가능 범위 아래입니다.';

  @override
  String get scanUnavailable => '이 기기에서는 스캔을 사용할 수 없습니다. 직접 입력할 수 있어요.';

  @override
  String get cameraPermissionRequired => '혈당계를 스캔하려면 카메라 권한이 필요합니다.';

  @override
  String readingSaved(String value, String unit) {
    return '$value $unit 저장했습니다';
  }

  @override
  String get manualEntryTitle => '혈당 입력';

  @override
  String get valueLabel => '혈당';

  @override
  String get invalidValueEmpty => '값을 입력하세요';

  @override
  String get invalidValueFormat => '숫자를 입력하세요';

  @override
  String get invalidValueDecimals => '이 단위는 소수점을 쓰지 않습니다';

  @override
  String get invalidValueRange => '혈당계가 표시할 수 있는 범위를 벗어납니다';

  @override
  String get historyEmpty => '아직 기록이 없습니다. 혈당계를 스캔하거나 직접 입력해 보세요.';

  @override
  String get actionDelete => '삭제';

  @override
  String get actionUndo => '실행 취소';

  @override
  String get readingDeleted => '기록을 삭제했습니다';

  @override
  String get recentReadings => '최근 기록';

  @override
  String get sourceOcr => '스캔';

  @override
  String get sourceManual => '직접 입력';

  @override
  String get sourceBle => '블루투스';

  @override
  String get sourceHealthSync => '건강 앱';

  @override
  String get sourceImport => '가져오기';

  @override
  String get onboardingUnitTitle => '혈당계가 어떤 단위를 쓰나요?';

  @override
  String get onboardingUnitBody => '혈당계 화면을 보고 표시되는 단위를 골라 주세요.';

  @override
  String get onboardingUnitWarning =>
      '중요합니다. 같은 숫자라도 단위에 따라 뜻이 완전히 달라집니다. 40은 mg/dL에서는 매우 낮고, mmol/L에서는 매우 높습니다.';

  @override
  String get unitExampleMgdl => '이런 식으로 표시됩니다: 138';

  @override
  String get unitExampleMmoll => '이런 식으로 표시됩니다: 7.6';

  @override
  String get actionContinue => '계속';

  @override
  String get settingsUnitSection => '표시 단위';

  @override
  String settingsUnitChanged(String unit) {
    return '표시 단위를 $unit로 바꿨습니다';
  }

  @override
  String get settingsUnitNote =>
      '이 설정은 보여 주는 방식만 바꿉니다. 이미 저장된 기록은 입력 당시의 단위를 그대로 간직합니다.';

  @override
  String get medicalDisclaimer =>
      'SugarScan은 의학적 진단을 제공하지 않습니다. 치료 결정 시 반드시 전문 의료진과 상담하세요.';

  @override
  String get authSignInTitle => '기록을 안전하게 보관합니다';

  @override
  String get authSignInBody => '로그인하면 기록이 백업되고 다른 기기에서도 이어서 볼 수 있습니다.';

  @override
  String get authSignInGoogle => 'Google로 계속하기';

  @override
  String get authSignInFailed => '로그인하지 못했습니다. 다시 시도해 주세요.';

  @override
  String get authSignInUnavailable => '이 빌드에서는 로그인을 쓸 수 없습니다.';

  @override
  String get authSignOut => '로그아웃';

  @override
  String authSignedInAs(String email) {
    return '$email 로 로그인됨';
  }

  @override
  String get authAccountSection => '계정';

  @override
  String get syncSection => '동기화';

  @override
  String get syncUpToDate => '모두 백업되었습니다';

  @override
  String syncPending(int count) {
    return '$count건 대기 중';
  }

  @override
  String syncBlocked(int count) {
    return '$count건을 올리지 못했습니다';
  }

  @override
  String get syncBlockedHint => '기록은 이 기기에 그대로 있습니다.';

  @override
  String get syncSignedOut => '로그아웃 상태라 백업이 멈춰 있습니다.';

  @override
  String get syncRetry => '다시 시도';

  @override
  String get syncNow => '지금 동기화';

  @override
  String get syncLastFailed => '마지막 시도가 실패했습니다.';

  @override
  String get editReadingTitle => '기록 수정';

  @override
  String get editEnteredUnitLabel => '입력 단위';

  @override
  String get editUnitWarning => '단위를 바꾸면 입력한 숫자를 그 단위로 다시 읽습니다 — 값을 변환하지 않습니다.';

  @override
  String editEquivalent(String value, String unit) {
    return '$value $unit 에 해당';
  }

  @override
  String get noteLabel => '메모 (선택)';

  @override
  String get readingUpdated => '기록을 수정했습니다';

  @override
  String get readingRestored => '기록을 되살렸습니다';

  @override
  String statsWindowDays(int days) {
    return '$days일';
  }

  @override
  String get statsEmpty => '이 기간에 기록이 없습니다';

  @override
  String statsReadingCount(int count) {
    return '$count건';
  }

  @override
  String get statsMean => '평균';

  @override
  String get statsInRange => '목표 범위 안';

  @override
  String get statsInRangeNote =>
      '시간이 아니라 건수 기준입니다. 채혈 측정은 시점 표본이라 CGM 의 TIR 과 다릅니다.';

  @override
  String statsTargetRange(String range, String unit) {
    return '목표 범위 $range $unit';
  }

  @override
  String get statsByTag => '태그별 평균';

  @override
  String get statsTrend => '기간 내 기록';

  @override
  String get statsLow => '최저';

  @override
  String get statsHigh => '최고';

  @override
  String get statsSd => '편차';

  @override
  String get settingsTargetSection => '목표 범위';

  @override
  String get targetObservation => '관찰 범위';

  @override
  String get targetObservationNote => '범위 내 비율을 볼 때 쓰이는 구간입니다.';

  @override
  String get targetPreMeal => '식전 목표';

  @override
  String get targetPreMealNote => 'ADA Standards of Care, 비임신 성인 기준.';

  @override
  String get targetTight => '좁은 범위';

  @override
  String get targetTightNote => '당뇨가 없는 사람이 대부분의 시간을 보내는 구간입니다.';

  @override
  String get settingsTargetNote => '참고 범위일 뿐 권고가 아닙니다. 본인의 목표는 담당 의료진과 정하세요.';

  @override
  String settingsTargetChanged(String range) {
    return '목표 범위를 $range 로 바꿨습니다';
  }
}
