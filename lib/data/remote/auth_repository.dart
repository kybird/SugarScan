// 의존성 필드를 private 으로 유지한다. Dart 는 private 이름의 named parameter 를
// 허용하지 않아 initializing formal(`this._client`)을 쓸 수 없다.
// ignore_for_file: prefer_initializing_formals

import 'package:google_sign_in/google_sign_in.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/result.dart';
import 'google_sign_in_flow.dart';

/// 로그인에 실패한 이유.
enum AuthFailure {
  /// 서버 접속 정보가 없거나 초기화가 실패했다. 재시도해도 소용없다.
  backendUnavailable,

  /// Google 클라이언트 ID 가 주입되지 않았다. 빌드 설정 문제다.
  notConfigured,

  /// 사용자가 계정 선택을 취소했다. **오류가 아니다** — 화면에 실패를 띄우지
  /// 않는다. 실수로 닫은 사람에게 붉은 배너를 보여줄 이유가 없다.
  cancelled,

  /// 클라이언트 ID·SHA-1·프로바이더 설정이 어긋났다. 사용자가 재시도해도
  /// 똑같이 실패하므로 일시적 오류와 섞으면 안 된다.
  configurationError,

  /// 네트워크·서버 문제. 나중에 다시 시도할 만하다.
  transient,
}

/// 인증. **Google 로그인만** 다룬다.
///
/// 익명 로그인은 쓰지 않는다. 설치할 때마다 `auth.users` 행이 쌓이고, 익명 →
/// Google 연결(link)에서 identity 충돌 처리가 따로 필요해지는데, 그 대가로 얻는
/// 것이 "로그인하지 않은 사용자의 서버 백업" 하나뿐이라 남는 장사가 아니다.
/// 로그인하지 않은 상태는 그냥 **완전 로컬**이다 — 기록 id 를 클라이언트가
/// 만들고 `user_id` 는 push 하는 순간에 찍기 때문에, 로그인 전에 쌓인 아웃박스가
/// 로그인 직후 그대로 올라간다.
class AuthRepository {
  AuthRepository({
    required SupabaseClient? client,
    required GoogleIdTokenProvider? idTokenProvider,
  })  : _client = client,
        _idTokenProvider = idTokenProvider;

  final SupabaseClient? _client;
  final GoogleIdTokenProvider? _idTokenProvider;

  /// 로그인된 사용자 id. 없으면 null.
  String? get currentUserId => _client?.auth.currentUser?.id;

  bool get isSignedIn => currentUserId != null;

  /// 로그인한 계정의 이메일. 설정 화면이 "누구로 로그인했는지" 보여줄 때 쓴다.
  String? get currentEmail => _client?.auth.currentUser?.email;

  /// 지금 로그인 시도가 가능한 상태인지. 둘 중 하나라도 없으면 버튼을 눌러도
  /// 실패할 뿐이라 화면이 미리 알아야 한다.
  bool get canSignIn => _client != null && _idTokenProvider != null;

  /// 세션 변화. 게이트가 이걸 보고 열리고 닫힌다.
  Stream<AuthState> get authStateChanges =>
      _client?.auth.onAuthStateChange ?? const Stream<AuthState>.empty();

  /// Google 계정으로 로그인한다.
  ///
  /// ID 토큰을 그대로 Supabase 에 넘긴다(`signInWithIdToken`). 브라우저를 띄우는
  /// OAuth 리디렉트 방식이 아니라 네이티브 계정 선택기를 쓰므로 딥링크 왕복이
  /// 없고, 앱을 벗어나지 않는다.
  Future<Result<String, AuthFailure>> signInWithGoogle() async {
    final client = _client;
    if (client == null) return const Err(AuthFailure.backendUnavailable);

    final provider = _idTokenProvider;
    if (provider == null) return const Err(AuthFailure.notConfigured);

    final String? idToken;
    try {
      idToken = await provider();
    } on GoogleSignInException catch (error) {
      return Err(_mapGoogleFailure(error.code));
    } catch (_) {
      return const Err(AuthFailure.transient);
    }

    // 취소. 사용자가 계정 선택기를 닫았을 뿐이다.
    if (idToken == null) return const Err(AuthFailure.cancelled);

    try {
      final response = await client.auth.signInWithIdToken(
        provider: OAuthProvider.google,
        idToken: idToken,
      );
      final user = response.user;
      if (user == null) return const Err(AuthFailure.transient);
      return Ok(user.id);
    } on AuthException catch (error) {
      // Supabase 쪽 Google 프로바이더가 꺼져 있거나 클라이언트 ID 가 등록되지
      // 않은 경우. 토큰은 정상인데 서버가 거부하는 것이라 재시도는 의미 없다.
      final misconfigured = error.statusCode == '400' ||
          error.message.toLowerCase().contains('provider');
      return Err(
        misconfigured ? AuthFailure.configurationError : AuthFailure.transient,
      );
    } catch (_) {
      return const Err(AuthFailure.transient);
    }
  }

  /// 로그아웃.
  ///
  /// 로컬 Drift 기록은 **지우지 않는다.** 정본은 로컬이고 서버는 복제본이라,
  /// 로그아웃했다고 사용자의 혈당 기록을 없애는 것은 데이터 손실이다.
  Future<void> signOut() async {
    try {
      await _client?.auth.signOut();
    } catch (_) {
      // 서버에 닿지 못해도 로컬 세션은 지워진다. 실패를 올릴 이유가 없다.
    }
  }

  static AuthFailure _mapGoogleFailure(GoogleSignInExceptionCode code) =>
      switch (code) {
        GoogleSignInExceptionCode.canceled => AuthFailure.cancelled,
        GoogleSignInExceptionCode.clientConfigurationError ||
        GoogleSignInExceptionCode.providerConfigurationError =>
          AuthFailure.configurationError,
        // uiUnavailable·userMismatch·interrupted 는 다시 시도하면 풀릴 수 있다.
        _ => AuthFailure.transient,
      };
}
