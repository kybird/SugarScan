import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/data/remote/google_auth_config.dart';

void main() {
  test('주입되지 않으면 null — 로그인 없는 로컬 전용 빌드가 가능하다', () {
    expect(
      GoogleAuthConfig.parse(serverClientId: '', iosClientId: ''),
      isNull,
    );
  });

  test('iOS 클라이언트 ID 는 없어도 된다 — Android 전용 빌드', () {
    final config = GoogleAuthConfig.parse(
      serverClientId: '123-web.apps.googleusercontent.com',
      iosClientId: '',
    );

    expect(config, isNotNull);
    expect(config!.iosClientId, isNull);
  });

  test('serverClientId 가 없으면 iOS ID 만으로는 성립하지 않는다', () {
    // Supabase 에 넘길 ID 토큰의 대상이 서버(웹) 클라이언트 ID 라서,
    // 이것이 없으면 로그인 자체가 성립하지 않는다.
    expect(
      GoogleAuthConfig.parse(
        serverClientId: '  ',
        iosClientId: '456-ios.apps.googleusercontent.com',
      ),
      isNull,
    );
  });

  test('공백을 걷어낸다', () {
    final config = GoogleAuthConfig.parse(
      serverClientId: ' 123-web.apps.googleusercontent.com \n',
      iosClientId: ' 456-ios.apps.googleusercontent.com ',
    );

    expect(config!.serverClientId, '123-web.apps.googleusercontent.com');
    expect(config.iosClientId, '456-ios.apps.googleusercontent.com');
  });
}
