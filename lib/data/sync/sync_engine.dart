// ignore_for_file: prefer_initializing_formals

import 'package:drift/drift.dart';

import '../../domain/models/glucose_reading.dart';
import '../local/database.dart';
import '../local/tables.dart';
import '../remote/auth_repository.dart';
import 'outbox_repository.dart';
import 'reading_api.dart';
import 'sync_cursor_store.dart';

/// 한 회차가 왜 그렇게 끝났는지.
enum SyncOutcome {
  /// 보내고 받았다. 실제로 옮긴 게 없어도 정상 종료면 이것이다.
  ok,

  /// 네트워크가 없다. **실패가 아니다** — 시도 횟수를 태우지 않는다.
  offline,

  /// 로그인하지 않았다. 아웃박스는 그대로 쌓인다.
  notSignedIn,

  /// 서버 접속 정보가 없는 빌드다.
  backendUnavailable,

  /// 시도했고 실패했다. 시도 횟수가 올라간다.
  failed,
}

class SyncReport {
  const SyncReport({
    required this.outcome,
    this.pushed = 0,
    this.pulled = 0,
    this.blocked = 0,
    this.error,
  });

  final SyncOutcome outcome;

  /// 서버로 올린 기록 수.
  final int pushed;

  /// 서버에서 받아 적용한 기록 수.
  final int pulled;

  /// 시도 한도를 넘겨 멈춰 선 변경 수. 0 이 아니면 사용자에게 알려야 한다.
  final int blocked;

  final String? error;

  @override
  String toString() => 'SyncReport($outcome, pushed: $pushed, '
      'pulled: $pulled, blocked: $blocked)';
}

/// 아웃박스 소비자. push → pull 순서로 한 회차를 돈다.
///
/// **순서가 설계다.** 먼저 보내고 나중에 받는다. 반대로 하면 아직 안 보낸 로컬
/// 변경 위에 서버의 옛 값이 덮이고, 그 다음 push 가 그 옛 값을 서버로 되돌려
/// 보낸다. 사용자가 방금 고친 값이 조용히 원복되는 것이라 알아채기도 어렵다.
class SyncEngine {
  SyncEngine({
    required AppDatabase database,
    required ReadingApi api,
    required AuthRepository auth,
    required SyncCursorStore cursor,
    required OutboxRepository outbox,
    Future<bool> Function()? isOnline,
    this.batchSize = 200,
    this.maxAttempts = 6,
  })  : _db = database,
        _api = api,
        _auth = auth,
        _cursor = cursor,
        _outbox = outbox,
        _isOnline = isOnline ?? _alwaysOnline;

  static Future<bool> _alwaysOnline() async => true;

  final AppDatabase _db;
  final ReadingApi _api;
  final AuthRepository _auth;
  final SyncCursorStore _cursor;
  final OutboxRepository _outbox;
  final Future<bool> Function() _isOnline;

  /// 한 번에 올리고 받을 최대 건수.
  final int batchSize;

  /// 이 횟수만큼 실패하면 그 변경은 더 시도하지 않는다.
  final int maxAttempts;

  /// 한 회차를 돈다. **예외를 밖으로 내보내지 않는다.**
  ///
  /// 백그라운드에서 주기적으로 도는 코드라, 예외가 새면 그때부터 동기화가
  /// 조용히 멈춘 채 아무도 모른다. 실패는 전부 [SyncReport] 로 돌려준다.
  Future<SyncReport> syncOnce() async {
    final userId = _auth.currentUserId;
    if (userId == null) {
      return SyncReport(
        outcome: _auth.canSignIn
            ? SyncOutcome.notSignedIn
            : SyncOutcome.backendUnavailable,
        blocked: await _blocked(),
      );
    }

    // 오프라인은 실패가 아니다. 여기서 시도 횟수를 태우면 지하철을 여섯 번
    // 타는 것만으로 아웃박스가 영구히 막힌다.
    if (!await _isOnline()) {
      return SyncReport(outcome: SyncOutcome.offline, blocked: await _blocked());
    }

    final int pushed;
    try {
      pushed = await _push(userId);
    } catch (error) {
      return SyncReport(
        outcome: SyncOutcome.failed,
        blocked: await _blocked(),
        error: error.toString(),
      );
    }

    try {
      final pulled = await _pull(userId);
      return SyncReport(
        outcome: SyncOutcome.ok,
        pushed: pushed,
        pulled: pulled,
        blocked: await _blocked(),
      );
    } catch (error) {
      // push 는 성공했다. 그 사실까지 삼키지 않는다.
      return SyncReport(
        outcome: SyncOutcome.failed,
        pushed: pushed,
        blocked: await _blocked(),
        error: error.toString(),
      );
    }
  }

  Future<int> _blocked() => _outbox.blockedCount(maxAttempts: maxAttempts);

