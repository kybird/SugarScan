// ignore_for_file: prefer_initializing_formals

import 'package:drift/drift.dart';

import '../local/database.dart';
import '../local/tables.dart';

/// 보낼 변경 하나. 아웃박스 행을 그 행이 가리키는 기록과 묶어 둔 것.
class PendingChange {
  const PendingChange({
    required this.seqs,
    required this.entityId,
    required this.attempts,
  });

  /// 같은 기록에 대한 아웃박스 행 번호들.
  ///
  /// 한 기록을 세 번 고치면 행이 세 개 쌓인다. 서버로는 **현재 상태 한 번**만
  /// 보내면 되므로 묶어서 처리하고, 성공하면 세 개를 함께 지운다.
  final List<int> seqs;

  final String entityId;

  /// 묶인 행들 중 최대 시도 횟수.
  final int attempts;
}

/// 아웃박스 큐.
///
/// 이 큐는 W8 부터 계정과 무관하게 쌓이고 있었다. 로그인하지 않은 채 남긴
/// 기록도 여기 들어가고, 로그인하는 순간 그대로 올라간다.
class OutboxRepository {
  OutboxRepository({required AppDatabase database}) : _db = database;

  final AppDatabase _db;

  /// 보낼 것을 오래된 순으로 가져온다.
  ///
  /// 같은 기록에 대한 여러 변경은 하나로 접는다. 서버에 보내는 것은 로컬의
  /// **현재 상태**라, 중간 단계를 순서대로 재생할 이유가 없다.
  Future<List<PendingChange>> pending({
    required int limit,
    required int maxAttempts,
  }) async {
    final query = _db.select(_db.syncOutboxRows)
      ..where((t) => t.attempts.isSmallerThanValue(maxAttempts))
      ..orderBy([(t) => OrderingTerm.asc(t.seq)]);

    final rows = await query.get();

    // 새 기록은 한도까지만 받아들이되, 이미 받아들인 기록의 나머지 행은 끝까지
    // 모은다. 한 기록의 아웃박스 행을 반만 지우면 다음 회차가 똑같은 것을 다시
    // 보낸다 — 틀리지는 않지만 매번 헛일을 한다.
    final grouped = <String, List<SyncOutboxRow>>{};
    for (final row in rows) {
      final known = grouped.containsKey(row.entityId);
      if (!known && grouped.length >= limit) continue;
      grouped.putIfAbsent(row.entityId, () => []).add(row);
    }

    return [
      for (final entry in grouped.entries)
        PendingChange(
          seqs: [for (final row in entry.value) row.seq],
          entityId: entry.key,
          attempts: entry.value
              .map((row) => row.attempts)
              .reduce((a, b) => a > b ? a : b),
        ),
    ];
  }

  /// 보내기에 성공했다. 아웃박스 행을 지우고 기록을 synced 로 표시한다.
  ///
  /// 둘을 한 트랜잭션에 묶는다. 큐만 비고 상태가 안 바뀌면 화면에는 영원히
  /// "대기 중"으로 남고, 반대면 다시 안 보내진다.
  Future<void> markSynced(Iterable<PendingChange> changes) async {
    if (changes.isEmpty) return;

    final seqs = [for (final c in changes) ...c.seqs];
    final ids = [for (final c in changes) c.entityId];

    await _db.transaction(() async {
      await (_db.delete(_db.syncOutboxRows)..where((t) => t.seq.isIn(seqs)))
          .go();
      await (_db.update(_db.glucoseReadingRows)..where((t) => t.id.isIn(ids)))
          .write(const GlucoseReadingRowsCompanion(
        syncState: Value(SyncState.synced),
      ));
    });
  }

  /// 보내기에 실패했다. **행을 지우지 않는다.**
  ///
  /// 시도 횟수만 올린다. 한도에 닿으면 [pending] 이 더 이상 집어오지 않아
  /// 조용히 멈추지만, 데이터는 남아 있어 원인을 고친 뒤 재개할 수 있다.
  /// 보낼 것을 버리는 선택지는 없다.
  Future<void> markFailed(Iterable<PendingChange> changes, String error) async {
    if (changes.isEmpty) return;

    final seqs = [for (final c in changes) ...c.seqs];
    await _db.customUpdate(
      'UPDATE sync_outbox SET attempts = attempts + 1, last_error = ? '
      'WHERE seq IN (${List.filled(seqs.length, '?').join(',')})',
      variables: [
        Variable<String>(_truncate(error)),
        for (final seq in seqs) Variable<int>(seq),
      ],
      updates: {_db.syncOutboxRows},
    );
  }

  /// 막힌 항목의 시도 횟수를 되돌린다.
  ///
  /// **사용자가 명시적으로 "다시 시도"를 누를 때만 부른다.** 자동으로 되돌리면
  /// 한도의 의미가 없어져, 고쳐지지 않는 오류를 무한히 재시도하며 배터리와
  /// 데이터를 태운다. 사람이 원인을 고쳤을 수도 있다는 신호가 있을 때만 푼다.
  Future<int> retryBlocked({required int maxAttempts}) {
    return (_db.update(_db.syncOutboxRows)
          ..where((t) => t.attempts.isBiggerOrEqualValue(maxAttempts)))
        .write(const SyncOutboxRowsCompanion(attempts: Value(0)));
  }

  /// 한도를 넘겨 더 이상 시도하지 않는 변경의 수.
  ///
  /// 0 이 아니면 사용자에게 알려야 한다. 조용히 안 올라가는 상태가 가장 나쁘다.
  Future<int> blockedCount({required int maxAttempts}) async {
    final count = _db.syncOutboxRows.seq.count();
    final query = _db.selectOnly(_db.syncOutboxRows)
      ..addColumns([count])
      ..where(_db.syncOutboxRows.attempts.isBiggerOrEqualValue(maxAttempts));
    return (await query.getSingle()).read(count) ?? 0;
  }

  /// 오류 문구가 길어질 수 있다. 진단에 필요한 앞부분만 남긴다.
  static String _truncate(String value) =>
      value.length <= 300 ? value : '${value.substring(0, 300)}…';
}
