import 'wire_name.dart';

/// 기록이 어디서 들어왔는지.
///
/// [healthSync] 는 OS 건강 앱에서 읽어온 값이라 앱이 직접 만든 기록과
/// 중복될 수 있다. 중복 제거 로직이 이 값을 기준으로 동작한다.
enum ReadingSource {
  ocr('ocr'),
  manual('manual'),
  ble('ble'),
  healthSync('health_sync'),
  import('import');

  const ReadingSource(this.wireName);

  final String wireName;

  /// 모르는 값은 **기본값으로 치환하지 않고 던진다.** 이유는
  /// [UnknownWireNameException] — 치환한 값을 되돌려 쓰면 데이터가 죽는다.
  /// 여기서는 중복 제거 판정([healthSync])까지 흔들린다는 이유가 더 붙는다.
  static ReadingSource fromWireName(String value) =>
      values.firstWhere((e) => e.wireName == value,
          orElse: () => throw UnknownWireNameException('ReadingSource', value));
}
