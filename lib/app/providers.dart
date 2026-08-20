import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:drift/drift.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/local/database.dart';
import '../data/remote/auth_repository.dart';
import '../data/remote/google_auth_config.dart';
import '../data/remote/google_sign_in_flow.dart';
import '../data/remote/remote_backend.dart';
import '../data/sync/outbox_repository.dart';
import '../data/sync/reading_api.dart';
import '../data/sync/sync_cursor_store.dart';
import '../data/sync/sync_engine.dart';
import '../data/sync/sync_scheduler.dart';
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

/// 서버 연결 상태.
///
/// `main()` 이 `runApp` 앞에서 초기화한 결과를 override 로 넣는다. 기본값이
/// [RemoteDisabled] 인 것은 테스트 편의가 아니라 설계다 — 서버 없이 도는 상태가
/// 이 앱의 정상 상태 중 하나다.
final remoteBackendProvider = Provider<RemoteBackend>((ref) {
  return const RemoteDisabled();
});

/// Google 클라이언트 ID. 주입되지 않았으면 null.
final googleAuthConfigProvider = Provider<GoogleAuthConfig?>((ref) {
  return GoogleAuthConfig.fromEnvironment();
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final backend = ref.watch(remoteBackendProvider);
  final googleConfig = ref.watch(googleAuthConfigProvider);

  return AuthRepository(
    client: switch (backend) {
      RemoteReady(:final client) => client,
      RemoteDisabled() || RemoteFailed() => null,
    },
    idTokenProvider:
        googleConfig == null ? null : googleIdTokenProvider(googleConfig),
  );
});

/// 지금 로그인되어 있는지. 세션이 바뀔 때마다 다시 흘린다.
///
/// 스트림 이벤트 자체가 아니라 매번 `isSignedIn` 을 다시 읽는다. 토큰 갱신·
/// 로그아웃·복원이 각각 다른 이벤트로 오는데, 게이트가 알고 싶은 것은
/// "지금 세션이 있느냐" 하나뿐이라 이벤트 종류를 해석할 이유가 없다.
final signedInProvider = StreamProvider<bool>((ref) async* {
  final auth = ref.watch(authRepositoryProvider);
  yield auth.isSignedIn;
  await for (final _ in auth.authStateChanges) {
    yield auth.isSignedIn;
  }
});

/// 이 기기에서 로그인한 적이 있는지.
final signedInBeforeProvider = StreamProvider<bool>((ref) {
  return ref.watch(settingsRepositoryProvider).watchSignedInBefore();
});

/// 로그인 게이트가 앱을 막을지 여부.
enum AuthGateStatus { loading, allowed, requireSignIn }

/// 게이트 판정.
///
/// 막는 경우는 **하나뿐**이다: 서버가 설정된 빌드에서, 세션이 없고, 이 기기에서
/// 로그인한 적도 없을 때. 나머지는 전부 통과시킨다 —
/// - 서버 미설정 빌드: 로그인이라는 개념 자체가 없다. 막으면 앱이 벽돌이 된다.
/// - 세션 만료: 한 번 로그인했던 기기다. 오프라인에서 기록을 남기려는 사람을
///   로그인 화면으로 막지 않는다. 동기화만 세션이 돌아올 때까지 미뤄진다.
final authGateProvider = Provider<AuthGateStatus>((ref) {
  final backend = ref.watch(remoteBackendProvider);
  if (!backend.isReady) return AuthGateStatus.allowed;

  final signedIn = ref.watch(signedInProvider).value;
  final signedInBefore = ref.watch(signedInBeforeProvider).value;
  if (signedIn == null || signedInBefore == null) {
    return AuthGateStatus.loading;
  }

  return signedIn || signedInBefore
      ? AuthGateStatus.allowed
      : AuthGateStatus.requireSignIn;
});

// ── 동기화 ──────────────────────────────────────────────────────────────

