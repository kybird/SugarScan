import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../data/remote/auth_repository.dart';
import '../../l10n/generated/app_localizations.dart';

/// 첫 실행 로그인 화면.
///
/// 이 화면이 뜨는 것은 **처음 한 번뿐**이다. 이후에는 세션이 Keychain/Keystore
/// 에 남아 자동 갱신되고, 갱신이 실패해도 게이트가 로컬 모드로 통과시킨다.
class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  bool _busy = false;
  AuthFailure? _failure;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final auth = ref.watch(authRepositoryProvider);

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              Text(
                l10n.authSignInTitle,
                style: theme.textTheme.headlineSmall
                    ?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              Text(
                l10n.authSignInBody,
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
              const Spacer(),
              if (_message(l10n) case final String message) ...[
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall
                      ?.copyWith(color: theme.colorScheme.error),
                ),
                const SizedBox(height: 12),
              ],
              FilledButton(
                onPressed: _busy || !auth.canSignIn ? null : _signIn,
                child: _busy
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(l10n.authSignInGoogle),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 취소는 실패가 아니다. 계정 선택기를 실수로 닫은 사람에게 붉은 문구를
  /// 보여줄 이유가 없다.
  String? _message(AppLocalizations l10n) => switch (_failure) {
        null || AuthFailure.cancelled => ref
                .watch(authRepositoryProvider)
                .canSignIn
            ? null
            : l10n.authSignInUnavailable,
        AuthFailure.notConfigured ||
        AuthFailure.backendUnavailable ||
        AuthFailure.configurationError =>
          l10n.authSignInUnavailable,
        AuthFailure.transient => l10n.authSignInFailed,
      };

  Future<void> _signIn() async {
    setState(() {
      _busy = true;
      _failure = null;
    });

    final result = await ref.read(authRepositoryProvider).signInWithGoogle();
    if (!mounted) return;

    await result.fold(
      (userId) async {
        // 이 기기에서 로그인한 적이 있다는 사실을 남긴다. 나중에 세션이
        // 만료되어도 게이트가 다시 막지 않게 하는 근거다.
        await ref.read(settingsRepositoryProvider).markSignedIn();
        // 게이트가 스스로 열린다. 여기서 화면을 밀어내지 않는다.
      },
      (failure) async {
        if (mounted) setState(() => _failure = failure);
      },
    );

    if (mounted) setState(() => _busy = false);
  }
}
