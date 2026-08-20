import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/models/glucose_reading.dart';
import '../../l10n/generated/app_localizations.dart';
import '../shared/reading_tile.dart';
import 'edit_reading_sheet.dart';

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final readings = ref.watch(recentReadingsProvider);
    final unit = ref.watch(displayUnitProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.navHistory)),
      body: readings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text('$error', textAlign: TextAlign.center),
          ),
        ),
        data: (items) {
          if (items.isEmpty) {
            return _EmptyState(message: l10n.historyEmpty);
          }
          return ListView.separated(
            itemCount: items.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final reading = items[index];
              return Dismissible(
                key: ValueKey(reading.id),
                direction: DismissDirection.endToStart,
                background: _DeleteBackground(label: l10n.actionDelete),
                onDismissed: (_) => _delete(context, ref, reading),
                child: ReadingTile(
                  reading: reading,
                  unit: unit,
                  onTap: () => _edit(context, ref, reading),
                ),
              );
            },
          );
        },
      ),
    );
  }

  Future<void> _delete(
    BuildContext context,
    WidgetRef ref,
    GlucoseReading reading,
  ) async {
    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);

    final repository = ref.read(glucoseRepositoryProvider);
    await repository.delete(reading.id);

    messenger.showSnackBar(
      SnackBar(
        content: Text(l10n.readingDeleted),
        action: SnackBarAction(
          label: l10n.actionUndo,
          // 되살리는 것도 아웃박스를 거친다. 이미 서버로 삭제가 전파됐을 수
          // 있어서, 되살렸다는 사실도 똑같이 전파되어야 다른 기기에서 살아난다.
          onPressed: () => repository.restore(reading.id),
        ),
      ),
    );
  }

  /// 기록을 수정한다.
  ///
  /// 값·단위·태그·메모만 고칠 수 있다. 측정 시각은 건드리지 않는다 — 태깅과
  /// 일별 집계가 벽시계 시각 위에 서 있어서, 시각을 고치면 그 기록이 속한
  /// 날짜와 구간이 통째로 움직인다. 시각 수정이 필요해지면 그때 따로 다룬다.
  Future<void> _edit(
    BuildContext context,
    WidgetRef ref,
    GlucoseReading reading,
  ) async {
    final edit = await showEditReadingSheet(context, reading: reading);
    if (edit == null || !context.mounted) return;

    final l10n = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);

    await ref.read(glucoseRepositoryProvider).update(
          reading.id,
          value: edit.value,
          unit: edit.unit,
          tag: edit.tag,
          note: edit.note,
        );

    messenger.showSnackBar(SnackBar(content: Text(l10n.readingUpdated)));
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.timeline, size: 48, color: scheme.outline),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context)
                  .textTheme
                  .bodyLarge
                  ?.copyWith(color: scheme.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}

class _DeleteBackground extends StatelessWidget {
  const _DeleteBackground({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      color: scheme.errorContainer,
      alignment: Alignment.centerRight,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: TextStyle(color: scheme.onErrorContainer)),
          const SizedBox(width: 8),
          Icon(Icons.delete_outline, color: scheme.onErrorContainer),
        ],
      ),
    );
  }
}