final outboxRepositoryProvider = Provider<OutboxRepository>((ref) {
  return OutboxRepository(database: ref.watch(databaseProvider));
});

final syncCursorStoreProvider = Provider<SyncCursorStore>((ref) {
  return SyncCursorStore(database: ref.watch(databaseProvider));
});

/// 서버 표면. 접속 정보가 없는 빌드에서는 null.
final readingApiProvider = Provider<ReadingApi?>((ref) {
  final backend = ref.watch(remoteBackendProvider);
  return switch (backend) {
    RemoteReady(:final client) => SupabaseReadingApi(client: client),
    RemoteDisabled() || RemoteFailed() => null,
  };
});

/// 네트워크가 있는지.
///
/// 오프라인을 실패와 구분하기 위한 것이다. 엔진이 오프라인에서 시도 횟수를
/// 태우면 지하철을 여섯 번 타는 것만으로 아웃박스가 영구히 막힌다.
final isOnlineProvider = Provider<Future<bool> Function()>((ref) {
  return () async {
    final results = await Connectivity().checkConnectivity();
    return results.any((r) => r != ConnectivityResult.none);
  };
});

/// 서버가 없는 빌드에서도 엔진은 만든다 — `syncOnce()` 가
/// [SyncOutcome.backendUnavailable] 을 돌려줄 뿐이라 호출부가 분기하지 않아도 된다.
final syncEngineProvider = Provider<SyncEngine>((ref) {
  return SyncEngine(
    database: ref.watch(databaseProvider),
    api: ref.watch(readingApiProvider) ?? _OfflineReadingApi(),
    auth: ref.watch(authRepositoryProvider),
    cursor: ref.watch(syncCursorStoreProvider),
    outbox: ref.watch(outboxRepositoryProvider),
    isOnline: ref.watch(isOnlineProvider),
  );
});

final syncSchedulerProvider = Provider<SyncScheduler>((ref) {
  final scheduler = SyncScheduler(run: ref.watch(syncEngineProvider).syncOnce);
  ref.onDispose(scheduler.dispose);
  return scheduler;
});

/// 로그아웃 동작.
///
/// 세션만 지우면 안 된다. 델타 pull 커서를 함께 버려야 다음 사용자가 남의
/// 커서를 물려받지 않는다. [SyncCursorStore] 가 소유자를 확인하고는 있지만,
/// 안 지운 커서를 그대로 두는 것은 그 확인에만 기대는 것이다.
///
/// 로컬 Drift 기록은 지우지 않는다. 정본이 로컬이라 지우면 데이터 손실이다.
final signOutProvider = Provider<Future<void> Function()>((ref) {
  return () async {
    await ref.read(authRepositoryProvider).signOut();
    await ref.read(syncCursorStoreProvider).clear();
  };
});

/// 마지막 동기화 결과. 화면이 "대기 중 n건"을 보여줄 때 쓴다.
final syncReportProvider = StreamProvider<SyncReport>((ref) {
  return ref.watch(syncSchedulerProvider).reports;
});

/// 아직 서버로 보내지 못한 변경 수. 저장할 때마다 바뀐다.
final pendingSyncCountProvider = StreamProvider<int>((ref) {
  final db = ref.watch(databaseProvider);
  final count = db.syncOutboxRows.seq.count();
  final query = db.selectOnly(db.syncOutboxRows)..addColumns([count]);
  return query.watch().map((rows) => rows.first.read(count) ?? 0);
});

/// 서버가 없는 빌드용 자리채움. 엔진이 로그인 여부에서 먼저 걸러 내므로
/// 실제로 호출되지 않는다.
class _OfflineReadingApi implements ReadingApi {
  @override
  Future<void> upsert(List<GlucoseReading> readings, String userId) async {}

  @override
  Future<List<GlucoseReading>> fetchUpdatedSince(
    DateTime? since, {
    required int limit,
    required int offset,
  }) async =>
      const [];
}
