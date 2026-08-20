/// 혈당계가 숫자 대신 띄우는 범위 초과 표시.
enum MeterRangeKind { high, low }

sealed class NormalizedReading {
  const NormalizedReading();
}

/// 숫자로 정리됐다. 아직 값의 타당성(범위·자릿수)은 판정하지 않았다.
final class NormalizedNumber extends NormalizedReading {
  const NormalizedNumber(this.text);
  final String text;

  @override
  String toString() => 'NormalizedNumber("$text")';
}

/// `HI` / `LO` 표시. 값이 아니라 상태다.
final class MeterRangeReading extends NormalizedReading {
  const MeterRangeReading(this.kind);
  final MeterRangeKind kind;

  @override
  String toString() => 'MeterRangeReading(${kind.name})';
}

/// 숫자를 뽑아낼 수 없었다.
final class UnreadableReading extends NormalizedReading {
  const UnreadableReading();

  @override
  String toString() => 'UnreadableReading()';
}

/// OCR 원문을 숫자 문자열로 보정한다.
///
/// **OCR 모듈 안에 있어야 하는 코드다.** 어떤 글자가 어떻게 잘못 읽히는지는
/// 7-세그먼트 LCD 와 인식 엔진의 특성이지 앱의 관심사가 아니다. 앱이 이걸
/// 알아야 한다면 엔진을 바꿀 때마다 앱도 같이 바뀐다.
class ReadingNormalizer {
  const ReadingNormalizer();

  /// 단위 표기. 긴 토큰을 먼저 매칭해야 `MMOL/L` 이 `MOL` 로 잘리지 않는다.
  static final RegExp _unitTokens =
      RegExp(r'MMOL\s*/?\s*L|MG\s*/?\s*DL|MMOL|MGDL|MG|DL');

  static final RegExp _high = RegExp(r'^(HI|HIGH|H1)$');
  static final RegExp _low = RegExp(r'^(LO|LOW)$');

  /// 7-세그먼트에서 흔한 글자 오인식.
  static const Map<String, String> _confusions = {
    'O': '0',
    'D': '0',
    'I': '1',
    'L': '1',
    'S': '5',
    'B': '8',
  };

  NormalizedReading normalize(String raw) {
    // ① 단위 표기를 먼저 떼어낸다.
    //    글자 교정보다 반드시 앞서야 한다. 순서를 바꾸면 `mg/dL` 의 D 와 L 이
    //    0 과 1 로 교정되어 `138 mg/dL` 이 `13801` 이 된다.
    final stripped = raw
        .trim()
        .toUpperCase()
        .replaceAll(',', '.')
        .replaceAll(_unitTokens, ' ')
        .trim();

    // ② 범위 초과 표시를 글자 교정 **전에** 판정한다.
    //    교정을 먼저 하면 `LO` 가 L→1, O→0 을 거쳐 `10` 이라는 정상 범위 값으로
    //    둔갑한다. 사용자가 실제로는 저혈당인데 앱에는 아무 일 없는 숫자가
    //    남는 최악의 오독이 된다.
    final compact = stripped.replaceAll(RegExp(r'\s'), '');
    if (_low.hasMatch(compact)) {
      return const MeterRangeReading(MeterRangeKind.low);
    }
    if (_high.hasMatch(compact)) {
      return const MeterRangeReading(MeterRangeKind.high);
    }

    // ③ 이제 글자를 숫자로 교정한다.
    var s = stripped;
    for (final entry in _confusions.entries) {
      s = s.replaceAll(entry.key, entry.value);
    }
    s = s.replaceAll(RegExp(r'[^0-9.]'), '');

    // 소수점이 여러 개면 첫 번째만 남긴다.
    final firstDot = s.indexOf('.');
    if (firstDot != -1) {
      s = '${s.substring(0, firstDot + 1)}'
          '${s.substring(firstDot + 1).replaceAll('.', '')}';
    }

    // 선행 0 제거. `093` 은 93 이다. 단 `0.x` 형태는 유지한다.
    s = s.replaceFirst(RegExp(r'^0+(?=\d)'), '');
    if (s.startsWith('.')) s = '0$s';
    if (s.endsWith('.')) s = s.substring(0, s.length - 1);

    if (s.isEmpty) return const UnreadableReading();
    return NormalizedNumber(s);
  }
}
