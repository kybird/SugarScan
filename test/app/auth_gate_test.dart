import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/data/remote/remote_backend.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

RemoteBackend _ready() => RemoteReady(
      SupabaseClient('https://example.supabase.co', 'publishable-key'),
    );

/// 게이트 판정. 스트림 프로바이더가 첫 값을 낼 때까지 기다린 뒤 읽는다.
///
/// 기다리지 않으면 무엇을 넣든 `loading` 이 나와 테스트가 통과해 버린다.
Future<AuthGateStatus> _status({
  required RemoteBackend backend,
  required bool signedIn,
  required bool signedInBefore,
}) async {
  final container = ProviderContainer(
    overrides: [
      remoteBackendProvider.overrideWithValue(backend),
      signedInProvider.overrideWith((ref) => Stream.value(signedIn)),
      signedInBeforeProvider.overrideWith((ref) => Stream.value(signedInBefore)),
    ],
  );
  addTearDown(container.dispose);

  // 구독을 붙여 두지 않으면 프로바이더가 곧바로 파기되어 `.future` 가 끝나지
  // 않는다. Riverpod 3 는 기본이 autoDispose 다.
  container.listen(authGateProvider, (_, _) {});

  if (backend.isReady) {
    await container.read(signedInProvider.future);
    await container.read(signedInBeforeProvider.future);
  }

  return container.read(authGateProvider);
}

void main() {
  // 막는 경우는 이 하나뿐이다.
  test('세션도 없고 이 기기에서 로그인한 적도 없으면 로그인 화면', () async {
    expect(
      await _status(backend: _ready(), signedIn: false, signedInBefore: false),
      AuthGateStatus.requireSignIn,
    );
  });

  test('로그인되어 있으면 통과', () async {
    expect(
      await _status(backend: _ready(), signedIn: true, signedInBefore: true),
      AuthGateStatus.allowed,
    );
  });

  // 리프레시 토큰이 끊긴 채 비행기에 탄 사람도 측정값을 남길 수 있어야 한다.
  // CLAUDE.md: "사용자가 기록을 남기지 못하는 상태를 만들지 않는다".
  test('세션이 만료돼도 로그인한 적 있는 기기는 통과한다', () async {
    expect(
      await _status(backend: _ready(), signedIn: false, signedInBefore: true),
      AuthGateStatus.allowed,
    );
  });

  // 서버 미설정 빌드에는 로그인이라는 개념 자체가 없다. 막으면 앱이 벽돌이 된다.
  test('서버 미설정 빌드는 로그인 없이 통과', () async {
    expect(
      await _status(
        backend: const RemoteDisabled(),
        signedIn: false,
        signedInBefore: false,
      ),
      AuthGateStatus.allowed,
    );
  });

  test('서버 초기화 실패도 통과', () async {
    expect(
      await _status(
        backend: const RemoteFailed('boom'),
        signedIn: false,
        signedInBefore: false,
      ),
      AuthGateStatus.allowed,
    );
  });

  test('아직 못 읽은 동안에는 loading — 로그인 화면을 깜빡이지 않는다', () {
    final container = ProviderContainer(
      overrides: [
        remoteBackendProvider.overrideWithValue(_ready()),
        signedInProvider.overrideWith((ref) => const Stream<bool>.empty()),
        signedInBeforeProvider.overrideWith((ref) => const Stream<bool>.empty()),
      ],
    );
    addTearDown(container.dispose);

    expect(container.read(authGateProvider), AuthGateStatus.loading);
  });
}
