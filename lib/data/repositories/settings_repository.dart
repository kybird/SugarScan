import '../../domain/models/glucose_unit.dart';
import '../local/database.dart';

/// 표시 단위 설정의 상태.
///
/// "아직 확인 안 됨"과 "사용자가 골랐음"을 구분하는 것이 이 타입의 존재
/// 이유다. 둘을 뭉뚱그리면 로케일 추정값이 사용자가 고른 값인 척하게 된다.
class UnitPreference {
  const UnitPreference({required this.unit, required this.confirmedByUser});

  final GlucoseUnit unit;

  /// 사용자가 온보딩이나 설정에서 직접 확인했는지.
  final bool confirmedByUser;
}

/// 앱 설정 저장소.
///
/// 표시 단위가 왜 이렇게까지 조심스럽게 다뤄지는가:
/// 검증기 범위상 **10~50 사이의 정수는 두 단위 모두에서 통과한다.** 같은 숫자가
/// mg/dL 로는 중증 저혈당, mmol/L 로는 중증 고혈당(180~900 mg/dL 상당)이다.
/// 단위가 반대로 잡혀 있으면 그 구간의 기록이 임상적으로 정반대 의미로 저장되고,
/// 검증기도 안정화기도 이 오류는 잡지 못한다. 그래서 추정값을 확정으로 쓰지 않는다.
class SettingsRepository {
  SettingsRepository({required AppDatabase database}) : _db = database;

  static const String _unitKey = 'display_unit';
  static const String _unitConfirmedKey = 'display_unit_confirmed';

  /// 이 기기에서 한 번이라도 로그인에 성공했는지.
  ///
  /// 세션 유무와는 다른 질문이다. 세션은 리프레시 토큰이 만료·폐기되면 사라지는데,
  /// 그때 로그인 화면으로 다시 막아 버리면 **비행기 안에서 측정한 사람이 기록을
  /// 남길 방법이 없어진다.** 한 번 로그인한 기기는 세션이 끊겨도 로컬 모드로
  /// 계속 쓰게 하고, 동기화만 세션이 돌아올 때까지 미룬다.
  static const String _signedInBeforeKey = 'auth_signed_in_before';

  final AppDatabase _db;

  /// 저장된 단위 설정. 아직 고른 적이 없으면 null.
  Future<UnitPreference?> readUnitPreference() async {
    final unit = await _read(_unitKey);
    if (unit == null) return null;

    return UnitPreference(
      unit: GlucoseUnit.fromWireName(unit),
      confirmedByUser: await _read(_unitConfirmedKey) == 'true',
    );
  }

  Stream<UnitPreference?> watchUnitPreference() {
    final query = _db.select(_db.appSettingRows)
      ..where((t) => t.key.isIn([_unitKey, _unitConfirmedKey]));

    return query.watch().map((rows) {
      final map = {for (final row in rows) row.key: row.value};
      final unit = map[_unitKey];
      if (unit == null) return null;
      return UnitPreference(
        unit: GlucoseUnit.fromWireName(unit),
        confirmedByUser: map[_unitConfirmedKey] == 'true',
      );
    });
  }

  /// 사용자가 직접 고른 단위를 저장한다.
  ///
  /// 이미 저장된 기록은 건드리지 않는다. 정본이 mg/dL 이라 표시만 바뀌며,
  /// 각 기록은 입력 당시의 `enteredUnit` 을 그대로 간직한다.
  Future<void> confirmUnit(GlucoseUnit unit) async {
    await _write(_unitKey, unit.wireName);
    await _write(_unitConfirmedKey, 'true');
  }

  /// 이 기기에서 로그인에 성공한 적이 있는지.
  Stream<bool> watchSignedInBefore() {
    final query = _db.select(_db.appSettingRows)
      ..where((t) => t.key.equals(_signedInBeforeKey));
    return query
        .watch()
        .map((rows) => rows.isNotEmpty && rows.first.value == 'true');
  }

  Future<void> markSignedIn() => _write(_signedInBeforeKey, 'true');

  Future<String?> _read(String key) async {
    final row = await (_db.select(_db.appSettingRows)
          ..where((t) => t.key.equals(key)))
        .getSingleOrNull();
    return row?.value;
  }

  Future<void> _write(String key, String value) {
    return _db.into(_db.appSettingRows).insertOnConflictUpdate(
          AppSettingRowsCompanion.insert(key: key, value: value),
        );
  }
}
