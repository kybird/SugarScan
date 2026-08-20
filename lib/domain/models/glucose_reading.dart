import 'glucose_unit.dart';
import 'measurement_tag.dart';
import 'reading_source.dart';

/// 혈당 기록 한 건.
///
/// 저장 규칙:
/// - [valueMgdl] 이 정본이다. 통계·동기화·헬스 연동은 모두 이 값을 쓴다.
/// - [enteredUnit] / [enteredValue] 로 사용자가 실제 입력한 원본을 함께 남긴다.
///   mmol/L 로 7.6 을 넣은 사용자에게 왕복 변환 결과인 7.5 를 되돌려주지
///   않기 위한 것으로, 표시할 때 [valueIn] 이 이 원본을 우선 사용한다.
class GlucoseReading {
  const GlucoseReading({
    required this.id,
    required this.measuredAtUtc,
    required this.tzName,
    required this.utcOffsetMinutes,
    required this.valueMgdl,
    required this.enteredUnit,
    required this.enteredValue,
    required this.tag,
    required this.source,
    required this.createdAt,
    required this.updatedAt,
    this.ocrEngineId,
    this.ocrConfidence,
    this.ocrRawText,
    this.photoPath,
    this.note,
    this.deletedAt,
    this.adjustedByUser = false,
  });

  /// 클라이언트가 생성하는 uuid v4.
  ///
  /// 서버가 아니라 앱이 id 를 만들기 때문에 오프라인에서 만든 기록도
  /// 네트워크 왕복 없이 즉시 정체성을 가진다. 동기화 설계의 전제다.
  final String id;

  final DateTime measuredAtUtc;

  /// IANA 타임존 이름(예: `Asia/Seoul`).
  final String tzName;

  /// 측정 시점의 UTC 오프셋(분). 서머타임 때문에 [tzName] 만으로는 부족하다.
  final int utcOffsetMinutes;

  final double valueMgdl;
  final GlucoseUnit enteredUnit;
  final double enteredValue;
  final MeasurementTag tag;
  final ReadingSource source;

  final String? ocrEngineId;
  final double? ocrConfidence;

  /// OCR 이 읽은 원문. 진단 목적이 아니라 오인식 분석용이며 서버로 보내지 않는다.
  final String? ocrRawText;

  /// 로컬 전용 사진 경로. 업로드하지 않는다.
  final String? photoPath;

  final String? note;

  /// 사용자가 인식값을 손으로 고쳤는지.
  ///
  /// 이 비율이 높은 기종은 엔진이 틀리고 있는 곳이다. 골든셋을 어디부터
  /// 늘려야 하는지 알려주는 가장 값싼 지표라 함께 남긴다.
  final bool adjustedByUser;

  final DateTime createdAt;
  final DateTime updatedAt;

  /// 소프트 삭제. 동기화 전달용일 뿐이며, 계정 탈퇴 시에는 완전 삭제한다.
  final DateTime? deletedAt;

  bool get isDeleted => deletedAt != null;

  /// 측정 시점의 **벽시계 시각**.
  ///
  /// 주의: 진짜 시각(instant)이 아니라 "사용자가 그때 시계에서 본 시각"이다.
  /// 태깅 규칙과 일별 집계는 반드시 이 값을 기준으로 계산해야 여행·서머타임
  /// 구간에서 그래프가 어긋나지 않는다.
  DateTime get measuredAtLocalWallClock =>
      measuredAtUtc.toUtc().add(Duration(minutes: utcOffsetMinutes));

  /// 주어진 단위로 표시할 값. 입력 단위와 같으면 원본을 그대로 돌려준다.
  double valueIn(GlucoseUnit unit) =>
      unit == enteredUnit ? enteredValue : unit.fromMgdl(valueMgdl);

  String formatted(GlucoseUnit unit) => unit.format(valueIn(unit));

  /// 사용자가 입력/스캔한 값으로부터 기록을 만든다. 정본 변환을 한곳에 모아
  /// 호출부가 mg/dL 변환을 잊는 실수를 막는다.
  factory GlucoseReading.fromEntry({
    required String id,
    required DateTime measuredAtUtc,
    required String tzName,
    required int utcOffsetMinutes,
    required double enteredValue,
    required GlucoseUnit enteredUnit,
    required MeasurementTag tag,
    required ReadingSource source,
    required DateTime now,
    String? ocrEngineId,
    double? ocrConfidence,
    String? ocrRawText,
    String? photoPath,
    String? note,
    bool adjustedByUser = false,
  }) {
    return GlucoseReading(
      id: id,
      measuredAtUtc: measuredAtUtc.toUtc(),
      tzName: tzName,
      utcOffsetMinutes: utcOffsetMinutes,
      valueMgdl: enteredUnit.toMgdl(enteredValue),
      enteredUnit: enteredUnit,
      enteredValue: enteredValue,
      tag: tag,
      source: source,
      ocrEngineId: ocrEngineId,
      ocrConfidence: ocrConfidence,
      ocrRawText: ocrRawText,
      photoPath: photoPath,
      note: note,
      adjustedByUser: adjustedByUser,
      createdAt: now.toUtc(),
      updatedAt: now.toUtc(),
    );
  }

  GlucoseReading copyWith({
    DateTime? measuredAtUtc,
    String? tzName,
    int? utcOffsetMinutes,
    double? valueMgdl,
    GlucoseUnit? enteredUnit,
    double? enteredValue,
    MeasurementTag? tag,
    ReadingSource? source,
    String? note,
    DateTime? updatedAt,
    DateTime? deletedAt,
  }) {
    return GlucoseReading(
      id: id,
      measuredAtUtc: measuredAtUtc ?? this.measuredAtUtc,
      tzName: tzName ?? this.tzName,
      utcOffsetMinutes: utcOffsetMinutes ?? this.utcOffsetMinutes,
      valueMgdl: valueMgdl ?? this.valueMgdl,
      enteredUnit: enteredUnit ?? this.enteredUnit,
      enteredValue: enteredValue ?? this.enteredValue,
      tag: tag ?? this.tag,
      source: source ?? this.source,
      ocrEngineId: ocrEngineId,
      ocrConfidence: ocrConfidence,
      ocrRawText: ocrRawText,
      photoPath: photoPath,
      note: note ?? this.note,
      adjustedByUser: adjustedByUser,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
    );
  }

  @override
  String toString() =>
      'GlucoseReading($id, ${valueMgdl.toStringAsFixed(1)} mg/dL, '
      '${tag.wireName}, ${source.wireName})';
}
