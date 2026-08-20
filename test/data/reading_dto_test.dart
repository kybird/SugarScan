import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/data/remote/reading_dto.dart';
import 'package:sugarscan/domain/models/glucose_reading.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';

GlucoseReading _reading({
  double enteredValue = 7.6,
  GlucoseUnit unit = GlucoseUnit.mmoll,
  MeasurementTag tag = MeasurementTag.preMeal,
}) {
  return GlucoseReading.fromEntry(
    id: '11111111-2222-3333-4444-555555555555',
    measuredAtUtc: DateTime.utc(2026, 3, 14, 1, 30),
    tzName: 'Asia/Seoul',
    utcOffsetMinutes: 540,
    enteredValue: enteredValue,
    enteredUnit: unit,
    tag: tag,
    source: ReadingSource.ocr,
    now: DateTime.utc(2026, 3, 14, 1, 31),
    ocrEngineId: 'segment_rule',
    ocrConfidence: 0.93,
    ocrRawText: '137 mg/dL',
  );
}

void main() {
  group('ReadingDto.toJson', () {
    test('enum 은 Dart 식별자가 아니라 wireName 으로 나간다', () {
      final json = ReadingDto.toJson(_reading(), 'user-1');

      // preMeal 이 아니라 pre_meal. 서버 enum 값과 문자 그대로 일치해야 한다.
      expect(json['tag'], 'pre_meal');
      expect(json['entered_unit'], 'mmoll');
      expect(json['source'], 'ocr');
    });

    test('OCR 원문은 서버로 보내지 않는다', () {
      final json = ReadingDto.toJson(_reading(), 'user-1');

      expect(json.containsKey('ocr_raw_text'), isFalse);
      expect(json.containsKey('photo_path'), isFalse);
      expect(json.values, isNot(contains('137 mg/dL')));
    });

    test('updated_at 은 보내지 않는다 — 서버 트리거가 정한다', () {
      // 단말 시계가 틀어져 미래 시각이 박히면, 그 뒤의 정상 변경이 델타 pull
      // 커서에 걸리지 않고 통째로 유실된다.
      final json = ReadingDto.toJson(_reading(), 'user-1');

      expect(json.containsKey('updated_at'), isFalse);
    });

    test('시각은 UTC ISO-8601 로 나간다', () {
      final json = ReadingDto.toJson(_reading(), 'user-1');

      expect(json['measured_at'], '2026-03-14T01:30:00.000Z');
      expect(json['deleted_at'], isNull);
    });

    test('정본은 mg/dL 이고 입력 원본도 함께 나간다', () {
      final json = ReadingDto.toJson(_reading(enteredValue: 7.6), 'user-1');

      expect(json['entered_value'], 7.6);
      expect(json['value_mgdl'], closeTo(136.94, 0.01));
    });
  });

  group('ReadingDto.fromJson', () {
    Map<String, dynamic> serverRow({Object? valueMgdl = 137.0}) => {
          'id': '11111111-2222-3333-4444-555555555555',
          'user_id': 'user-1',
          'measured_at': '2026-03-14T10:30:00+09:00',
          'tz_name': 'Asia/Seoul',
          'utc_offset_minutes': 540,
          'value_mgdl': valueMgdl,
          'entered_unit': 'mmoll',
          'entered_value': 7.6,
          'tag': 'pre_meal',
          'source': 'ocr',
          'ocr_engine_id': 'segment_rule',
          'ocr_confidence': 0.93,
          'note': null,
          'created_at': '2026-03-14T10:31:00+09:00',
          'updated_at': '2026-03-14T10:31:00+09:00',
          'deleted_at': null,
        };

    test('오프셋이 붙은 timestamptz 를 UTC 로 옮긴다', () {
      final reading = ReadingDto.fromJson(serverRow());

      expect(reading.measuredAtUtc.isUtc, isTrue);
      expect(reading.measuredAtUtc, DateTime.utc(2026, 3, 14, 1, 30));
      // 벽시계 시각은 오프셋을 되살려 원래 본 시각으로 돌아온다.
      expect(reading.measuredAtLocalWallClock.hour, 10);
    });

    test('numeric 이 문자열로 와도 읽는다', () {
      // PostgREST 는 설정에 따라 numeric 을 문자열로 돌려준다.
      final reading = ReadingDto.fromJson(serverRow(valueMgdl: '137.00'));

      expect(reading.valueMgdl, 137.0);
    });

    test('서버가 모르는 열은 비어 있는 채로 돌아온다', () {
      // 이 값들이 null 인 것은 "지워졌다"가 아니라 "서버가 모른다"는 뜻이다.
      // pull 이 로컬 행을 통째로 덮어쓰면 안 되는 이유가 여기 있다.
      final reading = ReadingDto.fromJson(serverRow());

      expect(reading.ocrRawText, isNull);
      expect(reading.photoPath, isNull);
      expect(reading.adjustedByUser, isFalse);
    });

    test('왕복해도 enum 과 입력 원본이 보존된다', () {
      final original = _reading();
      final json = ReadingDto.toJson(original, 'user-1');
      json['updated_at'] = original.updatedAt.toIso8601String();

      final restored = ReadingDto.fromJson(json);

      expect(restored.id, original.id);
      expect(restored.tag, original.tag);
      expect(restored.enteredUnit, original.enteredUnit);
      expect(restored.enteredValue, original.enteredValue);
      expect(restored.measuredAtUtc, original.measuredAtUtc);
    });
  });
}
