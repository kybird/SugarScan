import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/remote/remote_backend.dart';
import 'package:sugarscan/data/sync/sync_engine.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

RemoteBackend _ready() => RemoteReady(
      SupabaseClient('https://example.supabase.co', 'publishable-key'),
    );

Future<SyncStatus> _status({
  RemoteBackend? backend,
  int blocked = 0,
  int pending = 0,
  bool signedIn = true,
}) async {
  final container = ProviderContainer(
    overrides: [
      remoteBackendProvider.overrideWithValue(backend ?? _ready()),
      syncReportProvider.overrideWith(
        (ref) => Stream.value(
          SyncReport(outcome: SyncOutcome.ok, blocked: blocked),
        ),
      ),
      signedInProvider.overrideWith((ref) => Stream.value(signedIn)),
      pendingSyncCountProvider.overrideWith((ref) => Stream.value(pending)),
    ],
  );
  addTearDown(container.dispose);

  // 각 스트림에 직접 구독을 건다. syncStatusProvider 는 조기 반환하는 경로가
  // 있어서(서버 미설정, blocked > 0) 세 스트림을 늘 watch 하지는 않는다.
  // 그 경로에서는 구독이 없어 오토디스포즈되고 `.future` 가 끝나지 않는다.
  //
  // 기다리는 것 자체도 필요하다. 안 기다리면 무엇을 넣든 전부 loading 이라
  // 늘 Idle 이 나와 테스트가 통과해 버린다.
  container
    ..listen(syncReportProvider, (_, _) {})
    ..listen(signedInProvider, (_, _) {})
    ..listen(pendingSyncCountProvider, (_, _) {});

  await container.read(syncReportProvider.future);
  await container.read(signedInProvider.future);
  await container.read(pendingSyncCountProvider.future);

  return container.read(syncStatusProvider);
}

void main() {
  test('다 올라갔으면 아무것도 보여주지 않는다', () async {
    expect(await _status(), isA<SyncStatusIdle>());
  });

  // 서버가 없는 빌드에서 동기화가 고장 난 것처럼 보이면 안 된다. 있지도 않은
  // 기능이다.
  test('서버 미설정 빌드는 조용하다', () async {
    expect(
      await _status(backend: const RemoteDisabled(), blocked: 3, pending: 5),
      isA<SyncStatusIdle>(),
    );
  });

  test('대기 중인 변경은 건수로 알린다', () async {
    final status = await _status(pending: 4);

    expect(status, isA<SyncStatusPending>());
    expect((status as SyncStatusPending).count, 4);
  });

  test('막힌 것이 있으면 그것을 먼저 알린다', () async {
    final status = await _status(blocked: 2, pending: 9);

    // 조용히 안 올라가는 상태가 가장 나쁘다. 대기 건수보다 우선한다.
    expect(status, isA<SyncStatusBlocked>());
    expect((status as SyncStatusBlocked).count, 2);
  });

  test('막힌 것은 로그아웃보다도 먼저다', () async {
    expect(
      await _status(blocked: 1, signedIn: false),
      isA<SyncStatusBlocked>(),
    );
  });

  // 게이트가 첫 로그인을 강제하므로, 여기 걸리는 것은 세션이 끊겼거나 사용자가
  // 직접 로그아웃한 경우다. 둘 다 백업이 멈춘 상태다.
  test('로그아웃 상태면 백업이 멈췄다고 알린다', () async {
    expect(await _status(signedIn: false), isA<SyncStatusSignedOut>());
  });
}
