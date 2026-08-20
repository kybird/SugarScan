import 'package:drift/drift.dart';

import '../../domain/models/glucose_unit.dart';
import '../../domain/models/measurement_tag.dart';
import '../../domain/models/reading_source.dart';

/// enum 을 **wireName 으로** 저장한다.
///
/// Drift 의 `textEnum` 은 Dart 식별자(`preMeal`)를 그대로 쓴다. 그러면 로컬은
/// `preMeal`, 서버는 `pre_meal` 로 갈라져 동기화 계층에 매핑이 하나 더 생기고,
/// Dart 쪽 enum 이름을 바꾸는 순간 저장된 데이터가 깨진다.
/// 두 곳이 같은 문자열을 쓰게 해서 그 위험을 없앤다.
class GlucoseUnitConverter extends TypeConverter<GlucoseUnit, String> {
  const GlucoseUnitConverter();

  @override
  GlucoseUnit fromSql(String fromDb) => GlucoseUnit.fromWireName(fromDb);

  @override
  String toSql(GlucoseUnit value) => value.wireName;
}

class MeasurementTagConverter extends TypeConverter<MeasurementTag, String> {
  const MeasurementTagConverter();

  @override
  MeasurementTag fromSql(String fromDb) => MeasurementTag.fromWireName(fromDb);

  @override
  String toSql(MeasurementTag value) => value.wireName;
}

class ReadingSourceConverter extends TypeConverter<ReadingSource, String> {
  const ReadingSourceConverter();

  @override
  ReadingSource fromSql(String fromDb) => ReadingSource.fromWireName(fromDb);

  @override
  String toSql(ReadingSource value) => value.wireName;
}
