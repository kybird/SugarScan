import 'package:drift/drift.dart';

import 'converters.dart';

/// 서버와의 동기화 상태.
enum SyncState { pending, synced, conflict }

@DataClassName('GlucoseReadingRow')
class GlucoseReadingRows extends Table {
  @override
  String get tableName => 'glucose_readings';

  /// 클라이언트가 만드는 uuid v4.
  ///
  /// 서버가 아니라 앱이 id 를 만들기 때문에 오프라인에서 남긴 기록도 네트워크
  /// 왕복 없이 즉시 정체성을 가진다. 동기화 설계 전체가 이 전제 위에 있다.
  TextColumn get id => text()();

  DateTimeColumn get measuredAtUtc => dateTime()();

  /// IANA 타임존 이름(예: `Asia/Seoul`).
  TextColumn get tzName => text()();

  /// 측정 시점의 UTC 오프셋(분). 서머타임 때문에 [tzName] 만으로는 부족하다.
  IntColumn get utcOffsetMinutes => integer()();

  /// 저장 정본. 통계·동기화·헬스 연동이 전부 이 값을 쓴다.
  RealColumn get valueMgdl => real()();

  /// 사용자가 실제로 입력한 원본. mmol/L 로 7.6 을 넣은 사람에게 왕복 변환
  /// 결과인 7.5 를 되돌려주지 않기 위해 함께 남긴다.
  TextColumn get enteredUnit => text().map(const GlucoseUnitConverter())();
  RealColumn get enteredValue => real()();

  TextColumn get tag => text().map(const MeasurementTagConverter())();
  TextColumn get source => text().map(const ReadingSourceConverter())();

  TextColumn get ocrEngineId => text().nullable()();
  RealColumn get ocrConfidence => real().nullable()();

  /// OCR 원문. 오인식 분석용이며 서버로 보내지 않는다.
  TextColumn get ocrRawText => text().nullable()();

  /// 사용자가 인식값을 손으로 고쳤는지.
  ///
  /// 이 비율이 높은 기종은 엔진이 틀리고 있는 곳이다. 골든셋을 어디부터
  /// 늘려야 하는지 알려주는 가장 값싼 지표라 기록해 둔다.
  BoolColumn get adjustedByUser =>
      boolean().withDefault(const Constant(false))();

  /// 로컬 전용 사진 경로. 업로드하지 않는다.
  TextColumn get photoPath => text().nullable()();

  TextColumn get note => text().nullable()();

  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();

  /// 소프트 삭제. 동기화 전달용일 뿐이며, 계정 탈퇴 시에는 완전 삭제한다.
  DateTimeColumn get deletedAt => dateTime().nullable()();

  IntColumn get syncState => intEnum<SyncState>()();

  @override
  Set<Column> get primaryKey => {id};
}

/// 서버로 보내야 할 변경 목록.
///
/// 로컬 쓰기와 **같은 트랜잭션**에서 기록된다. 기록은 남았는데 보낼 목록에
/// 빠지거나 그 반대가 되는 상태를 애초에 만들지 않기 위해서다.
@DataClassName('SyncOutboxRow')
class SyncOutboxRows extends Table {
  @override
  String get tableName => 'sync_outbox';

  IntColumn get seq => integer().autoIncrement()();
  TextColumn get entity => text()();
  TextColumn get entityId => text()();

  /// `upsert` / `delete`.
  TextColumn get op => text()();

  DateTimeColumn get createdAt => dateTime()();
  IntColumn get attempts => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();
}
