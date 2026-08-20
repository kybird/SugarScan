import 'package:flutter_timezone/flutter_timezone.dart';

/// 기기의 IANA 타임존 이름(예: `Asia/Seoul`).
///
/// 실패하면 예외를 던지지 않고 `UTC` 로 떨어진다. 타임존을 못 읽는다고 해서
/// 사용자가 기록을 남기지 못하게 만들 이유는 없다. 오프셋은 별도로 저장되므로
/// 이름을 놓쳐도 시각 자체는 정확하다.
Future<String> systemTimeZoneName() async {
  try {
    final zone = await FlutterTimezone.getLocalTimezone();
    return zone.identifier;
  } on Object {
    return 'UTC';
  }
}
