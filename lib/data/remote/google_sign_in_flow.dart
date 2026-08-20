import 'package:google_sign_in/google_sign_in.dart';

import 'google_auth_config.dart';

/// Google 계정에서 ID 토큰을 받아 온다.
///
/// 계약:
/// - 성공하면 ID 토큰 문자열.
/// - 사용자가 취소하면 `null`. 취소는 오류가 아니다.
/// - 그 밖의 실패는 [GoogleSignInException] 을 던진다.
///
/// 함수로 뽑아 둔 이유는 `AuthRepository` 를 플러그인 없이 테스트하기 위해서다.
/// `GoogleSignIn.instance` 는 싱글턴이라 주입할 수가 없다.
typedef GoogleIdTokenProvider = Future<String?> Function();

/// 플랫폼 플러그인을 쓰는 실제 구현.
GoogleIdTokenProvider googleIdTokenProvider(GoogleAuthConfig config) {
  var initialized = false;

  return () async {
    if (!initialized) {
      await GoogleSignIn.instance.initialize(
        // iOS 는 자기 유형 ID 로 로그인하고, 서버로 넘길 토큰의 대상은
        // serverClientId 로 지정한다. Android 는 clientId 를 쓰지 않는다.
        clientId: config.iosClientId,
        serverClientId: config.serverClientId,
      );
      initialized = true;
    }

    try {
      final account = await GoogleSignIn.instance.authenticate();
      return account.authentication.idToken;
    } on GoogleSignInException catch (error) {
      if (error.code == GoogleSignInExceptionCode.canceled) return null;
      rethrow;
    }
  };
}
