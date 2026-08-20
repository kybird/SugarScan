import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'app/providers.dart';
import 'data/remote/remote_backend.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 서버 초기화는 앱을 막지 않는다. 접속 정보가 없거나(로컬 전용 빌드) 초기화가
  // 실패해도 [initializeRemoteBackend] 는 상태를 돌려줄 뿐 던지지 않는다.
  // Drift 가 정본이므로 이 상태에서도 스캔·저장·조회가 전부 동작한다.
  final backend = await initializeRemoteBackend();

  runApp(
    ProviderScope(
      overrides: [remoteBackendProvider.overrideWithValue(backend)],
      child: const SugarScanApp(),
    ),
  );
}
