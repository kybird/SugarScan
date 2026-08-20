import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/local/database.dart';
import '../data/repositories/glucose_repository.dart';
import '../data/repositories/settings_repository.dart';
import '../data/system_timezone.dart';
import '../domain/models/glucose_reading.dart';
import '../domain/models/glucose_unit.dart';

/// 앱 전역 의존성.
///
/// Riverpod 코드 생성은 쓰지 않는다. `riverpod_generator` 가 요구하는 analyzer
/// 버전이 `drift_dev` 와 공존하지 못해서다(§15 W1). 프로바이더를 손으로 쓰면
/// 보일러플레이트가 조금 늘 뿐 기능 차이는 없다.
final databaseProvider = Provider<AppDatabase>((ref) {
  final db = AppDatabase();
  ref.onDispose(db.close);
  return db;
});

final glucoseRepositoryProvider = Provider<GlucoseRepository>((ref) {
  return GlucoseRepository(
    database: ref.watch(databaseProvider),
    resolveTzName: systemTimeZoneName,
  );
});

/// 최근 기록. Drift 가 변경을 흘려보내므로 저장 직후 화면이 알아서 갱신된다.
final recentReadingsProvider = StreamProvider<List<GlucoseReading>>((ref) {
  return ref.watch(glucoseRepositoryProvider).watchRecent();
});

final settingsRepositoryProvider = Provider<SettingsRepository>((ref) {
  return SettingsRepository(database: ref.watch(databaseProvider));
});

/// 로케일에서 추정한 단위.
///
/// **추정일 뿐이다.** 온보딩에서 미리 선택해 두는 용도로만 쓰고, 확인 없이
/// 저장 경로로 흘려보내지 않는다. 이유는 [unitPreferenceProvider] 참조.
final localeUnitGuessProvider = Provider<GlucoseUnit>((ref) {
  return defaultUnitForCountry(
    WidgetsBinding.instance.platformDispatcher.locale.countryCode,
  );
});

/// 사용자가 확인한 표시 단위 설정. 아직 고른 적이 없으면 null.
///
/// 검증기 범위상 10~50 사이의 정수는 두 단위 모두에서 통과한다. 같은 숫자가
/// mg/dL 로는 중증 저혈당, mmol/L 로는 중증 고혈당이다. 단위가 반대로 잡히면
/// 그 구간의 기록이 정반대 의미로 저장되므로, 확인 전에는 앱이 진행하지 않는다.
final unitPreferenceProvider = StreamProvider<UnitPreference?>((ref) {
  return ref.watch(settingsRepositoryProvider).watchUnitPreference();
});

/// 화면에 쓸 표시 단위.
///
/// 확인된 값이 없으면 추정값으로 떨어지지만, 그 상태에서는 온보딩 게이트가
/// 다른 화면을 막고 있으므로 실제 저장에는 쓰이지 않는다.
final displayUnitProvider = Provider<GlucoseUnit>((ref) {
  final preference = ref.watch(unitPreferenceProvider).value;
  return preference?.unit ?? ref.watch(localeUnitGuessProvider);
});
