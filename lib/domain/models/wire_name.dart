/// 저장·전송 이름(`wireName`)을 도메인 값으로 되살리지 못했을 때 던진다.
///
/// **기본값으로 조용히 떨어지지 않는 것이 이 예외의 존재 이유다.**
///
/// 앱이 출시되는 순간부터 여러 버전이 같은 서버를 공유한다. 새 버전이 새로운
/// enum 값을 쓰기 시작하면 구버전은 그 값을 모르는데, 그때 아는 값으로 바꿔
/// 저장하면 두 단계 뒤에 데이터가 죽는다.
///
/// 1. 구버전이 모르는 태그를 `random` 으로 바꿔 로컬에 저장한다
/// 2. 사용자가 그 기록의 **메모만** 고친다 → push 는 행 전체를 보낸다
/// 3. **서버의 태그가 `random` 으로 덮인다** — 원본은 복구할 수 없다
///
/// 그래서 모르면 그 행을 통째로 건너뛴다. 구버전에서 그 기록이 잠깐 보이지
/// 않는 것은 앱을 업데이트하면 낫지만, 덮어쓴 값은 업데이트해도 못 살린다.
/// 건너뛴 행은 동기화 엔진이 세어서 [SyncReport.malformed] 로 보고한다.
///
/// 예외: **동기화되지 않는 로컬 설정**은 기본값으로 떨어져도 된다
/// (`TargetRangePreset`). 서버로 되돌아 나가지 않으므로 파괴 경로가 없고,
/// 사용자가 다시 고르면 그만이다.
class UnknownWireNameException implements Exception {
  const UnknownWireNameException(this.typeName, this.value);

  /// 되살리려던 타입 이름. 로그에서 어느 열이 문제인지 바로 보이게 한다.
  final String typeName;

  /// 서버가 보낸 원문.
  final String value;

  @override
  String toString() => '알 수 없는 $typeName wireName: "$value" — '
      '이 버전이 모르는 값이다. 기본값으로 치환하지 않고 행을 건너뛴다.';
}
