import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/providers.dart';
import 'package:sugarscan/features/sync/sync_status_banner.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

/// G14 — 동기화 상태 띠. **판정 로직(syncStatusProvider)은 이미
/// `test/app/sync_status_test.dart` 가 고정한다.** 여기서 보는 것은 그 판정이
/// 화면에 어떻게 나타나는가다. 화면 코드는 고치지 않는다.
void main() {
  var retried = 0;

  setUp(() => retried = 0);

  /// [status] 가 null 이면 공급자를 덮어쓰지 않는다 — 실제 사슬(기본 원격
  /// 비활성)을 그대로 돈다. [retry] 를 주면 기록용 콜백으로 바꾼다.
  Future<void> pumpBanner(
    WidgetTester tester, {
    SyncStatus? status,
    Future<void> Function()? retry,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          if (status != null) syncStatusProvider.overrideWith((ref) => status),
          if (retry != null)
            retrySyncProvider.overrideWith((ref) => () async => retry()),
        ],
        child: const MaterialApp(
          localizationsDelegates: [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(body: SyncStatusBanner()),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
  }

  Future<void> unmount(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(milliseconds: 100));
  }

  testWidgets('막힘 상태에서는 막힘 띠가 뜬다 — 대기/로그아웃 띠가 아니다',
      (tester) async {
    await pumpBanner(tester, status: const SyncStatusBlocked(3));

    // 막힘 문구와 "다시 시도" 액션이 함께 있다.
    expect(find.textContaining("Couldn't upload 3 readings"), findsOneWidget);
    expect(find.text('Try again'), findsOneWidget);
    // 로그아웃 문구로 보이면 안 된다.
    expect(find.textContaining('signed out'), findsNothing);

    await unmount(tester);
  });

  testWidgets('대기·유휴 상태에서는 아무것도 그리지 않는다', (tester) async {
    await pumpBanner(tester, status: const SyncStatusPending(5));
    expect(find.byType(Container), findsNothing);

    await pumpBanner(tester, status: const SyncStatusIdle());
    expect(find.byType(Container), findsNothing);

    await unmount(tester);
  });

  testWidgets('로그아웃 상태에서는 안내만 — "다시 시도"는 없다', (tester) async {
    await pumpBanner(tester, status: const SyncStatusSignedOut());

    expect(
      find.text('Backup is paused because you are signed out.'),
      findsOneWidget,
    );
    expect(find.text('Try again'), findsNothing);

    await unmount(tester);
  });

  testWidgets('서버 미설정 빌드에서는 띠가 숨는다 — 실제 공급자 사슬로',
      (tester) async {
    // remoteBackendProvider 기본값(RemoteDisabled)을 그대로 두고 진짜
    // syncStatusProvider 를 돌린다 — 게이트(isReady)가 화면까지 살아 있는지.
    await pumpBanner(tester);

    expect(find.byType(Container), findsNothing);
    expect(find.textContaining('upload'), findsNothing);

    await unmount(tester);
  });

  testWidgets('"다시 시도"는 retrySyncProvider 를 부른다', (tester) async {
    await pumpBanner(
      tester,
      status: const SyncStatusBlocked(3),
      retry: () async => retried++,
    );

    await tester.tap(find.text('Try again'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(retried, 1);

    await unmount(tester);
  });
}
