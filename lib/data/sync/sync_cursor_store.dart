import '../local/database.dart';

/// 델타 pull 커서. "여기까지 받았다"를 기억한다.
///
/// **커서는 사용자에 딸린 값이다.** 계정이 바뀌었는데 이전 커서를 그대로 쓰면
/// 새 사용자의 그 시점 이전 기록을 통째로 건너뛴다. 그래서 커서와 함께 소유자를
/// 저장하고, 소유자가 다르면 커서가 없는 것으로 취급해 전체를 다시 받는다.
///
/// `app_settings`(Drift)에 둔다. 비밀이 아니라 secure storage 일 필요가 없고,
/// DB 와 같이 지워지는 편이 오히려 맞다 — 기록을 지웠는데 커서만 남으면
/// 받아야 할 것을 안 받는다.
class SyncCursorStore {
  SyncCursorStore({required AppDatabase database}) : _db = database;

  static const String _atKey = 'sync_cursor_at';
  static const String _ownerKey = 'sync_cursor_owner';

  final AppDatabase _db;

  /// [userId] 기준 커서. 없거나 소유자가 다르면 null.
  Future<DateTime?> read(String userId) async {
    final owner = await _readKey(_ownerKey);
    if (owner != userId) return null;

    final at = await _readKey(_atKey);
    if (at == null) return null;

    return DateTime.tryParse(at)?.toUtc();
  }

  Future<void> write(String userId, DateTime at) async {
    await _writeKey(_ownerKey, userId);
    await _writeKey(_atKey, at.toUtc().toIso8601String());
  }

  /// 로그아웃할 때 지운다. 다음 사용자가 남의 커서를 물려받지 않게.
  Future<void> clear() async {
    await (_db.delete(_db.appSettingRows)
          ..where((t) => t.key.isIn([_atKey, _ownerKey])))
        .go();
  }

  Future<String?> _readKey(String key) async {
    final row = await (_db.select(_db.appSettingRows)
          ..where((t) => t.key.equals(key)))
        .getSingleOrNull();
    return row?.value;
  }

  Future<void> _writeKey(String key, String value) {
    return _db.into(_db.appSettingRows).insertOnConflictUpdate(
          AppSettingRowsCompanion.insert(key: key, value: value),
        );
  }
}