  Future<int> _push(String userId) async {
    final changes = await _outbox.pending(
      limit: batchSize,
      maxAttempts: maxAttempts,
    );
    if (changes.isEmpty) return 0;

    final rows = await (_db.select(_db.glucoseReadingRows)
          ..where((t) => t.id.isIn([for (final c in changes) c.entityId])))
        .get();

    // 아웃박스에는 있는데 기록이 없는 경우. 보낼 것이 없으므로 큐에서 치운다.
    // 그냥 두면 매 회차 실패하며 다른 변경의 자리만 차지한다.
    final present = {for (final row in rows) row.id};
    await _outbox.markSynced(
      changes.where((c) => !present.contains(c.entityId)),
    );

    final live = changes.where((c) => present.contains(c.entityId)).toList();
    if (live.isEmpty) return 0;

    try {
      await _api.upsert([for (final row in rows) _toDomain(row)], userId);
    } catch (error) {
      await _outbox.markFailed(live, error.toString());
      rethrow;
    }

    await _outbox.markSynced(live);
    return live.length;
  }

  Future<int> _pull(String userId) async {
    final since = await _cursor.read(userId);

    var offset = 0;
    var applied = 0;
    DateTime? newest;

    while (true) {
      final batch = await _api.fetchUpdatedSince(
        since,
        limit: batchSize,
        offset: offset,
      );
      if (batch.isEmpty) break;

      applied += await _apply(batch);

      for (final reading in batch) {
        if (newest == null || reading.updatedAt.isAfter(newest)) {
          newest = reading.updatedAt;
        }
      }

      if (batch.length < batchSize) break;
      offset += batch.length;
    }

    if (newest != null) await _cursor.write(userId, newest);
    return applied;
  }

  /// 받아 온 기록을 로컬에 적용한다.
  ///
  /// 두 가지를 지킨다.
  ///
  /// **① 아직 안 보낸 로컬 변경은 덮지 않는다.** 서버의 `updated_at` 은 서버
  /// 시계가 찍고 로컬 `updatedAt` 은 단말 시계가 찍어서, 둘을 크기 비교하는
  /// LWW 는 시계가 틀어진 만큼 틀린다. 대신 "보내지 않은 변경이 있으면 그것이
  /// 최신"으로 판정한다 — 그 변경은 다음 push 에서 올라가고, 그 다음 pull 이
  /// 서버가 정한 결과를 받아 온다. 승자를 정하는 것은 결국 서버다.
  ///
  /// **② 서버가 모르는 열은 건드리지 않는다.** `ocrRawText`·`photoPath`·
  /// `adjustedByUser` 는 서버 스키마에 없다. companion 에서 통째로 빼면 Drift 가
  /// UPDATE SET 에서도 제외하므로 로컬 값이 그대로 남는다. 넣었다가는 이 기기에만
  /// 있던 OCR 원문과 사진 경로가 동기화 한 번에 사라진다.
  Future<int> _apply(List<GlucoseReading> readings) async {
    if (readings.isEmpty) return 0;

    return _db.transaction(() async {
      final ids = [for (final r in readings) r.id];
      final existing = await (_db.select(_db.glucoseReadingRows)
            ..where((t) => t.id.isIn(ids)))
          .get();
      final pendingIds = {
        for (final row in existing)
          if (row.syncState == SyncState.pending) row.id,
      };

      var applied = 0;
      for (final reading in readings) {
        if (pendingIds.contains(reading.id)) continue;

        await _db.into(_db.glucoseReadingRows).insertOnConflictUpdate(
              GlucoseReadingRowsCompanion.insert(
                id: reading.id,
                measuredAtUtc: reading.measuredAtUtc,
                tzName: reading.tzName,
                utcOffsetMinutes: reading.utcOffsetMinutes,
                valueMgdl: reading.valueMgdl,
                enteredUnit: reading.enteredUnit,
                enteredValue: reading.enteredValue,
                tag: reading.tag,
                source: reading.source,
                createdAt: reading.createdAt,
                updatedAt: reading.updatedAt,
                syncState: SyncState.synced,
                ocrEngineId: Value(reading.ocrEngineId),
                ocrConfidence: Value(reading.ocrConfidence),
                note: Value(reading.note),
                deletedAt: Value(reading.deletedAt),
              ),
            );
        applied++;
      }

      return applied;
    });
  }

  GlucoseReading _toDomain(GlucoseReadingRow row) => GlucoseReading(
        id: row.id,
        measuredAtUtc: row.measuredAtUtc,
        tzName: row.tzName,
        utcOffsetMinutes: row.utcOffsetMinutes,
        valueMgdl: row.valueMgdl,
        enteredUnit: row.enteredUnit,
        enteredValue: row.enteredValue,
        tag: row.tag,
        source: row.source,
        ocrEngineId: row.ocrEngineId,
        ocrConfidence: row.ocrConfidence,
        ocrRawText: row.ocrRawText,
        adjustedByUser: row.adjustedByUser,
        photoPath: row.photoPath,
        note: row.note,
        createdAt: row.createdAt,
        updatedAt: row.updatedAt,
        deletedAt: row.deletedAt,
      );
}
