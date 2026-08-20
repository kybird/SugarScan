import '../../domain/models/glucose_reading.dart';
import '../../domain/models/glucose_unit.dart';
import '../../domain/models/measurement_tag.dart';
import '../../domain/models/reading_source.dart';

/// `public.glucose_readings` 행과 [GlucoseReading] 사이의 변환.
///
/// 서버 스키마는 로컬의 부분집합이다(`supabase/migrations/0001_init.sql`).
/// 올리지 않는 열: `ocrRawText`, `photoPath`, `adjustedByUser`.
///
/// **그래서 pull 은 로컬 행을 통째로 덮어쓰면 안 된다.** [fromJson] 이 돌려주는
/// 기록에서 그 세 값은 "서버가 모르는 값"이지 "비어 있는 값"이 아니다. 덮어쓰면
/// 그 기기에서만 갖고 있던 OCR 원문과 사진이 동기화 한 번에 사라진다.
class ReadingDto {
  const ReadingDto._();

  /// enum 은 Dart 식별자가 아니라 `wireName` 으로 나간다. 서버 enum 값과
  /// 문자 그대로 일치해야 하고, Dart enum 이름을 바꿔도 깨지지 않는다.
  static Map<String, dynamic> toJson(GlucoseReading r, String userId) => {
        'id': r.id,
        'user_id': userId,
        'measured_at': r.measuredAtUtc.toUtc().toIso8601String(),
        'tz_name': r.tzName,
        'utc_offset_minutes': r.utcOffsetMinutes,
        'value_mgdl': r.valueMgdl,
        'entered_unit': r.enteredUnit.wireName,
        'entered_value': r.enteredValue,
        'tag': r.tag.wireName,
        'source': r.source.wireName,
        'ocr_engine_id': r.ocrEngineId,
        'ocr_confidence': r.ocrConfidence,
        'note': r.note,
        'created_at': r.createdAt.toUtc().toIso8601String(),
        'deleted_at': r.deletedAt?.toUtc().toIso8601String(),
        // `updated_at` 은 보내지 않는다. 서버 트리거가 now() 로 덮어쓰며,
        // 델타 pull 커서가 그 값 위에 서 있다. 틀어진 단말 시계가 미래 시각을
        // 심으면 그 뒤 변경들이 커서에 걸리지 않고 통째로 유실된다.
      };

  static GlucoseReading fromJson(Map<String, dynamic> json) => GlucoseReading(
        id: json['id'] as String,
        measuredAtUtc: _dateTime(json['measured_at'])!,
        tzName: json['tz_name'] as String,
        utcOffsetMinutes: (json['utc_offset_minutes'] as num).toInt(),
        valueMgdl: _double(json['value_mgdl'])!,
        enteredUnit: GlucoseUnit.fromWireName(json['entered_unit'] as String),
        enteredValue: _double(json['entered_value'])!,
        tag: MeasurementTag.fromWireName(json['tag'] as String),
        source: ReadingSource.fromWireName(json['source'] as String),
        ocrEngineId: json['ocr_engine_id'] as String?,
        ocrConfidence: _double(json['ocr_confidence']),
        note: json['note'] as String?,
        createdAt: _dateTime(json['created_at'])!,
        updatedAt: _dateTime(json['updated_at'])!,
        deletedAt: _dateTime(json['deleted_at']),
      );

  /// PostgREST 는 `numeric` 을 설정에 따라 JSON 숫자로도, 정밀도 손실을 피하려고
  /// 문자열로도 돌려준다. 두 경우 모두 받는다.
  static double? _double(Object? value) => switch (value) {
        null => null,
        final num n => n.toDouble(),
        final String s => double.parse(s),
        _ => throw FormatException('숫자가 아니다: $value'),
      };

  /// timestamptz 는 오프셋을 달고 온다. UTC 정본 규칙에 맞춰 즉시 UTC 로 옮긴다.
  static DateTime? _dateTime(Object? value) =>
      value == null ? null : DateTime.parse(value as String).toUtc();
}
