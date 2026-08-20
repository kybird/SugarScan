import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'secure_session_storage.dart';
import 'supabase_config.dart';

/// 서버 연결 상태.
///
/// **연결 실패가 앱 실패는 아니다.** Drift 가 정본이라 서버가 없어도 스캔·저장·
/// 조회가 전부 동작한다. 그래서 초기화 실패를 예외로 던지지 않고 상태로 남긴다.
/// 호출부가 `RemoteReady` 를 패턴 매칭으로 꺼내야만 클라이언트를 만질 수 있으므로
/// "설정 안 됐을 수도 있다"를 잊고 지나갈 수 없다.
sealed class RemoteBackend {
  const RemoteBackend();

  /// 지금 서버로 보낼 수 있는 상태인지.
  bool get isReady => this is RemoteReady;
}

/// 빌드에 접속 정보가 주입되지 않았다. 로컬 전용으로 동작한다.
final class RemoteDisabled extends RemoteBackend {
  const RemoteDisabled();

  @override
  String toString() => 'RemoteDisabled()';
}

/// 접속 정보는 있었지만 초기화가 실패했다.
final class RemoteFailed extends RemoteBackend {
  const RemoteFailed(this.error);

  final Object error;

  @override
  String toString() => 'RemoteFailed($error)';
}

final class RemoteReady extends RemoteBackend {
  const RemoteReady(this.client);

  final SupabaseClient client;

  @override
  String toString() => 'RemoteReady()';
}

/// Supabase 를 초기화한다. `runApp` 앞에서 **한 번만** 부른다.
///
/// 예외를 밖으로 내보내지 않는다. 서버가 죽었거나 URL 을 잘못 넣었다고 해서
/// 앱이 뜨지 않으면, 오프라인 우선 설계가 있으나 마나다.
Future<RemoteBackend> initializeRemoteBackend({SupabaseConfig? config}) async {
  final SupabaseConfig? resolved;
  try {
    resolved = config ?? SupabaseConfig.fromEnvironment();
  } catch (error) {
    // service_role 키 주입 같은 설정 오류. 이건 조용히 넘기면 안 된다.
    debugPrint('Supabase 설정이 잘못되었다: $error');
    return RemoteFailed(error);
  }

  if (resolved == null) return const RemoteDisabled();

  try {
    final supabase = await Supabase.initialize(
      url: resolved.url,
      publishableKey: resolved.publishableKey,
      authOptions: FlutterAuthClientOptions(
        localStorage: SecureSessionStorage(),
      ),
    );
    return RemoteReady(supabase.client);
  } catch (error) {
    debugPrint('Supabase 초기화 실패, 로컬 전용으로 계속한다: $error');
    return RemoteFailed(error);
  }
}
