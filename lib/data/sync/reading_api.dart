// 의존성 필드를 private 으로 유지한다. Dart 는 private 이름의 named parameter 를
// 허용하지 않아 initializing formal(`this._client`)을 쓸 수 없다.
// ignore_for_file: prefer_initializing_formals

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../domain/models/glucose_reading.dart';
import '../remote/reading_dto.dart';

/// pull 한 페이지의 결과.
///
/// 해석한 기록만 돌려주면 안 되는 이유가 두 가지다.
///
/// **① 페이지 경계 판정.** 다음 페이지가 있는지는 서버가 **돌려준 행 수**로
/// 판정해야 한다. 버린 행을 뺀 수로 판정하면 마지막 페이지로 오판해 뒷 페이지를
/// 통째로 놓친다. offset 을 밀 때도 마찬가지다.
///
/// **② 커서 전진.** 해석하지 못한 행도 `updated_at` 은 읽히는 경우가 많다.
/// 그 값까지 봐야 커서가 그 행 너머로 넘어가고, pull 이 같은 행에서 제자리를
/// 돌지 않는다.
class ReadingPage {
  const ReadingPage({
    required this.readings,
    required this.fetchedRows,
    this.malformed = const [],
    this.newestSeen,
  });

  const ReadingPage.empty()
      : readings = const [],
        fetchedRows = 0,
        malformed = const [],
        newestSeen = null;

  /// 해석에 성공한 기록.
  final List<GlucoseReading> readings;

  /// 서버가 실제로 돌려준 행 수. **버린 행도 포함한다.**
  final int fetchedRows;

  /// 해석하지 못해 버린 행의 id.
  final List<String> malformed;

  /// 이 페이지에서 본 가장 큰 `updated_at`(버린 행 포함).
  final DateTime? newestSeen;
}

/// 서버의 기록 테이블에 접근하는 표면.
///
/// 인터페이스로 뽑아 둔 이유는 동기화 엔진을 네트워크 없이 테스트하기 위해서다.
/// 엔진의 어려운 부분은 HTTP 가 아니라 **순서·중복·부분 실패** 처리이고,
/// 그건 가짜 구현으로 훨씬 정확하게 검증된다.
abstract interface class ReadingApi {
  /// 기록을 올린다. 같은 id 가 있으면 덮어쓴다.
  ///
  /// 삭제도 이 경로로 간다 — 소프트 삭제라 `deleted_at` 이 채워진 행을
  /// 올리는 것일 뿐이다.
  Future<void> upsert(List<GlucoseReading> readings, String userId);

  /// `updated_at` 이 [since] **이상**인 기록을 오래된 순으로 가져온다.
  ///
  /// `초과`가 아니라 `이상`인 것이 중요하다. 서버의 `updated_at` 은 트랜잭션
  /// 시각이라 한 번에 올린 배치가 **전부 같은 값**을 갖는다. `초과`로 자르면
  /// 페이지 경계에 걸친 동일 시각 행들이 영영 안 넘어온다. 경계 행을 매번 다시
  /// 받는 비용이 훨씬 싸다 — 적용이 멱등이라 다시 받아도 결과가 같다.
  ///
  /// **해석하지 못한 행은 던지지 말고 버린다.** 행 하나가 던지면 pull 전체가
  /// 실패하고 커서가 전혀 전진하지 않아, 그 행이 고쳐질 때까지 동기화가 통째로
  /// 멈춘다. 가장 현실적인 시나리오는 버전 차이다 — 새 앱이 새로운 enum
  /// `wireName` 을 쓰면 구버전 앱은 그때부터 영원히 받지 못한다.
  Future<ReadingPage> fetchUpdatedSince(
    DateTime? since, {
    required int limit,
    required int offset,
  });
}

class SupabaseReadingApi implements ReadingApi {
  SupabaseReadingApi({required SupabaseClient client}) : _client = client;

  static const String _table = 'glucose_readings';

  final SupabaseClient _client;

  @override
  Future<void> upsert(List<GlucoseReading> readings, String userId) async {
    if (readings.isEmpty) return;

    await _client.from(_table).upsert(
          [for (final r in readings) ReadingDto.toJson(r, userId)],
        );
  }

  @override
  Future<ReadingPage> fetchUpdatedSince(
    DateTime? since, {
    required int limit,
    required int offset,
  }) async {
    // user_id 로 거르지 않는다. RLS 정책이 이미 `auth.uid() = user_id` 로
    // 자르고 있어서, 여기서 또 거는 것은 중복이고 정책과 어긋날 여지만 만든다.
    final filter = _client.from(_table).select();
    final scoped = since == null
        ? filter
        : filter.gte('updated_at', since.toUtc().toIso8601String());

    final rows = await scoped
        // 같은 updated_at 안에서 순서가 흔들리면 페이지 경계에서 행이 새거나
        // 겹친다. id 를 2차 정렬로 두어 고정한다.
        .order('updated_at', ascending: true)
        .order('id', ascending: true)
        .range(offset, offset + limit - 1);

    final readings = <GlucoseReading>[];
    final malformed = <String>[];
    DateTime? newest;

    for (final raw in rows) {
      final json = Map<String, dynamic>.from(raw);
      final seen = ReadingDto.updatedAtOf(json);
      if (seen != null && (newest == null || seen.isAfter(newest))) {
        newest = seen;
      }
      try {
        readings.add(ReadingDto.fromJson(json));
      } on Object catch (error) {
        final id = ReadingDto.idOf(json);
        malformed.add(id);
        // 사용자에게 예외 원문을 보여 주지 않는다. 진단은 로그로만 남긴다.
        debugPrint('pull: 해석 못 한 행을 건너뛴다 — $id: $error');
      }
    }

    return ReadingPage(
      readings: readings,
      fetchedRows: rows.length,
      malformed: malformed,
      newestSeen: newest,
    );
  }
}
