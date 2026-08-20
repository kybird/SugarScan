import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/auth_gate.dart';
import '../features/onboarding/unit_gate.dart';
import '../l10n/generated/app_localizations.dart';
import 'router.dart';
import 'sync_runner.dart';
import 'theme/app_theme.dart';

class SugarScanApp extends StatefulWidget {
  const SugarScanApp({super.key});

  @override
  State<SugarScanApp> createState() => _SugarScanAppState();
}

class _SugarScanAppState extends State<SugarScanApp> {
  late final GoRouter _router = createRouter();

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      onGenerateTitle: (context) => AppLocalizations.of(context).appTitle,
      routerConfig: _router,
      // 게이트를 라우터 위에 둔다. 대시보드에만 걸면 스캔 화면으로 직접
      // 들어가는 경로가 뚫린다.
      //
      // 순서가 중요하다. 로그인이 바깥이고 단위 확인이 안쪽이다 — 단위는
      // 계정에 딸린 설정이 될 값이라 누구의 설정인지부터 정해져야 한다.
      //
      // SyncRunner 는 게이트 바깥이다. 로그인 화면이나 단위 확인 화면에
      // 머무는 동안에도 이미 쌓인 것은 올라가야 한다.
      builder: (context, child) => SyncRunner(
        child: AuthGate(
          child: UnitGate(child: child ?? const SizedBox()),
        ),
      ),
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
    );
  }
}
