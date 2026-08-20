import 'dart:convert';

/// Supabase 접속 정보.
///
/// **저장소에 값을 넣지 않는다.** 빌드할 때 `--dart-define` 으로 주입한다.
/// publishable(anon) 키 자체는 RLS 뒤에 있어 클라이언트에 노출되어도 되는
/// 값이지만, 커밋해 두면 프로젝트를 바꿀 때마다 코드를 고쳐야 하고 실수로
/// service_role 키를 같은 자리에 넣는 사고가 언젠가 난다. 주입 경로를
/// 하나만 열어 두는 편이 싸다.
class SupabaseConfig {
  const SupabaseConfig({required this.url, required this.publishableKey});

  final String url;

  /// 새 이름은 publishable key, 예전 이름은 anon key. 같은 자리에 들어간다.
  final String publishableKey;

  /// 빌드 시 주입된 값. 하나라도 비어 있으면 null 이다.
  ///
  /// null 이 정상 상태라는 점이 중요하다. 서버 설정 없이도 앱은 스캔하고
  /// 저장할 수 있어야 한다 — Drift 가 정본이고 서버는 복제본이다.
  static SupabaseConfig? fromEnvironment() {
    const url = String.fromEnvironment('SUPABASE_URL');
    // 두 이름을 모두 받는다. 대시보드가 어느 쪽 이름으로 보여주든 그대로
    // 복사해 붙이면 동작해야 한다.
    const publishable = String.fromEnvironment('SUPABASE_PUBLISHABLE_KEY');
    const anon = String.fromEnvironment('SUPABASE_ANON_KEY');

    return parse(url: url, publishableKey: publishable, anonKey: anon);
  }

  /// [fromEnvironment] 의 순수 함수 버전. 컴파일 타임 상수 없이 테스트한다.
  static SupabaseConfig? parse({
    required String url,
    required String publishableKey,
    required String anonKey,
  }) {
    final trimmedUrl = url.trim();
    final key = publishableKey.trim().isNotEmpty
        ? publishableKey.trim()
        : anonKey.trim();

    if (trimmedUrl.isEmpty || key.isEmpty) return null;

    // service_role 키는 RLS 를 통째로 우회한다. 클라이언트 번들에 들어가면
    // 그 프로젝트의 모든 사용자 혈당 기록이 열린다. 붙여넣기 실수를 여기서
    // 잡지 않으면 잡을 곳이 없다.
    if (_looksLikeServiceRoleKey(key)) {
      throw ArgumentError(
        'service_role 키가 주입되었다. 이 키는 RLS 를 우회하므로 클라이언트에 '
        '넣으면 안 된다. publishable(anon) 키를 쓸 것.',
      );
    }

    return SupabaseConfig(url: trimmedUrl, publishableKey: key);
  }

  /// 새 형식(`sb_secret_...`)과 예전 JWT 형식(`"role":"service_role"`)을 함께 본다.
  static bool _looksLikeServiceRoleKey(String key) {
    if (key.startsWith('sb_secret_')) return true;

    final parts = key.split('.');
    if (parts.length != 3) return false;

    try {
      final normalized = parts[1].replaceAll('-', '+').replaceAll('_', '/');
      final padded = normalized.padRight(
        normalized.length + (4 - normalized.length % 4) % 4,
        '=',
      );
      return utf8.decode(base64.decode(padded)).contains('service_role');
    } catch (_) {
      // 디코드에 실패하면 우리가 아는 형식이 아니다. 판단하지 않고 통과시킨다.
      return false;
    }
  }

  @override
  String toString() => 'SupabaseConfig($url)';
}
