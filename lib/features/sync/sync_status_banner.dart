import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../l10n/generated/app_localizations.dart';

/// 동기화가 막혔을 때만 나타나는 띠.
///
/// **평상시에는 아무것도 그리지 않는다.** "동기화됨" 배지를 상시 노출하면
/// 사용자가 곧 읽지 않게 되고, 정작 막혔을 때도 눈에 안 들어온다. 대기 중인
/// 변경도 곧 처리되므로 여기서 말하지 않는다 — 설정 화면이 숫자로 보여준다.
///
/// 문구는 **기록이 사라지지 않았다는 사실**부터 말한다. 사용자가 걱정할 것은
/// 데이터 유실이지 업로드 실패가 아니고, 실제로 유실은 일어나지 않는다.
class SyncStatusBanner extends ConsumerWidget {
  const SyncStatusBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(syncStatusProvider);
    final l10n = AppLocalizations.of(context);

    return switch (status) {
      SyncStatusIdle() || SyncStatusPending() => const SizedBox.shrink(),
      SyncStatusBlocked(:final count) => _Banner(
          icon: Icons.cloud_off_outlined,
          title: l10n.syncBlocked(count),
          body: l10n.syncBlockedHint,
          actionLabel: l10n.syncRetry,
          onAction: () => ref.read(retrySyncProvider)(),
        ),
      SyncStatusSignedOut() => _Banner(
          icon: Icons.cloud_off_outlined,
          title: l10n.syncSignedOut,
          body: l10n.syncBlockedHint,
        ),
    };
  }
}

class _Banner extends StatelessWidget {
  const _Banner({
    required this.icon,
    required this.title,
    required this.body,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String title;
  final String body;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: scheme.surfaceContainerHighest,
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: scheme.onSurfaceVariant),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                Text(
                  body,
                  style: theme.textTheme.bodySmall
                      ?.copyWith(color: scheme.onSurfaceVariant),
                ),
                if (actionLabel case final String label) ...[
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: onAction,
                    style: TextButton.styleFrom(
                      padding: EdgeInsets.zero,
                      minimumSize: const Size(0, 32),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    child: Text(label),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
