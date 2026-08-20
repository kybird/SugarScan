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

  static ReadingSource fromWireName(String value) =>
      values.firstWhere((e) => e.wireName == value,
          orElse: () => ReadingSource.manual);
}
