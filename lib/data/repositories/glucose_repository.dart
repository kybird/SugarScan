// 의존성 필드를 private 으로 유지한다. Dart 는 private 이름의 named parameter 를
// 허용하지 않아 initializing formal(`this._db`)을 쓸 수 없다.
// ignore_for_file: prefer_initializing_formals

import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

import '../../domain/models/glucose_reading.dart';
import '../../domain/models/glucose_unit.dart';
import '../../domain/models/measurement_tag.dart';
import '../../domain/models/reading_source.dart';
import '../local/database.dart';
import '../local/tables.dart';

/// 측정 시점의 IANA 타임존 이름을 알아내는 함수.
///
/// 플러그인 호출을 주입 가능하게 두어 저장소를 실기기 없이 테스트한다.
typedef TzNameResolver = Future<String> Function();

/// 혈당 기록의 로컬 저장소.
///
/// **Drift 가 정본이고 서버는 복제본이다.** 스캔은 네트워크 없이 완결되어야
/// 하므로 쓰기는 항상 로컬에서 끝나고, 서버 반영은 아웃박스가 나중에 처리한다.
class GlucoseRepository {
  GlucoseRepository({
    required AppDatabase database,
    required TzNameResolver resolveTzName,
    DateTime Function() clock = DateTime.now,
    String Function()? idGenerator,
  })  : _db = database,
        _resolveTzName = resolveTzName,
        _clock = clock,
        _newId = idGenerator ?? const Uuid().v4;

  static const String entityName = 'glucose_readings';

  final AppDatabase _db;
  final TzNameResolver _resolveTzName;
  final DateTime Function() _clock;
  final String Function() _newId;

  /// 기록 한 건을 남긴다.
  ///
  /// 기록 저장과 아웃박스 등록이 **한 트랜잭션**에서 일어난다. 둘이 갈라지면
  /// 화면에는 보이는데 서버에는 영원히 안 올라가는(또는 그 반대) 기록이 생기고,
  /// 그런 불일치는 나중에 재구성할 방법이 없다.
  Future<GlucoseReading> add({
    required double value,
    required GlucoseUnit unit,
    required MeasurementTag tag,
    required ReadingSource source,
    DateTime? measuredAt,
    String? ocrEngineId,
    double? ocrConfidence,
    String? ocrRawText,
    bool adjustedByUser = false,
    String? note,
  }) async {
    final now = _clock();
    final measured = measuredAt ?? now;

    final reading = GlucoseReading.fromEntry(
      id: _newId(),
      measuredAtUtc: measured,
      tzName: await _resolveTzName(),
      // 오프셋은 측정 시점 기준으로 잡는다. 서머타임 전환일에 오늘 아침 기록과
      // 저녁 기록의 오프셋이 다를 수 있다.
      utcOffsetMinutes: measured.timeZoneOffset.inMinutes,
      enteredValue: value,
      enteredUnit: unit,
      tag: tag,
      source: source,
      now: now,
      ocrEngineId: ocrEngineId,
      ocrConfidence: ocrConfidence,
      ocrRawText: ocrRawText,
      adjustedByUser: adjustedByUser,
      note: note,
    );

    await _db.transaction(() async {
      await _db.into(_db.glucoseReadingRows).insert(_toRow(reading));
      await _enqueue(reading.id, 'upsert', now);
    });

    return reading;
  }

  /// 소프트 삭제. 실제 행은 남긴다 — 다른 기기에도 삭제를 전달해야 한다.
  Future<void> delete(String id) async {
    final now = _clock();
    await _db.transaction(() async {
      await (_db.update(_db.glucoseReadingRows)..where((t) => t.id.equals(id)))
          .write(
        GlucoseReadingRowsCompanion(
          deletedAt: Value(now.toUtc()),
          updatedAt: Value(now.toUtc()),
          syncState: const Value(SyncState.pending),
        ),
      );
      await _enqueue(id, 'delete', now);
    });
  }

  /// 삭제를 되돌린다.
  ///
  /// 소프트 삭제라 행이 남아 있어 복구 자체는 값을 되돌리는 일이다. 다만
  /// **아웃박스에 다시 올려야 한다** — 이미 서버로 삭제가 전파됐을 수 있고,
  /// 그렇다면 되살렸다는 사실도 똑같이 전파되어야 다른 기기에서 되살아난다.
  Future<void> restore(String id) async {
    final now = _clock();
    await _db.transaction(() async {
      await (_db.update(_db.glucoseReadingRows)..where((t) => t.id.equals(id)))
          .write(
        GlucoseReadingRowsCompanion(
          deletedAt: const Value(null),
          updatedAt: Value(now.toUtc()),
          syncState: const Value(SyncState.pending),
        ),
      );
      await _enqueue(id, 'upsert', now);
    });
  }

