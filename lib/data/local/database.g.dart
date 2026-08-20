// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database.dart';

// ignore_for_file: type=lint
class $GlucoseReadingRowsTable extends GlucoseReadingRows
    with TableInfo<$GlucoseReadingRowsTable, GlucoseReadingRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $GlucoseReadingRowsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _measuredAtUtcMeta = const VerificationMeta(
    'measuredAtUtc',
  );
  @override
  late final GeneratedColumn<DateTime> measuredAtUtc =
      GeneratedColumn<DateTime>(
        'measured_at_utc',
        aliasedName,
        false,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _tzNameMeta = const VerificationMeta('tzName');
  @override
  late final GeneratedColumn<String> tzName = GeneratedColumn<String>(
    'tz_name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _utcOffsetMinutesMeta = const VerificationMeta(
    'utcOffsetMinutes',
  );
  @override
  late final GeneratedColumn<int> utcOffsetMinutes = GeneratedColumn<int>(
    'utc_offset_minutes',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _valueMgdlMeta = const VerificationMeta(
    'valueMgdl',
  );
  @override
  late final GeneratedColumn<double> valueMgdl = GeneratedColumn<double>(
    'value_mgdl',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  @override
  late final GeneratedColumnWithTypeConverter<GlucoseUnit, String> enteredUnit =
      GeneratedColumn<String>(
        'entered_unit',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: true,
      ).withConverter<GlucoseUnit>(
        $GlucoseReadingRowsTable.$converterenteredUnit,
      );
  static const VerificationMeta _enteredValueMeta = const VerificationMeta(
    'enteredValue',
  );
  @override
  late final GeneratedColumn<double> enteredValue = GeneratedColumn<double>(
    'entered_value',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  @override
  late final GeneratedColumnWithTypeConverter<MeasurementTag, String> tag =
      GeneratedColumn<String>(
        'tag',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: true,
      ).withConverter<MeasurementTag>($GlucoseReadingRowsTable.$convertertag);
  @override
  late final GeneratedColumnWithTypeConverter<ReadingSource, String> source =
      GeneratedColumn<String>(
        'source',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: true,
      ).withConverter<ReadingSource>($GlucoseReadingRowsTable.$convertersource);
  static const VerificationMeta _ocrEngineIdMeta = const VerificationMeta(
    'ocrEngineId',
  );
  @override
  late final GeneratedColumn<String> ocrEngineId = GeneratedColumn<String>(
    'ocr_engine_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _ocrConfidenceMeta = const VerificationMeta(
    'ocrConfidence',
  );
  @override
  late final GeneratedColumn<double> ocrConfidence = GeneratedColumn<double>(
    'ocr_confidence',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _ocrRawTextMeta = const VerificationMeta(
    'ocrRawText',
  );
  @override
  late final GeneratedColumn<String> ocrRawText = GeneratedColumn<String>(
    'ocr_raw_text',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _adjustedByUserMeta = const VerificationMeta(
    'adjustedByUser',
  );
  @override
  late final GeneratedColumn<bool> adjustedByUser = GeneratedColumn<bool>(
    'adjusted_by_user',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("adjusted_by_user" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _photoPathMeta = const VerificationMeta(
    'photoPath',
  );
  @override
  late final GeneratedColumn<String> photoPath = GeneratedColumn<String>(
    'photo_path',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _noteMeta = const VerificationMeta('note');
  @override
  late final GeneratedColumn<String> note = GeneratedColumn<String>(
    'note',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta(
    'updatedAt',
  );
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _deletedAtMeta = const VerificationMeta(
    'deletedAt',
  );
  @override
  late final GeneratedColumn<DateTime> deletedAt = GeneratedColumn<DateTime>(
    'deleted_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  @override
  late final GeneratedColumnWithTypeConverter<SyncState, int> syncState =
      GeneratedColumn<int>(
        'sync_state',
        aliasedName,
        false,
        type: DriftSqlType.int,
        requiredDuringInsert: true,
      ).withConverter<SyncState>($GlucoseReadingRowsTable.$convertersyncState);
  @override
  List<GeneratedColumn> get $columns => [
    id,
    measuredAtUtc,
    tzName,
    utcOffsetMinutes,
    valueMgdl,
    enteredUnit,
    enteredValue,
    tag,
    source,
    ocrEngineId,
    ocrConfidence,
    ocrRawText,
    adjustedByUser,
    photoPath,
    note,
    createdAt,
    updatedAt,
    deletedAt,
    syncState,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'glucose_readings';
  @override
  VerificationContext validateIntegrity(
    Insertable<GlucoseReadingRow> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('measured_at_utc')) {
      context.handle(
        _measuredAtUtcMeta,
        measuredAtUtc.isAcceptableOrUnknown(
          data['measured_at_utc']!,
          _measuredAtUtcMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_measuredAtUtcMeta);
    }
    if (data.containsKey('tz_name')) {
      context.handle(
        _tzNameMeta,
        tzName.isAcceptableOrUnknown(data['tz_name']!, _tzNameMeta),
      );
    } else if (isInserting) {
      context.missing(_tzNameMeta);
    }
    if (data.containsKey('utc_offset_minutes')) {
      context.handle(
        _utcOffsetMinutesMeta,
        utcOffsetMinutes.isAcceptableOrUnknown(
          data['utc_offset_minutes']!,
          _utcOffsetMinutesMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_utcOffsetMinutesMeta);
    }
    if (data.containsKey('value_mgdl')) {
      context.handle(
        _valueMgdlMeta,
        valueMgdl.isAcceptableOrUnknown(data['value_mgdl']!, _valueMgdlMeta),
      );
    } else if (isInserting) {
      context.missing(_valueMgdlMeta);
    }
    if (data.containsKey('entered_value')) {
      context.handle(
        _enteredValueMeta,
        enteredValue.isAcceptableOrUnknown(
          data['entered_value']!,
          _enteredValueMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_enteredValueMeta);
    }
    if (data.containsKey('ocr_engine_id')) {
      context.handle(
        _ocrEngineIdMeta,
        ocrEngineId.isAcceptableOrUnknown(
          data['ocr_engine_id']!,
          _ocrEngineIdMeta,
        ),
      );
    }
    if (data.containsKey('ocr_confidence')) {
      context.handle(
        _ocrConfidenceMeta,
        ocrConfidence.isAcceptableOrUnknown(
          data['ocr_confidence']!,
          _ocrConfidenceMeta,
        ),
      );
    }
    if (data.containsKey('ocr_raw_text')) {
      context.handle(
        _ocrRawTextMeta,
        ocrRawText.isAcceptableOrUnknown(
          data['ocr_raw_text']!,
          _ocrRawTextMeta,
        ),
      );
    }
    if (data.containsKey('adjusted_by_user')) {
      context.handle(
        _adjustedByUserMeta,
        adjustedByUser.isAcceptableOrUnknown(
          data['adjusted_by_user']!,
          _adjustedByUserMeta,
        ),
      );
    }
    if (data.containsKey('photo_path')) {
      context.handle(
        _photoPathMeta,
        photoPath.isAcceptableOrUnknown(data['photo_path']!, _photoPathMeta),
      );
    }
    if (data.containsKey('note')) {
      context.handle(
        _noteMeta,
        note.isAcceptableOrUnknown(data['note']!, _noteMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(
        _updatedAtMeta,
        updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('deleted_at')) {
      context.handle(
        _deletedAtMeta,
        deletedAt.isAcceptableOrUnknown(data['deleted_at']!, _deletedAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  GlucoseReadingRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return GlucoseReadingRow(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      measuredAtUtc: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}measured_at_utc'],
      )!,
      tzName: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}tz_name'],
      )!,
      utcOffsetMinutes: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}utc_offset_minutes'],
      )!,
      valueMgdl: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}value_mgdl'],
      )!,
      enteredUnit: $GlucoseReadingRowsTable.$converterenteredUnit.fromSql(
        attachedDatabase.typeMapping.read(
          DriftSqlType.string,
          data['${effectivePrefix}entered_unit'],
        )!,
      ),
      enteredValue: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}entered_value'],
      )!,
      tag: $GlucoseReadingRowsTable.$convertertag.fromSql(
        attachedDatabase.typeMapping.read(
          DriftSqlType.string,
          data['${effectivePrefix}tag'],
        )!,
      ),
      source: $GlucoseReadingRowsTable.$convertersource.fromSql(
        attachedDatabase.typeMapping.read(
          DriftSqlType.string,
          data['${effectivePrefix}source'],
        )!,
      ),
      ocrEngineId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}ocr_engine_id'],
      ),
      ocrConfidence: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}ocr_confidence'],
      ),
      ocrRawText: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}ocr_raw_text'],
      ),
      adjustedByUser: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}adjusted_by_user'],
      )!,
      photoPath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}photo_path'],
      ),
      note: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}note'],
      ),
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      deletedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}deleted_at'],
      ),
      syncState: $GlucoseReadingRowsTable.$convertersyncState.fromSql(
        attachedDatabase.typeMapping.read(
          DriftSqlType.int,
          data['${effectivePrefix}sync_state'],
        )!,
      ),
    );
  }

  @override
  $GlucoseReadingRowsTable createAlias(String alias) {
    return $GlucoseReadingRowsTable(attachedDatabase, alias);
  }

  static TypeConverter<GlucoseUnit, String> $converterenteredUnit =
      const GlucoseUnitConverter();
  static TypeConverter<MeasurementTag, String> $convertertag =
      const MeasurementTagConverter();
  static TypeConverter<ReadingSource, String> $convertersource =
      const ReadingSourceConverter();
  static JsonTypeConverter2<SyncState, int, int> $convertersyncState =
      const EnumIndexConverter<SyncState>(SyncState.values);
}

