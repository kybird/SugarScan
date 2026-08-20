// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Korean (`ko`).
class AppLocalizationsKo extends AppLocalizations {
  AppLocalizationsKo([String locale = 'ko']) : super(locale);

  @override
  String get appTitle => 'sugarScan';

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
  String get unitLabel => '표시 단위';

  @override
  String get unitMgdl => 'mg/dL';

  @override
  String get unitMmoll => 'mmol/L';

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
  String get actionRetry => '다시 스캔';

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
  String get medicalDisclaimer =>
      'sugarScan은 의학적 진단을 제공하지 않습니다. 치료 결정 시 반드시 전문 의료진과 상담하세요.';

  @override
  String comingSoon(String phase) {
    return '$phase에 구현 예정';
  }
}
