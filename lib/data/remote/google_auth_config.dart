/// Google Sign-In 클라이언트 ID.
///
/// Supabase URL/키와 같은 이유로 `--dart-define` 으로 주입한다. 클라이언트 ID
/// 자체는 비밀이 아니지만(앱 번들에서 읽힌다) 주입 경로를 하나로 좁혀 둔다.
///
/// 두 값의 역할이 다르다:
/// - [serverClientId] 는 **웹 애플리케이션** 유형 클라이언트 ID 다. Android 가
///   Supabase 로 넘길 ID 토큰의 `aud` 가 이 값이 되어야 하고, Supabase 대시보드
///   Google 프로바이더에 등록하는 값도 이것이다. Android 유형 ID 를 여기 넣으면
///   토큰이 발급은 되는데 Supabase 가 거부한다 — 원인을 찾기 어려운 실패다.
/// - [iosClientId] 는 iOS 유형 클라이언트 ID 다. iOS 에서만 쓴다.
class GoogleAuthConfig {
  const GoogleAuthConfig({required this.serverClientId, this.iosClientId});

  final String serverClientId;
  final String? iosClientId;

  static GoogleAuthConfig? fromEnvironment() {
    const server = String.fromEnvironment('GOOGLE_SERVER_CLIENT_ID');
    const ios = String.fromEnvironment('GOOGLE_IOS_CLIENT_ID');
    return parse(serverClientId: server, iosClientId: ios);
  }

  /// [fromEnvironment] 의 순수 함수 버전.
  static GoogleAuthConfig? parse({
    required String serverClientId,
    required String iosClientId,
  }) {
    final server = serverClientId.trim();
    if (server.isEmpty) return null;

    final ios = iosClientId.trim();
    return GoogleAuthConfig(
      serverClientId: server,
      iosClientId: ios.isEmpty ? null : ios,
    );
  }

  @override
  String toString() => 'GoogleAuthConfig($serverClientId)';
}