class GlucoseReadingRow extends DataClass
    implements Insertable<GlucoseReadingRow> {
  /// 클라이언트가 만드는 uuid v4.
  ///
  /// 서버가 아니라 앱이 id 를 만들기 때문에 오프라인에서 남긴 기록도 네트워크
  /// 왕복 없이 즉시 정체성을 가진다. 동기화 설계 전체가 이 전제 위에 있다.
  final String id;
  final DateTime measuredAtUtc;

  /// IANA 타임존 이름(예: `Asia/Seoul`).
  final String tzName;

  /// 측정 시점의 UTC 오프셋(분). 서머타임 때문에 [tzName] 만으로는 부족하다.
  final int utcOffsetMinutes;

  /// 저장 정본. 통계·동기화·헬스 연동이 전부 이 값을 쓴다.
  final double valueMgdl;

  /// 사용자가 실제로 입력한 원본. mmol/L 로 7.6 을 넣은 사람에게 왕복 변환
  /// 결과인 7.5 를 되돌려주지 않기 위해 함께 남긴다.
  final GlucoseUnit enteredUnit;
  final double enteredValue;
  final MeasurementTag tag;
  final ReadingSource source;
  final String? ocrEngineId;
  final double? ocrConfidence;

  /// OCR 원문. 오인식 분석용이며 서버로 보내지 않는다.
  final String? ocrRawText;

  /// 사용자가 인식값을 손으로 고쳤는지.
  ///
  /// 이 비율이 높은 기종은 엔진이 틀리고 있는 곳이다. 골든셋을 어디부터
  /// 늘려야 하는지 알려주는 가장 값싼 지표라 기록해 둔다.
  final bool adjustedByUser;

  /// 로컬 전용 사진 경로. 업로드하지 않는다.
  final String? photoPath;
  final String? note;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// 소프트 삭제. 동기화 전달용일 뿐이며, 계정 탈퇴 시에는 완전 삭제한다.
  final DateTime? deletedAt;
  final SyncState syncState;
  const GlucoseReadingRow({
    required this.id,
    required this.measuredAtUtc,
    required this.tzName,
    required this.utcOffsetMinutes,
    required this.valueMgdl,
    required this.enteredUnit,
    required this.enteredValue,
    required this.tag,
    required this.source,
    this.ocrEngineId,
    this.ocrConfidence,
    this.ocrRawText,
    required this.adjustedByUser,
    this.photoPath,
    this.note,
    required this.createdAt,
    required this.updatedAt,
    this.deletedAt,
    required this.syncState,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['measured_at_utc'] = Variable<DateTime>(measuredAtUtc);
    map['tz_name'] = Variable<String>(tzName);
    map['utc_offset_minutes'] = Variable<int>(utcOffsetMinutes);
    map['value_mgdl'] = Variable<double>(valueMgdl);
    {
      map['entered_unit'] = Variable<String>(
        $GlucoseReadingRowsTable.$converterenteredUnit.toSql(enteredUnit),
      );
    }
    map['entered_value'] = Variable<double>(enteredValue);
    {
      map['tag'] = Variable<String>(
        $GlucoseReadingRowsTable.$convertertag.toSql(tag),
      );
    }
    {
      map['source'] = Variable<String>(
        $GlucoseReadingRowsTable.$convertersource.toSql(source),
      );
    }
    if (!nullToAbsent || ocrEngineId != null) {
      map['ocr_engine_id'] = Variable<String>(ocrEngineId);
    }
    if (!nullToAbsent || ocrConfidence != null) {
      map['ocr_confidence'] = Variable<double>(ocrConfidence);
    }
    if (!nullToAbsent || ocrRawText != null) {
      map['ocr_raw_text'] = Variable<String>(ocrRawText);
    }
    map['adjusted_by_user'] = Variable<bool>(adjustedByUser);
    if (!nullToAbsent || photoPath != null) {
      map['photo_path'] = Variable<String>(photoPath);
    }
    if (!nullToAbsent || note != null) {
      map['note'] = Variable<String>(note);
    }
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || deletedAt != null) {
      map['deleted_at'] = Variable<DateTime>(deletedAt);
    }
    {
      map['sync_state'] = Variable<int>(
        $GlucoseReadingRowsTable.$convertersyncState.toSql(syncState),
      );
    }
    return map;
  }

  GlucoseReadingRowsCompanion toCompanion(bool nullToAbsent) {
    return GlucoseReadingRowsCompanion(
      id: Value(id),
      measuredAtUtc: Value(measuredAtUtc),
      tzName: Value(tzName),
      utcOffsetMinutes: Value(utcOffsetMinutes),
      valueMgdl: Value(valueMgdl),
      enteredUnit: Value(enteredUnit),
      enteredValue: Value(enteredValue),
      tag: Value(tag),
      source: Value(source),
      ocrEngineId: ocrEngineId == null && nullToAbsent
          ? const Value.absent()
          : Value(ocrEngineId),
      ocrConfidence: ocrConfidence == null && nullToAbsent
          ? const Value.absent()
          : Value(ocrConfidence),
      ocrRawText: ocrRawText == null && nullToAbsent
          ? const Value.absent()
          : Value(ocrRawText),
      adjustedByUser: Value(adjustedByUser),
      photoPath: photoPath == null && nullToAbsent
          ? const Value.absent()
          : Value(photoPath),
      note: note == null && nullToAbsent ? const Value.absent() : Value(note),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      deletedAt: deletedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(deletedAt),
      syncState: Value(syncState),
    );
  }

  factory GlucoseReadingRow.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return GlucoseReadingRow(
      id: serializer.fromJson<String>(json['id']),
      measuredAtUtc: serializer.fromJson<DateTime>(json['measuredAtUtc']),
      tzName: serializer.fromJson<String>(json['tzName']),
      utcOffsetMinutes: serializer.fromJson<int>(json['utcOffsetMinutes']),
      valueMgdl: serializer.fromJson<double>(json['valueMgdl']),
      enteredUnit: serializer.fromJson<GlucoseUnit>(json['enteredUnit']),
      enteredValue: serializer.fromJson<double>(json['enteredValue']),
      tag: serializer.fromJson<MeasurementTag>(json['tag']),
      source: serializer.fromJson<ReadingSource>(json['source']),
      ocrEngineId: serializer.fromJson<String?>(json['ocrEngineId']),
      ocrConfidence: serializer.fromJson<double?>(json['ocrConfidence']),
      ocrRawText: serializer.fromJson<String?>(json['ocrRawText']),
      adjustedByUser: serializer.fromJson<bool>(json['adjustedByUser']),
      photoPath: serializer.fromJson<String?>(json['photoPath']),
      note: serializer.fromJson<String?>(json['note']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      deletedAt: serializer.fromJson<DateTime?>(json['deletedAt']),
      syncState: $GlucoseReadingRowsTable.$convertersyncState.fromJson(
        serializer.fromJson<int>(json['syncState']),
      ),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'measuredAtUtc': serializer.toJson<DateTime>(measuredAtUtc),
      'tzName': serializer.toJson<String>(tzName),
      'utcOffsetMinutes': serializer.toJson<int>(utcOffsetMinutes),
      'valueMgdl': serializer.toJson<double>(valueMgdl),
      'enteredUnit': serializer.toJson<GlucoseUnit>(enteredUnit),
      'enteredValue': serializer.toJson<double>(enteredValue),
      'tag': serializer.toJson<MeasurementTag>(tag),
      'source': serializer.toJson<ReadingSource>(source),
      'ocrEngineId': serializer.toJson<String?>(ocrEngineId),
      'ocrConfidence': serializer.toJson<double?>(ocrConfidence),
      'ocrRawText': serializer.toJson<String?>(ocrRawText),
      'adjustedByUser': serializer.toJson<bool>(adjustedByUser),
      'photoPath': serializer.toJson<String?>(photoPath),
      'note': serializer.toJson<String?>(note),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'deletedAt': serializer.toJson<DateTime?>(deletedAt),
      'syncState': serializer.toJson<int>(
        $GlucoseReadingRowsTable.$convertersyncState.toJson(syncState),
      ),
    };
  }

  GlucoseReadingRow copyWith({
    String? id,
    DateTime? measuredAtUtc,
    String? tzName,
    int? utcOffsetMinutes,
    double? valueMgdl,
    GlucoseUnit? enteredUnit,
    double? enteredValue,
    MeasurementTag? tag,
    ReadingSource? source,
    Value<String?> ocrEngineId = const Value.absent(),
    Value<double?> ocrConfidence = const Value.absent(),
    Value<String?> ocrRawText = const Value.absent(),
    bool? adjustedByUser,
    Value<String?> photoPath = const Value.absent(),
    Value<String?> note = const Value.absent(),
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<DateTime?> deletedAt = const Value.absent(),
    SyncState? syncState,
  }) => GlucoseReadingRow(
    id: id ?? this.id,
    measuredAtUtc: measuredAtUtc ?? this.measuredAtUtc,
    tzName: tzName ?? this.tzName,
    utcOffsetMinutes: utcOffsetMinutes ?? this.utcOffsetMinutes,
    valueMgdl: valueMgdl ?? this.valueMgdl,
    enteredUnit: enteredUnit ?? this.enteredUnit,
    enteredValue: enteredValue ?? this.enteredValue,
    tag: tag ?? this.tag,
    source: source ?? this.source,
    ocrEngineId: ocrEngineId.present ? ocrEngineId.value : this.ocrEngineId,
    ocrConfidence: ocrConfidence.present
        ? ocrConfidence.value
        : this.ocrConfidence,
    ocrRawText: ocrRawText.present ? ocrRawText.value : this.ocrRawText,
    adjustedByUser: adjustedByUser ?? this.adjustedByUser,
    photoPath: photoPath.present ? photoPath.value : this.photoPath,
    note: note.present ? note.value : this.note,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    deletedAt: deletedAt.present ? deletedAt.value : this.deletedAt,
    syncState: syncState ?? this.syncState,
  );
  GlucoseReadingRow copyWithCompanion(GlucoseReadingRowsCompanion data) {
    return GlucoseReadingRow(
      id: data.id.present ? data.id.value : this.id,
      measuredAtUtc: data.measuredAtUtc.present
          ? data.measuredAtUtc.value
          : this.measuredAtUtc,
      tzName: data.tzName.present ? data.tzName.value : this.tzName,
      utcOffsetMinutes: data.utcOffsetMinutes.present
          ? data.utcOffsetMinutes.value
          : this.utcOffsetMinutes,
      valueMgdl: data.valueMgdl.present ? data.valueMgdl.value : this.valueMgdl,
      enteredUnit: data.enteredUnit.present
          ? data.enteredUnit.value
          : this.enteredUnit,
      enteredValue: data.enteredValue.present
          ? data.enteredValue.value
          : this.enteredValue,
      tag: data.tag.present ? data.tag.value : this.tag,
      source: data.source.present ? data.source.value : this.source,
      ocrEngineId: data.ocrEngineId.present
          ? data.ocrEngineId.value
          : this.ocrEngineId,
      ocrConfidence: data.ocrConfidence.present
          ? data.ocrConfidence.value
          : this.ocrConfidence,
      ocrRawText: data.ocrRawText.present
          ? data.ocrRawText.value
          : this.ocrRawText,
      adjustedByUser: data.adjustedByUser.present
          ? data.adjustedByUser.value
          : this.adjustedByUser,
      photoPath: data.photoPath.present ? data.photoPath.value : this.photoPath,
      note: data.note.present ? data.note.value : this.note,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      deletedAt: data.deletedAt.present ? data.deletedAt.value : this.deletedAt,
      syncState: data.syncState.present ? data.syncState.value : this.syncState,
    );
  }

  @override
  String toString() {
    return (StringBuffer('GlucoseReadingRow(')
          ..write('id: $id, ')
          ..write('measuredAtUtc: $measuredAtUtc, ')
          ..write('tzName: $tzName, ')
          ..write('utcOffsetMinutes: $utcOffsetMinutes, ')
          ..write('valueMgdl: $valueMgdl, ')
          ..write('enteredUnit: $enteredUnit, ')
          ..write('enteredValue: $enteredValue, ')
          ..write('tag: $tag, ')
          ..write('source: $source, ')
          ..write('ocrEngineId: $ocrEngineId, ')
          ..write('ocrConfidence: $ocrConfidence, ')
          ..write('ocrRawText: $ocrRawText, ')
          ..write('adjustedByUser: $adjustedByUser, ')
          ..write('photoPath: $photoPath, ')
          ..write('note: $note, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('syncState: $syncState')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    measuredAtUtc,
    tzName,
    utcOffsetMinutes,
    valueMgdl,
    enteredUnit,
    enteredValue,
    tag,
    source,
    ocrEngineId,
    ocrConfidence,
    ocrRawText,
    adjustedByUser,
    photoPath,
    note,
    createdAt,
    updatedAt,
    deletedAt,
    syncState,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is GlucoseReadingRow &&
          other.id == this.id &&
          other.measuredAtUtc == this.measuredAtUtc &&
          other.tzName == this.tzName &&
          other.utcOffsetMinutes == this.utcOffsetMinutes &&
          other.valueMgdl == this.valueMgdl &&
          other.enteredUnit == this.enteredUnit &&
          other.enteredValue == this.enteredValue &&
          other.tag == this.tag &&
          other.source == this.source &&
          other.ocrEngineId == this.ocrEngineId &&
          other.ocrConfidence == this.ocrConfidence &&
          other.ocrRawText == this.ocrRawText &&
          other.adjustedByUser == this.adjustedByUser &&
          other.photoPath == this.photoPath &&
          other.note == this.note &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.deletedAt == this.deletedAt &&
          other.syncState == this.syncState);
}

class GlucoseReadingRowsCompanion extends UpdateCompanion<GlucoseReadingRow> {
  final Value<String> id;
  final Value<DateTime> measuredAtUtc;
  final Value<String> tzName;
  final Value<int> utcOffsetMinutes;
  final Value<double> valueMgdl;
  final Value<GlucoseUnit> enteredUnit;
  final Value<double> enteredValue;
  final Value<MeasurementTag> tag;
  final Value<ReadingSource> source;
  final Value<String?> ocrEngineId;
  final Value<double?> ocrConfidence;
  final Value<String?> ocrRawText;
  final Value<bool> adjustedByUser;
  final Value<String?> photoPath;
  final Value<String?> note;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<DateTime?> deletedAt;
  final Value<SyncState> syncState;
  final Value<int> rowid;
  const GlucoseReadingRowsCompanion({
    this.id = const Value.absent(),
    this.measuredAtUtc = const Value.absent(),
    this.tzName = const Value.absent(),
    this.utcOffsetMinutes = const Value.absent(),
    this.valueMgdl = const Value.absent(),
    this.enteredUnit = const Value.absent(),
    this.enteredValue = const Value.absent(),
    this.tag = const Value.absent(),
    this.source = const Value.absent(),
    this.ocrEngineId = const Value.absent(),
    this.ocrConfidence = const Value.absent(),
    this.ocrRawText = const Value.absent(),
    this.adjustedByUser = const Value.absent(),
    this.photoPath = const Value.absent(),
    this.note = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.deletedAt = const Value.absent(),
    this.syncState = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  GlucoseReadingRowsCompanion.insert({
    required String id,
    required DateTime measuredAtUtc,
    required String tzName,
    required int utcOffsetMinutes,
    required double valueMgdl,
    required GlucoseUnit enteredUnit,
    required double enteredValue,
    required MeasurementTag tag,
    required ReadingSource source,
    this.ocrEngineId = const Value.absent(),
    this.ocrConfidence = const Value.absent(),
    this.ocrRawText = const Value.absent(),
    this.adjustedByUser = const Value.absent(),
    this.photoPath = const Value.absent(),
    this.note = const Value.absent(),
    required DateTime createdAt,
    required DateTime updatedAt,
    this.deletedAt = const Value.absent(),
    required SyncState syncState,
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       measuredAtUtc = Value(measuredAtUtc),
       tzName = Value(tzName),
       utcOffsetMinutes = Value(utcOffsetMinutes),
       valueMgdl = Value(valueMgdl),
       enteredUnit = Value(enteredUnit),
       enteredValue = Value(enteredValue),
       tag = Value(tag),
       source = Value(source),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt),
       syncState = Value(syncState);
  static Insertable<GlucoseReadingRow> custom({
    Expression<String>? id,
    Expression<DateTime>? measuredAtUtc,
    Expression<String>? tzName,
    Expression<int>? utcOffsetMinutes,
    Expression<double>? valueMgdl,
    Expression<String>? enteredUnit,
    Expression<double>? enteredValue,
    Expression<String>? tag,
    Expression<String>? source,
    Expression<String>? ocrEngineId,
    Expression<double>? ocrConfidence,
    Expression<String>? ocrRawText,
    Expression<bool>? adjustedByUser,
    Expression<String>? photoPath,
    Expression<String>? note,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<DateTime>? deletedAt,
    Expression<int>? syncState,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (measuredAtUtc != null) 'measured_at_utc': measuredAtUtc,
      if (tzName != null) 'tz_name': tzName,
      if (utcOffsetMinutes != null) 'utc_offset_minutes': utcOffsetMinutes,
      if (valueMgdl != null) 'value_mgdl': valueMgdl,
      if (enteredUnit != null) 'entered_unit': enteredUnit,
      if (enteredValue != null) 'entered_value': enteredValue,
      if (tag != null) 'tag': tag,
      if (source != null) 'source': source,
      if (ocrEngineId != null) 'ocr_engine_id': ocrEngineId,
      if (ocrConfidence != null) 'ocr_confidence': ocrConfidence,
      if (ocrRawText != null) 'ocr_raw_text': ocrRawText,
      if (adjustedByUser != null) 'adjusted_by_user': adjustedByUser,
      if (photoPath != null) 'photo_path': photoPath,
      if (note != null) 'note': note,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (deletedAt != null) 'deleted_at': deletedAt,
      if (syncState != null) 'sync_state': syncState,
      if (rowid != null) 'rowid': rowid,
    });
  }

  GlucoseReadingRowsCompanion copyWith({
    Value<String>? id,
    Value<DateTime>? measuredAtUtc,
    Value<String>? tzName,
    Value<int>? utcOffsetMinutes,
    Value<double>? valueMgdl,
    Value<GlucoseUnit>? enteredUnit,
    Value<double>? enteredValue,
    Value<MeasurementTag>? tag,
    Value<ReadingSource>? source,
    Value<String?>? ocrEngineId,
    Value<double?>? ocrConfidence,
    Value<String?>? ocrRawText,
    Value<bool>? adjustedByUser,
    Value<String?>? photoPath,
    Value<String?>? note,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<DateTime?>? deletedAt,
    Value<SyncState>? syncState,
    Value<int>? rowid,
  }) {
    return GlucoseReadingRowsCompanion(
      id: id ?? this.id,
      measuredAtUtc: measuredAtUtc ?? this.measuredAtUtc,
      tzName: tzName ?? this.tzName,
      utcOffsetMinutes: utcOffsetMinutes ?? this.utcOffsetMinutes,
      valueMgdl: valueMgdl ?? this.valueMgdl,
      enteredUnit: enteredUnit ?? this.enteredUnit,
      enteredValue: enteredValue ?? this.enteredValue,
      tag: tag ?? this.tag,
      source: source ?? this.source,
      ocrEngineId: ocrEngineId ?? this.ocrEngineId,
      ocrConfidence: ocrConfidence ?? this.ocrConfidence,
      ocrRawText: ocrRawText ?? this.ocrRawText,
      adjustedByUser: adjustedByUser ?? this.adjustedByUser,
      photoPath: photoPath ?? this.photoPath,
      note: note ?? this.note,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      deletedAt: deletedAt ?? this.deletedAt,
      syncState: syncState ?? this.syncState,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (measuredAtUtc.present) {
      map['measured_at_utc'] = Variable<DateTime>(measuredAtUtc.value);
    }
    if (tzName.present) {
      map['tz_name'] = Variable<String>(tzName.value);
    }
    if (utcOffsetMinutes.present) {
      map['utc_offset_minutes'] = Variable<int>(utcOffsetMinutes.value);
    }
    if (valueMgdl.present) {
      map['value_mgdl'] = Variable<double>(valueMgdl.value);
    }
    if (enteredUnit.present) {
      map['entered_unit'] = Variable<String>(
        $GlucoseReadingRowsTable.$converterenteredUnit.toSql(enteredUnit.value),
      );
    }
    if (enteredValue.present) {
      map['entered_value'] = Variable<double>(enteredValue.value);
    }
    if (tag.present) {
      map['tag'] = Variable<String>(
        $GlucoseReadingRowsTable.$convertertag.toSql(tag.value),
      );
    }
    if (source.present) {
      map['source'] = Variable<String>(
        $GlucoseReadingRowsTable.$convertersource.toSql(source.value),
      );
    }
    if (ocrEngineId.present) {
      map['ocr_engine_id'] = Variable<String>(ocrEngineId.value);
    }
    if (ocrConfidence.present) {
      map['ocr_confidence'] = Variable<double>(ocrConfidence.value);
    }
    if (ocrRawText.present) {
      map['ocr_raw_text'] = Variable<String>(ocrRawText.value);
    }
    if (adjustedByUser.present) {
      map['adjusted_by_user'] = Variable<bool>(adjustedByUser.value);
    }
    if (photoPath.present) {
      map['photo_path'] = Variable<String>(photoPath.value);
    }
    if (note.present) {
      map['note'] = Variable<String>(note.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (deletedAt.present) {
      map['deleted_at'] = Variable<DateTime>(deletedAt.value);
    }
    if (syncState.present) {
      map['sync_state'] = Variable<int>(
        $GlucoseReadingRowsTable.$convertersyncState.toSql(syncState.value),
      );
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('GlucoseReadingRowsCompanion(')
          ..write('id: $id, ')
          ..write('measuredAtUtc: $measuredAtUtc, ')
          ..write('tzName: $tzName, ')
          ..write('utcOffsetMinutes: $utcOffsetMinutes, ')
          ..write('valueMgdl: $valueMgdl, ')
          ..write('enteredUnit: $enteredUnit, ')
          ..write('enteredValue: $enteredValue, ')
          ..write('tag: $tag, ')
          ..write('source: $source, ')
          ..write('ocrEngineId: $ocrEngineId, ')
          ..write('ocrConfidence: $ocrConfidence, ')
          ..write('ocrRawText: $ocrRawText, ')
          ..write('adjustedByUser: $adjustedByUser, ')
          ..write('photoPath: $photoPath, ')
          ..write('note: $note, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('deletedAt: $deletedAt, ')
          ..write('syncState: $syncState, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $SyncOutboxRowsTable extends SyncOutboxRows
    with TableInfo<$SyncOutboxRowsTable, SyncOutboxRow> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SyncOutboxRowsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _seqMeta = const VerificationMeta('seq');
  @override
  late final GeneratedColumn<int> seq = GeneratedColumn<int>(
    'seq',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _entityMeta = const VerificationMeta('entity');
  @override
  late final GeneratedColumn<String> entity = GeneratedColumn<String>(
    'entity',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _entityIdMeta = const VerificationMeta(
    'entityId',
  );
  @override
  late final GeneratedColumn<String> entityId = GeneratedColumn<String>(
    'entity_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _opMeta = const VerificationMeta('op');
  @override
  late final GeneratedColumn<String> op = GeneratedColumn<String>(
    'op',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _attemptsMeta = const VerificationMeta(
    'attempts',
  );
  @override
  late final GeneratedColumn<int> attempts = GeneratedColumn<int>(
    'attempts',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _lastErrorMeta = const VerificationMeta(
    'lastError',
  );
  @override
  late final GeneratedColumn<String> lastError = GeneratedColumn<String>(
    'last_error',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    seq,
    entity,
    entityId,
    op,
    createdAt,
    attempts,
    lastError,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'sync_outbox';
  @override
  VerificationContext validateIntegrity(
    Insertable<SyncOutboxRow> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('seq')) {
      context.handle(
        _seqMeta,
        seq.isAcceptableOrUnknown(data['seq']!, _seqMeta),
      );
    }
    if (data.containsKey('entity')) {
      context.handle(
        _entityMeta,
        entity.isAcceptableOrUnknown(data['entity']!, _entityMeta),
      );
    } else if (isInserting) {
      context.missing(_entityMeta);
    }
    if (data.containsKey('entity_id')) {
      context.handle(
        _entityIdMeta,
        entityId.isAcceptableOrUnknown(data['entity_id']!, _entityIdMeta),
      );
    } else if (isInserting) {
      context.missing(_entityIdMeta);
    }
    if (data.containsKey('op')) {
      context.handle(_opMeta, op.isAcceptableOrUnknown(data['op']!, _opMeta));
    } else if (isInserting) {
      context.missing(_opMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('attempts')) {
      context.handle(
        _attemptsMeta,
        attempts.isAcceptableOrUnknown(data['attempts']!, _attemptsMeta),
      );
    }
    if (data.containsKey('last_error')) {
      context.handle(
        _lastErrorMeta,
        lastError.isAcceptableOrUnknown(data['last_error']!, _lastErrorMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {seq};
  @override
  SyncOutboxRow map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SyncOutboxRow(
      seq: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}seq'],
      )!,
      entity: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}entity'],
      )!,
      entityId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}entity_id'],
      )!,
      op: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}op'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      attempts: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}attempts'],
      )!,
      lastError: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}last_error'],
      ),
    );
  }

  @override
  $SyncOutboxRowsTable createAlias(String alias) {
    return $SyncOutboxRowsTable(attachedDatabase, alias);
  }
}

class SyncOutboxRow extends DataClass implements Insertable<SyncOutboxRow> {
  final int seq;
  final String entity;
  final String entityId;

  /// `upsert` / `delete`.
  final String op;
  final DateTime createdAt;
  final int attempts;
  final String? lastError;
  const SyncOutboxRow({
    required this.seq,
    required this.entity,
    required this.entityId,
    required this.op,
    required this.createdAt,
    required this.attempts,
    this.lastError,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['seq'] = Variable<int>(seq);
    map['entity'] = Variable<String>(entity);
    map['entity_id'] = Variable<String>(entityId);
    map['op'] = Variable<String>(op);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['attempts'] = Variable<int>(attempts);
    if (!nullToAbsent || lastError != null) {
      map['last_error'] = Variable<String>(lastError);
    }
    return map;
  }

  SyncOutboxRowsCompanion toCompanion(bool nullToAbsent) {
    return SyncOutboxRowsCompanion(
      seq: Value(seq),
      entity: Value(entity),
      entityId: Value(entityId),
      op: Value(op),
      createdAt: Value(createdAt),
      attempts: Value(attempts),
      lastError: lastError == null && nullToAbsent
          ? const Value.absent()
          : Value(lastError),
    );
  }

  factory SyncOutboxRow.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SyncOutboxRow(
      seq: serializer.fromJson<int>(json['seq']),
      entity: serializer.fromJson<String>(json['entity']),
      entityId: serializer.fromJson<String>(json['entityId']),
      op: serializer.fromJson<String>(json['op']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      attempts: serializer.fromJson<int>(json['attempts']),
      lastError: serializer.fromJson<String?>(json['lastError']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'seq': serializer.toJson<int>(seq),
      'entity': serializer.toJson<String>(entity),
      'entityId': serializer.toJson<String>(entityId),
      'op': serializer.toJson<String>(op),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'attempts': serializer.toJson<int>(attempts),
      'lastError': serializer.toJson<String?>(lastError),
    };
  }

  SyncOutboxRow copyWith({
    int? seq,
    String? entity,
    String? entityId,
    String? op,
    DateTime? createdAt,
    int? attempts,
    Value<String?> lastError = const Value.absent(),
  }) => SyncOutboxRow(
    seq: seq ?? this.seq,
    entity: entity ?? this.entity,
    entityId: entityId ?? this.entityId,
    op: op ?? this.op,
    createdAt: createdAt ?? this.createdAt,
    attempts: attempts ?? this.attempts,
    lastError: lastError.present ? lastError.value : this.lastError,
  );
  SyncOutboxRow copyWithCompanion(SyncOutboxRowsCompanion data) {
    return SyncOutboxRow(
      seq: data.seq.present ? data.seq.value : this.seq,
      entity: data.entity.present ? data.entity.value : this.entity,
      entityId: data.entityId.present ? data.entityId.value : this.entityId,
      op: data.op.present ? data.op.value : this.op,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      attempts: data.attempts.present ? data.attempts.value : this.attempts,
      lastError: data.lastError.present ? data.lastError.value : this.lastError,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SyncOutboxRow(')
          ..write('seq: $seq, ')
          ..write('entity: $entity, ')
          ..write('entityId: $entityId, ')
          ..write('op: $op, ')
          ..write('createdAt: $createdAt, ')
          ..write('attempts: $attempts, ')
          ..write('lastError: $lastError')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(seq, entity, entityId, op, createdAt, attempts, lastError);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SyncOutboxRow &&
          other.seq == this.seq &&
          other.entity == this.entity &&
          other.entityId == this.entityId &&
          other.op == this.op &&
          other.createdAt == this.createdAt &&
          other.attempts == this.attempts &&
          other.lastError == this.lastError);
}

class SyncOutboxRowsCompanion extends UpdateCompanion<SyncOutboxRow> {
  final Value<int> seq;
  final Value<String> entity;
  final Value<String> entityId;
  final Value<String> op;
  final Value<DateTime> createdAt;
  final Value<int> attempts;
  final Value<String?> lastError;
  const SyncOutboxRowsCompanion({
    this.seq = const Value.absent(),
    this.entity = const Value.absent(),
    this.entityId = const Value.absent(),
    this.op = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.attempts = const Value.absent(),
    this.lastError = const Value.absent(),
  });
  SyncOutboxRowsCompanion.insert({
    this.seq = const Value.absent(),
    required String entity,
    required String entityId,
    required String op,
    required DateTime createdAt,
    this.attempts = const Value.absent(),
    this.lastError = const Value.absent(),
  }) : entity = Value(entity),
       entityId = Value(entityId),
       op = Value(op),
       createdAt = Value(createdAt);
  static Insertable<SyncOutboxRow> custom({
    Expression<int>? seq,
    Expression<String>? entity,
    Expression<String>? entityId,
    Expression<String>? op,
    Expression<DateTime>? createdAt,
    Expression<int>? attempts,
    Expression<String>? lastError,
  }) {
    return RawValuesInsertable({
      if (seq != null) 'seq': seq,
      if (entity != null) 'entity': entity,
      if (entityId != null) 'entity_id': entityId,
      if (op != null) 'op': op,
      if (createdAt != null) 'created_at': createdAt,
      if (attempts != null) 'attempts': attempts,
      if (lastError != null) 'last_error': lastError,
    });
  }

  SyncOutboxRowsCompanion copyWith({
    Value<int>? seq,
    Value<String>? entity,
    Value<String>? entityId,
    Value<String>? op,
    Value<DateTime>? createdAt,
    Value<int>? attempts,
    Value<String?>? lastError,
  }) {
    return SyncOutboxRowsCompanion(
      seq: seq ?? this.seq,
      entity: entity ?? this.entity,
      entityId: entityId ?? this.entityId,
      op: op ?? this.op,
      createdAt: createdAt ?? this.createdAt,
      attempts: attempts ?? this.attempts,
      lastError: lastError ?? this.lastError,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (seq.present) {
      map['seq'] = Variable<int>(seq.value);
    }
    if (entity.present) {
      map['entity'] = Variable<String>(entity.value);
    }
    if (entityId.present) {
      map['entity_id'] = Variable<String>(entityId.value);
    }
    if (op.present) {
      map['op'] = Variable<String>(op.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (attempts.present) {
      map['attempts'] = Variable<int>(attempts.value);
    }
    if (lastError.present) {
      map['last_error'] = Variable<String>(lastError.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SyncOutboxRowsCompanion(')
          ..write('seq: $seq, ')
          ..write('entity: $entity, ')
          ..write('entityId: $entityId, ')
          ..write('op: $op, ')
          ..write('createdAt: $createdAt, ')
          ..write('attempts: $attempts, ')
          ..write('lastError: $lastError')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $GlucoseReadingRowsTable glucoseReadingRows =
      $GlucoseReadingRowsTable(this);
  late final $SyncOutboxRowsTable syncOutboxRows = $SyncOutboxRowsTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    glucoseReadingRows,
    syncOutboxRows,
  ];
}

typedef $$GlucoseReadingRowsTableCreateCompanionBuilder =
    GlucoseReadingRowsCompanion Function({
      required String id,
      required DateTime measuredAtUtc,
      required String tzName,
      required int utcOffsetMinutes,
      required double valueMgdl,
      required GlucoseUnit enteredUnit,
      required double enteredValue,
      required MeasurementTag tag,
      required ReadingSource source,
      Value<String?> ocrEngineId,
      Value<double?> ocrConfidence,
      Value<String?> ocrRawText,
      Value<bool> adjustedByUser,
      Value<String?> photoPath,
      Value<String?> note,
      required DateTime createdAt,
      required DateTime updatedAt,
      Value<DateTime?> deletedAt,
      required SyncState syncState,
      Value<int> rowid,
    });
typedef $$GlucoseReadingRowsTableUpdateCompanionBuilder =
    GlucoseReadingRowsCompanion Function({
      Value<String> id,
      Value<DateTime> measuredAtUtc,
      Value<String> tzName,
      Value<int> utcOffsetMinutes,
      Value<double> valueMgdl,
      Value<GlucoseUnit> enteredUnit,
      Value<double> enteredValue,
      Value<MeasurementTag> tag,
      Value<ReadingSource> source,
      Value<String?> ocrEngineId,
      Value<double?> ocrConfidence,
      Value<String?> ocrRawText,
      Value<bool> adjustedByUser,
      Value<String?> photoPath,
      Value<String?> note,
      Value<DateTime> createdAt,
      Value<DateTime> updatedAt,
      Value<DateTime?> deletedAt,
      Value<SyncState> syncState,
      Value<int> rowid,
    });

class $$GlucoseReadingRowsTableFilterComposer
    extends Composer<_$AppDatabase, $GlucoseReadingRowsTable> {
  $$GlucoseReadingRowsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get measuredAtUtc => $composableBuilder(
    column: $table.measuredAtUtc,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get tzName => $composableBuilder(
    column: $table.tzName,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get utcOffsetMinutes => $composableBuilder(
    column: $table.utcOffsetMinutes,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get valueMgdl => $composableBuilder(
    column: $table.valueMgdl,
    builder: (column) => ColumnFilters(column),
  );

  ColumnWithTypeConverterFilters<GlucoseUnit, GlucoseUnit, String>
  get enteredUnit => $composableBuilder(
    column: $table.enteredUnit,
    builder: (column) => ColumnWithTypeConverterFilters(column),
  );

  ColumnFilters<double> get enteredValue => $composableBuilder(
    column: $table.enteredValue,
    builder: (column) => ColumnFilters(column),
  );

  ColumnWithTypeConverterFilters<MeasurementTag, MeasurementTag, String>
  get tag => $composableBuilder(
    column: $table.tag,
    builder: (column) => ColumnWithTypeConverterFilters(column),
  );

  ColumnWithTypeConverterFilters<ReadingSource, ReadingSource, String>
  get source => $composableBuilder(
    column: $table.source,
    builder: (column) => ColumnWithTypeConverterFilters(column),
  );

  ColumnFilters<String> get ocrEngineId => $composableBuilder(
    column: $table.ocrEngineId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get ocrConfidence => $composableBuilder(
    column: $table.ocrConfidence,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get ocrRawText => $composableBuilder(
    column: $table.ocrRawText,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get adjustedByUser => $composableBuilder(
    column: $table.adjustedByUser,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get photoPath => $composableBuilder(
    column: $table.photoPath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get note => $composableBuilder(
    column: $table.note,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get deletedAt => $composableBuilder(
    column: $table.deletedAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnWithTypeConverterFilters<SyncState, SyncState, int> get syncState =>
      $composableBuilder(
        column: $table.syncState,
        builder: (column) => ColumnWithTypeConverterFilters(column),
      );
}

class $$GlucoseReadingRowsTableOrderingComposer
    extends Composer<_$AppDatabase, $GlucoseReadingRowsTable> {
  $$GlucoseReadingRowsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get measuredAtUtc => $composableBuilder(
    column: $table.measuredAtUtc,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get tzName => $composableBuilder(
    column: $table.tzName,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get utcOffsetMinutes => $composableBuilder(
    column: $table.utcOffsetMinutes,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get valueMgdl => $composableBuilder(
    column: $table.valueMgdl,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get enteredUnit => $composableBuilder(
    column: $table.enteredUnit,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get enteredValue => $composableBuilder(
    column: $table.enteredValue,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get tag => $composableBuilder(
    column: $table.tag,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get source => $composableBuilder(
    column: $table.source,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get ocrEngineId => $composableBuilder(
    column: $table.ocrEngineId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get ocrConfidence => $composableBuilder(
    column: $table.ocrConfidence,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get ocrRawText => $composableBuilder(
    column: $table.ocrRawText,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get adjustedByUser => $composableBuilder(
    column: $table.adjustedByUser,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get photoPath => $composableBuilder(
    column: $table.photoPath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get note => $composableBuilder(
    column: $table.note,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get deletedAt => $composableBuilder(
    column: $table.deletedAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get syncState => $composableBuilder(
    column: $table.syncState,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$GlucoseReadingRowsTableAnnotationComposer
    extends Composer<_$AppDatabase, $GlucoseReadingRowsTable> {
  $$GlucoseReadingRowsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<DateTime> get measuredAtUtc => $composableBuilder(
    column: $table.measuredAtUtc,
    builder: (column) => column,
  );

  GeneratedColumn<String> get tzName =>
      $composableBuilder(column: $table.tzName, builder: (column) => column);

  GeneratedColumn<int> get utcOffsetMinutes => $composableBuilder(
    column: $table.utcOffsetMinutes,
    builder: (column) => column,
  );

  GeneratedColumn<double> get valueMgdl =>
      $composableBuilder(column: $table.valueMgdl, builder: (column) => column);

  GeneratedColumnWithTypeConverter<GlucoseUnit, String> get enteredUnit =>
      $composableBuilder(
        column: $table.enteredUnit,
        builder: (column) => column,
      );

  GeneratedColumn<double> get enteredValue => $composableBuilder(
    column: $table.enteredValue,
    builder: (column) => column,
  );

  GeneratedColumnWithTypeConverter<MeasurementTag, String> get tag =>
      $composableBuilder(column: $table.tag, builder: (column) => column);

  GeneratedColumnWithTypeConverter<ReadingSource, String> get source =>
      $composableBuilder(column: $table.source, builder: (column) => column);

  GeneratedColumn<String> get ocrEngineId => $composableBuilder(
    column: $table.ocrEngineId,
    builder: (column) => column,
  );

  GeneratedColumn<double> get ocrConfidence => $composableBuilder(
    column: $table.ocrConfidence,
    builder: (column) => column,
  );

  GeneratedColumn<String> get ocrRawText => $composableBuilder(
    column: $table.ocrRawText,
    builder: (column) => column,
  );

  GeneratedColumn<bool> get adjustedByUser => $composableBuilder(
    column: $table.adjustedByUser,
    builder: (column) => column,
  );

  GeneratedColumn<String> get photoPath =>
      $composableBuilder(column: $table.photoPath, builder: (column) => column);

  GeneratedColumn<String> get note =>
      $composableBuilder(column: $table.note, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<DateTime> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);

  GeneratedColumn<DateTime> get deletedAt =>
      $composableBuilder(column: $table.deletedAt, builder: (column) => column);

  GeneratedColumnWithTypeConverter<SyncState, int> get syncState =>
      $composableBuilder(column: $table.syncState, builder: (column) => column);
}

class $$GlucoseReadingRowsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $GlucoseReadingRowsTable,
          GlucoseReadingRow,
          $$GlucoseReadingRowsTableFilterComposer,
          $$GlucoseReadingRowsTableOrderingComposer,
          $$GlucoseReadingRowsTableAnnotationComposer,
          $$GlucoseReadingRowsTableCreateCompanionBuilder,
          $$GlucoseReadingRowsTableUpdateCompanionBuilder,
          (
            GlucoseReadingRow,
            BaseReferences<
              _$AppDatabase,
              $GlucoseReadingRowsTable,
              GlucoseReadingRow
            >,
          ),
          GlucoseReadingRow,
          PrefetchHooks Function()
        > {
  $$GlucoseReadingRowsTableTableManager(
    _$AppDatabase db,
    $GlucoseReadingRowsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$GlucoseReadingRowsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$GlucoseReadingRowsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$GlucoseReadingRowsTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<DateTime> measuredAtUtc = const Value.absent(),
                Value<String> tzName = const Value.absent(),
                Value<int> utcOffsetMinutes = const Value.absent(),
                Value<double> valueMgdl = const Value.absent(),
                Value<GlucoseUnit> enteredUnit = const Value.absent(),
                Value<double> enteredValue = const Value.absent(),
                Value<MeasurementTag> tag = const Value.absent(),
                Value<ReadingSource> source = const Value.absent(),
                Value<String?> ocrEngineId = const Value.absent(),
                Value<double?> ocrConfidence = const Value.absent(),
                Value<String?> ocrRawText = const Value.absent(),
                Value<bool> adjustedByUser = const Value.absent(),
                Value<String?> photoPath = const Value.absent(),
                Value<String?> note = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<DateTime> updatedAt = const Value.absent(),
                Value<DateTime?> deletedAt = const Value.absent(),
                Value<SyncState> syncState = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => GlucoseReadingRowsCompanion(
                id: id,
                measuredAtUtc: measuredAtUtc,
                tzName: tzName,
                utcOffsetMinutes: utcOffsetMinutes,
                valueMgdl: valueMgdl,
                enteredUnit: enteredUnit,
                enteredValue: enteredValue,
                tag: tag,
                source: source,
                ocrEngineId: ocrEngineId,
                ocrConfidence: ocrConfidence,
                ocrRawText: ocrRawText,
                adjustedByUser: adjustedByUser,
                photoPath: photoPath,
                note: note,
                createdAt: createdAt,
                updatedAt: updatedAt,
                deletedAt: deletedAt,
                syncState: syncState,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required DateTime measuredAtUtc,
                required String tzName,
                required int utcOffsetMinutes,
                required double valueMgdl,
                required GlucoseUnit enteredUnit,
                required double enteredValue,
                required MeasurementTag tag,
                required ReadingSource source,
                Value<String?> ocrEngineId = const Value.absent(),
                Value<double?> ocrConfidence = const Value.absent(),
                Value<String?> ocrRawText = const Value.absent(),
                Value<bool> adjustedByUser = const Value.absent(),
                Value<String?> photoPath = const Value.absent(),
                Value<String?> note = const Value.absent(),
                required DateTime createdAt,
                required DateTime updatedAt,
                Value<DateTime?> deletedAt = const Value.absent(),
                required SyncState syncState,
                Value<int> rowid = const Value.absent(),
              }) => GlucoseReadingRowsCompanion.insert(
                id: id,
                measuredAtUtc: measuredAtUtc,
                tzName: tzName,
                utcOffsetMinutes: utcOffsetMinutes,
                valueMgdl: valueMgdl,
                enteredUnit: enteredUnit,
                enteredValue: enteredValue,
                tag: tag,
                source: source,
                ocrEngineId: ocrEngineId,
                ocrConfidence: ocrConfidence,
                ocrRawText: ocrRawText,
                adjustedByUser: adjustedByUser,
                photoPath: photoPath,
                note: note,
                createdAt: createdAt,
                updatedAt: updatedAt,
                deletedAt: deletedAt,
                syncState: syncState,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$GlucoseReadingRowsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $GlucoseReadingRowsTable,
      GlucoseReadingRow,
      $$GlucoseReadingRowsTableFilterComposer,
      $$GlucoseReadingRowsTableOrderingComposer,
      $$GlucoseReadingRowsTableAnnotationComposer,
      $$GlucoseReadingRowsTableCreateCompanionBuilder,
      $$GlucoseReadingRowsTableUpdateCompanionBuilder,
      (
        GlucoseReadingRow,
        BaseReferences<
          _$AppDatabase,
          $GlucoseReadingRowsTable,
          GlucoseReadingRow
        >,
      ),
      GlucoseReadingRow,
      PrefetchHooks Function()
    >;
typedef $$SyncOutboxRowsTableCreateCompanionBuilder =
    SyncOutboxRowsCompanion Function({
      Value<int> seq,
      required String entity,
      required String entityId,
      required String op,
      required DateTime createdAt,
      Value<int> attempts,
      Value<String?> lastError,
    });
typedef $$SyncOutboxRowsTableUpdateCompanionBuilder =
    SyncOutboxRowsCompanion Function({
      Value<int> seq,
      Value<String> entity,
      Value<String> entityId,
      Value<String> op,
      Value<DateTime> createdAt,
      Value<int> attempts,
      Value<String?> lastError,
    });

class $$SyncOutboxRowsTableFilterComposer
    extends Composer<_$AppDatabase, $SyncOutboxRowsTable> {
  $$SyncOutboxRowsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get seq => $composableBuilder(
    column: $table.seq,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get entity => $composableBuilder(
    column: $table.entity,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get entityId => $composableBuilder(
    column: $table.entityId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get op => $composableBuilder(
    column: $table.op,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get attempts => $composableBuilder(
    column: $table.attempts,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get lastError => $composableBuilder(
    column: $table.lastError,
    builder: (column) => ColumnFilters(column),
  );
}

class $$SyncOutboxRowsTableOrderingComposer
    extends Composer<_$AppDatabase, $SyncOutboxRowsTable> {
  $$SyncOutboxRowsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get seq => $composableBuilder(
    column: $table.seq,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get entity => $composableBuilder(
    column: $table.entity,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get entityId => $composableBuilder(
    column: $table.entityId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get op => $composableBuilder(
    column: $table.op,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get attempts => $composableBuilder(
    column: $table.attempts,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get lastError => $composableBuilder(
    column: $table.lastError,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$SyncOutboxRowsTableAnnotationComposer
    extends Composer<_$AppDatabase, $SyncOutboxRowsTable> {
  $$SyncOutboxRowsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get seq =>
      $composableBuilder(column: $table.seq, builder: (column) => column);

  GeneratedColumn<String> get entity =>
      $composableBuilder(column: $table.entity, builder: (column) => column);

  GeneratedColumn<String> get entityId =>
      $composableBuilder(column: $table.entityId, builder: (column) => column);

  GeneratedColumn<String> get op =>
      $composableBuilder(column: $table.op, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<int> get attempts =>
      $composableBuilder(column: $table.attempts, builder: (column) => column);

  GeneratedColumn<String> get lastError =>
      $composableBuilder(column: $table.lastError, builder: (column) => column);
}

class $$SyncOutboxRowsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $SyncOutboxRowsTable,
          SyncOutboxRow,
          $$SyncOutboxRowsTableFilterComposer,
          $$SyncOutboxRowsTableOrderingComposer,
          $$SyncOutboxRowsTableAnnotationComposer,
          $$SyncOutboxRowsTableCreateCompanionBuilder,
          $$SyncOutboxRowsTableUpdateCompanionBuilder,
          (
            SyncOutboxRow,
            BaseReferences<_$AppDatabase, $SyncOutboxRowsTable, SyncOutboxRow>,
          ),
          SyncOutboxRow,
          PrefetchHooks Function()
        > {
  $$SyncOutboxRowsTableTableManager(
    _$AppDatabase db,
    $SyncOutboxRowsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SyncOutboxRowsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SyncOutboxRowsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$SyncOutboxRowsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> seq = const Value.absent(),
                Value<String> entity = const Value.absent(),
                Value<String> entityId = const Value.absent(),
                Value<String> op = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<int> attempts = const Value.absent(),
                Value<String?> lastError = const Value.absent(),
              }) => SyncOutboxRowsCompanion(
                seq: seq,
                entity: entity,
                entityId: entityId,
                op: op,
                createdAt: createdAt,
                attempts: attempts,
                lastError: lastError,
              ),
          createCompanionCallback:
              ({
                Value<int> seq = const Value.absent(),
                required String entity,
                required String entityId,
                required String op,
                required DateTime createdAt,
                Value<int> attempts = const Value.absent(),
                Value<String?> lastError = const Value.absent(),
              }) => SyncOutboxRowsCompanion.insert(
                seq: seq,
                entity: entity,
                entityId: entityId,
                op: op,
                createdAt: createdAt,
                attempts: attempts,
                lastError: lastError,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$SyncOutboxRowsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $SyncOutboxRowsTable,
      SyncOutboxRow,
      $$SyncOutboxRowsTableFilterComposer,
      $$SyncOutboxRowsTableOrderingComposer,
      $$SyncOutboxRowsTableAnnotationComposer,
      $$SyncOutboxRowsTableCreateCompanionBuilder,
      $$SyncOutboxRowsTableUpdateCompanionBuilder,
      (
        SyncOutboxRow,
        BaseReferences<_$AppDatabase, $SyncOutboxRowsTable, SyncOutboxRow>,
      ),
      SyncOutboxRow,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$GlucoseReadingRowsTableTableManager get glucoseReadingRows =>
      $$GlucoseReadingRowsTableTableManager(_db, _db.glucoseReadingRows);
  $$SyncOutboxRowsTableTableManager get syncOutboxRows =>
      $$SyncOutboxRowsTableTableManager(_db, _db.syncOutboxRows);
}
