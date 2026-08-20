import '../../domain/models/glucose_unit.dart';
import '../../domain/models/measurement_tag.dart';
import '../../domain/models/reading_source.dart';

/// 사용자가 확인 시트에서 승인한 기록.
///
/// 아직 저장 계층이 없어(W8) 스캔 화면이 이 값을 호출부로 돌려준다. Drift 와
/// 동기화가 붙으면 이 타입이 그대로 `GlucoseReading.fromEntry` 의 입력이 된다.
class ScanEntry {
  const ScanEntry({
    required this.value,
    required this.unit,
    required this.tag,
    required this.source,
    this.engineId,
    this.confidence,
    this.rawText,
    this.adjustedByUser = false,
  });

  final double value;
  final GlucoseUnit unit;
  final MeasurementTag tag;
  final ReadingSource source;

  final String? engineId;
  final double? confidence;
  final String? rawText;

  /// 사용자가 인식값을 손으로 고쳤는지.
  ///
  /// 이 비율이 높으면 엔진이 특정 기종에서 틀리고 있다는 신호다. 골든셋을
  /// 늘려야 할 곳을 알려주는 가장 값싼 지표이므로 기록해 둔다.
  final bool adjustedByUser;

  double get valueMgdl => unit.toMgdl(value);

  ScanEntry copyWith({
    double? value,
    MeasurementTag? tag,
    bool? adjustedByUser,
  }) =>
      ScanEntry(
        value: value ?? this.value,
        unit: unit,
        tag: tag ?? this.tag,
        source: source,
        engineId: engineId,
        confidence: confidence,
        rawText: rawText,
        adjustedByUser: adjustedByUser ?? this.adjustedByUser,
      );
}
