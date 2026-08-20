import 'package:flutter_test/flutter_test.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sugarscan/core/result.dart';
import 'package:sugarscan/data/remote/auth_repository.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// 네트워크를 타지 않는 클라이언트. 생성자만으로는 아무 요청도 하지 않는다.
SupabaseClient _client() =>
    SupabaseClient('https://example.supabase.co', 'publishable-key');

AuthRepository _repo({
  SupabaseClient? client,
  Future<String?> Function()? provider,
}) {
  return AuthRepository(client: client, idTokenProvider: provider);
}

void main() {
  group('로그인 불가 상태', () {
    test('서버 미설정 빌드는 backendUnavailable', () async {
      final repo = _repo(provider: () async => 'token');

      expect(repo.canSignIn, isFalse);
      expect(
        (await repo.signInWithGoogle()).errorOrNull,
        AuthFailure.backendUnavailable,
      );
    });

    test('Google 클라이언트 ID 가 없으면 notConfigured', () async {
      final repo = _repo(client: _client());

      expect(repo.canSignIn, isFalse);
      expect(
        (await repo.signInWithGoogle()).errorOrNull,
        AuthFailure.notConfigured,
      );
    });

    test('둘 다 있으면 로그인을 시도할 수 있다', () {
      expect(
        _repo(client: _client(), provider: () async => 'token').canSignIn,
        isTrue,
      );
    });
  });

  group('실패 분류', () {
    // 취소는 오류가 아니다. 화면이 붉은 배너를 띄우지 않도록 따로 둔다.
    test('계정 선택기를 닫으면 cancelled', () async {
      final repo = _repo(client: _client(), provider: () async => null);

      expect(
        (await repo.signInWithGoogle()).errorOrNull,
        AuthFailure.cancelled,
      );
    });

    test('canceled 예외도 cancelled 로 접힌다', () async {
      final repo = _repo(
        client: _client(),
        provider: () async => throw const GoogleSignInException(
          code: GoogleSignInExceptionCode.canceled,
        ),
      );

      expect(
        (await repo.signInWithGoogle()).errorOrNull,
        AuthFailure.cancelled,
      );
    });

    // 설정 오류는 재시도해도 똑같이 실패한다. 일시적 오류와 섞으면 백오프만 돈다.
    test('클라이언트 설정 오류는 configurationError', () async {
      final repo = _repo(
        client: _client(),
        provider: () async => throw const GoogleSignInException(
          code: GoogleSignInExceptionCode.clientConfigurationError,
        ),
      );

      expect(
        (await repo.signInWithGoogle()).errorOrNull,
        AuthFailure.configurationError,
      );
    });

    test('프로바이더 설정 오류는 configurationError', () async {
      final repo = _repo(
        client: _client(),
        provider: () async => throw const GoogleSignInException(
          code: GoogleSignInExceptionCode.providerConfigurationError,
        ),
      );

      expect(
        (await repo.signInWithGoogle()).errorOrNull,
        AuthFailure.configurationError,
      );
    });

    test('UI 를 띄우지 못한 것은 다시 시도할 만하다', () async {
      final repo = _repo(
        client: _client(),
        provider: () async => throw const GoogleSignInException(
          code: GoogleSignInExceptionCode.uiUnavailable,
        ),
      );

      expect(
        (await repo.signInWithGoogle()).errorOrNull,
        AuthFailure.transient,
      );
    });

    test('알 수 없는 예외는 transient', () async {
      final repo = _repo(
        client: _client(),
        provider: () async => throw StateError('boom'),
      );

      expect(
        (await repo.signInWithGoogle()).errorOrNull,
        AuthFailure.transient,
      );
    });
  });

  test('로그인 전에는 사용자 id 가 없다', () {
    expect(_repo(client: _client()).currentUserId, isNull);
    expect(_repo(client: _client()).isSignedIn, isFalse);
  });

  test('서버가 없어도 signOut 은 던지지 않는다', () async {
    await expectLater(_repo().signOut(), completes);
  });

  test('Ok/Err 로 분기가 드러난다', () async {
    final result = await _repo().signInWithGoogle();
    expect(result, isA<Err<String, AuthFailure>>());
  });
}
