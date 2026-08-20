import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';

import '../features/onboarding/unit_gate.dart';
import '../l10n/generated/app_localizations.dart';
import 'router.dart';
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
      builder: (context, child) => UnitGate(child: child ?? const SizedBox()),
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
