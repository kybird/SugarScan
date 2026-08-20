import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

// 생성되는 part 파일이 이 타입들을 쓴다. 여기서 import 하지 않으면
// database.g.dart 가 컴파일되지 않는다.
import '../../domain/models/glucose_unit.dart';
import '../../domain/models/measurement_tag.dart';
import '../../domain/models/reading_source.dart';
import 'converters.dart';
import 'tables.dart';

part 'database.g.dart';

@DriftDatabase(tables: [GlucoseReadingRows, SyncOutboxRows, AppSettingRows])
class AppDatabase extends _$AppDatabase {
  AppDatabase([QueryExecutor? executor])
      : super(executor ?? driftDatabase(name: 'sugarscan'));

  @override
  int get schemaVersion => 2;

  /// 날짜를 유닉스 정수가 아니라 **ISO-8601 UTC 문자열**로 저장한다.
  ///
  /// 기본값인 정수 저장은 읽을 때 로컬 시각 `DateTime` 을 돌려주므로, UTC 를
  /// 정본으로 삼는다는 규칙이 저장 계층에서 조용히 깨진다. 문자열 저장은
  /// 넣은 그대로 UTC 로 돌아오고, DB 를 직접 열어봤을 때 읽히기도 한다.
  @override
  DriftDatabaseOptions get options =>
      const DriftDatabaseOptions(storeDateTimeAsText: true);

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onUpgrade: (m, from, to) async {
          // v2: 표시 단위 등 앱 설정 저장소.
          if (from < 2) {
            await m.createTable(appSettingRows);
          }
        },
        beforeOpen: (details) async {
          // 소프트 삭제와 동기화 큐가 참조 무결성에 기대게 될 때를 대비해
          // 처음부터 켜 둔다. 나중에 켜면 기존 데이터가 걸린다.
          await customStatement('PRAGMA foreign_keys = ON');
        },
      );
}
