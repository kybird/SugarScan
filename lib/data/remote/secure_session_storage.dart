import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// 세션(리프레시 토큰 포함)을 Keystore/Keychain 에 둔다.
///
/// supabase_flutter 기본값은 SharedPreferences 다. 루팅/탈옥 단말이나 기기
/// 백업에서 평문으로 읽히는데, 이 토큰 하나면 그 사용자의 혈당 기록 전체가
/// 열린다. 저장 위치를 바꾸는 비용이 이 클래스 하나뿐이라 안 할 이유가 없다.
class SecureSessionStorage extends LocalStorage {
  SecureSessionStorage({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              // Android 기본값(AES-GCM + Keystore)이면 충분하다.
              // iOS 는 기본값이 `unlocked` 라 잠금 화면 상태에서 읽지 못한다.
              // 백그라운드 토큰 갱신이 재부팅 후 첫 잠금 해제까지 막히므로
              // `first_unlock` 으로 완화한다.
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock,
              ),
            );

  static const String _sessionKey = 'supabase.session';

  final FlutterSecureStorage _storage;

  @override
  Future<void> initialize() async {}

  @override
  Future<bool> hasAccessToken() async =>
      await _storage.read(key: _sessionKey) != null;

  @override
  Future<String?> accessToken() => _storage.read(key: _sessionKey);

  @override
  Future<void> persistSession(String persistSessionString) =>
      _storage.write(key: _sessionKey, value: persistSessionString);

  @override
  Future<void> removePersistedSession() => _storage.delete(key: _sessionKey);
}
