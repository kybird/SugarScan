import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/local/database.dart';
import '../data/repositories/glucose_repository.dart';
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

/// 표시 단위.
///
/// 지금은 로케일에서 추정한다. 설정 화면(W11)이 붙으면 사용자가 고른 값이
/// 이 자리를 대신한다. **추정값을 그대로 확정하지 않는다** — 단위 오설정은
/// 이 앱에서 가장 위험한 UX 버그라, 온보딩에서 반드시 확인을 받아야 한다.
final displayUnitProvider = Provider<GlucoseUnit>((ref) {
  return defaultUnitForCountry(
    WidgetsBinding.instance.platformDispatcher.locale.countryCode,
  );
});
