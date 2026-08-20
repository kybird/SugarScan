import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/data/remote/supabase_config.dart';

String _jwtWithRole(String role) {
  final payload = base64Url.encode(utf8.encode('{"role":"$role"}'));
  return 'header.$payload.signature';
}

void main() {
  group('SupabaseConfig.parse', () {
    test('둘 다 비어 있으면 null — 서버 없이 도는 것이 정상 상태다', () {
      expect(
        SupabaseConfig.parse(url: '', publishableKey: '', anonKey: ''),
        isNull,
      );
    });

    test('키만 있고 URL 이 없으면 null', () {
      expect(
        SupabaseConfig.parse(
          url: '   ',
          publishableKey: 'sb_publishable_abc',
          anonKey: '',
        ),
        isNull,
      );
    });

    test('anon 이름으로 준 키도 받는다', () {
      final config = SupabaseConfig.parse(
        url: 'https://x.supabase.co',
        publishableKey: '',
        anonKey: _jwtWithRole('anon'),
      );

      expect(config, isNotNull);
      expect(config!.publishableKey, _jwtWithRole('anon'));
    });

    test('둘 다 주면 publishable 을 쓴다', () {
      final config = SupabaseConfig.parse(
        url: 'https://x.supabase.co',
        publishableKey: 'sb_publishable_new',
        anonKey: 'legacy',
      );

      expect(config!.publishableKey, 'sb_publishable_new');
    });

    test('공백을 걷어낸다 — 대시보드에서 복사하면 잘 붙어 온다', () {
      final config = SupabaseConfig.parse(
        url: '  https://x.supabase.co \n',
        publishableKey: ' sb_publishable_abc ',
        anonKey: '',
      );

      expect(config!.url, 'https://x.supabase.co');
      expect(config.publishableKey, 'sb_publishable_abc');
    });

    // service_role 키는 RLS 를 통째로 우회한다. 클라이언트 번들에 들어가면
    // 그 프로젝트의 모든 사용자 혈당 기록이 열린다.
    test('새 형식 secret 키는 거부한다', () {
      expect(
        () => SupabaseConfig.parse(
          url: 'https://x.supabase.co',
          publishableKey: 'sb_secret_abc',
          anonKey: '',
        ),
        throwsArgumentError,
      );
    });

    test('예전 JWT 형식 service_role 키도 거부한다', () {
      expect(
        () => SupabaseConfig.parse(
          url: 'https://x.supabase.co',
          publishableKey: '',
          anonKey: _jwtWithRole('service_role'),
        ),
        throwsArgumentError,
      );
    });

    test('형식을 모르는 키는 판단하지 않고 통과시킨다', () {
      expect(
        SupabaseConfig.parse(
          url: 'https://x.supabase.co',
          publishableKey: 'not.a.jwt.at.all',
          anonKey: '',
        ),
        isNotNull,
      );
    });
  });
}