  /// 태그나 값을 고친다.
  ///
  /// [note] 의 `null` 은 **바꾸지 않음**이고, 빈 문자열은 **지움**이다. 둘을
  /// 같게 두면 메모를 한 번 남긴 뒤로는 지울 방법이 없어진다.
  Future<void> update(
    String id, {
    double? value,
    GlucoseUnit? unit,
    MeasurementTag? tag,
    String? note,
  }) async {
    final now = _clock();
    final resolvedUnit = unit;

    await _db.transaction(() async {
      await (_db.update(_db.glucoseReadingRows)..where((t) => t.id.equals(id)))
          .write(
        GlucoseReadingRowsCompanion(
          enteredValue: value == null ? const Value.absent() : Value(value),
          enteredUnit: resolvedUnit == null
              ? const Value.absent()
              : Value(resolvedUnit),
          valueMgdl: value == null || resolvedUnit == null
              ? const Value.absent()
              : Value(resolvedUnit.toMgdl(value)),
          tag: tag == null ? const Value.absent() : Value(tag),
          note: switch (note) {
            null => const Value.absent(),
            final String text when text.trim().isEmpty => const Value(null),
            final String text => Value(text),
          },
          updatedAt: Value(now.toUtc()),
          syncState: const Value(SyncState.pending),
        ),
      );
      await _enqueue(id, 'upsert', now);
    });
  }

  Future<GlucoseReading?> byId(String id) async {
    final row = await (_db.select(_db.glucoseReadingRows)
          ..where((t) => t.id.equals(id)))
        .getSingleOrNull();
    return row == null ? null : _toDomain(row);
  }

  /// 최근 기록. 삭제된 것은 제외한다.
  Future<List<GlucoseReading>> recent({int limit = 50}) =>
      _recentQuery(limit).map(_toDomain).get();

  Stream<List<GlucoseReading>> watchRecent({int limit = 50}) =>
      _recentQuery(limit).map(_toDomain).watch();

  /// 기간으로 조회한다. 통계와 리포트가 쓴다.
  Future<List<GlucoseReading>> between(DateTime from, DateTime to) =>
      _betweenQuery(from, to).map(_toDomain).get();

  /// 기간 조회를 스트림으로. 통계 화면이 저장·수정·삭제에 스스로 반응한다.
  Stream<List<GlucoseReading>> watchBetween(DateTime from, DateTime to) =>
      _betweenQuery(from, to).map(_toDomain).watch();

  SimpleSelectStatement<$GlucoseReadingRowsTable, GlucoseReadingRow>
      _betweenQuery(DateTime from, DateTime to) {
    return _db.select(_db.glucoseReadingRows)
      ..where((t) => t.deletedAt.isNull())
      ..where((t) => t.measuredAtUtc.isBiggerOrEqualValue(from.toUtc()))
      ..where((t) => t.measuredAtUtc.isSmallerOrEqualValue(to.toUtc()))
      ..orderBy([(t) => OrderingTerm.desc(t.measuredAtUtc)]);
  }

  /// 아직 서버로 보내지 못한 변경 수.
  Future<int> pendingSyncCount() async {
    final count = _db.syncOutboxRows.seq.count();
    final query = _db.selectOnly(_db.syncOutboxRows)..addColumns([count]);
    return (await query.getSingle()).read(count) ?? 0;
  }

  SimpleSelectStatement<$GlucoseReadingRowsTable, GlucoseReadingRow>
      _recentQuery(int limit) {
    return _db.select(_db.glucoseReadingRows)
      ..where((t) => t.deletedAt.isNull())
      ..orderBy([(t) => OrderingTerm.desc(t.measuredAtUtc)])
      ..limit(limit);
  }

  Future<void> _enqueue(String entityId, String op, DateTime now) {
    return _db.into(_db.syncOutboxRows).insert(
          SyncOutboxRowsCompanion.insert(
            entity: entityName,
            entityId: entityId,
            op: op,
            createdAt: now.toUtc(),
          ),
        );
  }

  GlucoseReadingRowsCompanion _toRow(GlucoseReading r) =>
      GlucoseReadingRowsCompanion.insert(
        id: r.id,
        measuredAtUtc: r.measuredAtUtc,
        tzName: r.tzName,
        utcOffsetMinutes: r.utcOffsetMinutes,
        valueMgdl: r.valueMgdl,
        enteredUnit: r.enteredUnit,
        enteredValue: r.enteredValue,
        tag: r.tag,
        source: r.source,
        createdAt: r.createdAt,
        updatedAt: r.updatedAt,
        syncState: SyncState.pending,
        ocrEngineId: Value(r.ocrEngineId),
        ocrConfidence: Value(r.ocrConfidence),
        ocrRawText: Value(r.ocrRawText),
        adjustedByUser: Value(r.adjustedByUser),
        photoPath: Value(r.photoPath),
        note: Value(r.note),
        deletedAt: Value(r.deletedAt),
      );

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
