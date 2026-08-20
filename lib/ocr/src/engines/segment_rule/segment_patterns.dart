/// 7-세그먼트 비트 순서: 최상위부터 `A B C D E F G`.
///
/// ```
///      ── A ──
///     │       │
///     F       B
///     │       │
///      ── G ──
///     │       │
///     E       C
///     │       │
///      ── D ──
/// ```
///
/// 이 순서는 모듈 전체에서 하나로 고정한다. 순서가 어긋나면 `2` 와 `5` 처럼
/// 좌우 대칭인 숫자가 조용히 뒤바뀐다.
abstract final class Seg {
  static const int a = 1 << 6;
  static const int b = 1 << 5;
  static const int c = 1 << 4;
  static const int d = 1 << 3;
  static const int e = 1 << 2;
  static const int f = 1 << 1;
  static const int g = 1 << 0;

  /// 샘플링 순서(A→G)와 비트 위치의 대응.
  static const List<int> ordered = [a, b, c, d, e, f, g];
  static const int count = 7;
}

/// 숫자 0~9 의 세그먼트 패턴.
const Map<int, int> kDigitPatterns = {
  0: 0x7E, // 1111110  ABCDEF
  1: 0x30, // 0110000  BC
  2: 0x6D, // 1101101  ABDEG
  3: 0x79, // 1111001  ABCDG
  4: 0x33, // 0110011  BCFG
  5: 0x5B, // 1011011  ACDFG
  6: 0x5F, // 1011111  ACDEFG
  7: 0x70, // 1110000  ABC
  8: 0x7F, // 1111111  전체
  9: 0x7B, // 1111011  ABCDFG
};

/// 혈당계가 범위 초과를 알릴 때 쓰는 글자.
///
/// `O` 와 `I` 는 각각 `0`, `1` 과 세그먼트 패턴이 완전히 같아서 글자 하나만
/// 보고는 구분할 수 없다. 반면 `L` 과 `H` 는 어떤 숫자와도 겹치지 않는다.
/// 그래서 이 둘을 닻으로 삼아 표시 전체를 `LO` / `HI` 로 판정한다(§표시 조립).
const Map<String, int> kLetterPatterns = {
  'L': 0x0E, // 0001110  DEF
  'H': 0x37, // 0110111  BCEFG
};

sealed class GlyphMatch {
  const GlyphMatch();
}

/// 켜진 세그먼트가 없다. 앞자리 공백.
final class BlankGlyph extends GlyphMatch {
  const BlankGlyph();
  @override
  String toString() => 'Blank';
}

final class DigitGlyph extends GlyphMatch {
  const DigitGlyph(this.digit, this.hammingDistance);
  final int digit;
  final int hammingDistance;
  @override
  String toString() => 'Digit($digit, d=$hammingDistance)';
}

/// `L` 또는 `H`.
final class LetterGlyph extends GlyphMatch {
  const LetterGlyph(this.letter, this.hammingDistance);
  final String letter;
  final int hammingDistance;
  @override
  String toString() => 'Letter($letter, d=$hammingDistance)';
}

/// 어떤 패턴에도 충분히 가깝지 않거나, 후보가 동점이라 고를 수 없다.
///
/// **억지로 숫자를 돌려주지 않는다.** 혈당값에서 "모르겠음"과 "틀린 숫자"는
/// 전혀 다른 무게를 가진다.
final class UnknownGlyph extends GlyphMatch {
  const UnknownGlyph(this.reason);
  final UnknownReason reason;
  @override
  String toString() => 'Unknown(${reason.name})';
}

enum UnknownReason {
  /// 가장 가까운 패턴도 허용 거리를 넘었다.
  tooFar,

  /// 최소 거리 후보가 둘 이상이다.
  ambiguous,
}

abstract final class SegmentPatternTable {
  /// 허용하는 최대 해밍 거리.
  ///
  /// 1 로 둔다. 2 까지 허용하면 `6`(1011111)과 `8`(1111111)처럼 한 획 차이인
  /// 숫자들 사이에서 오판이 급격히 늘어난다. 세그먼트 하나가 반사로 날아가는
  /// 정도는 1 로 흡수되고, 그 이상 망가진 프레임은 읽지 않는 편이 맞다.
  static const int maxHammingDistance = 1;

  /// 세그먼트 비트열을 글자로 해석한다.
  static GlyphMatch match(
    int bits, {
    int maxDistance = maxHammingDistance,
  }) {
    if (bits == 0) return const BlankGlyph();

    // 정확히 일치하면 곧바로 확정한다.
    for (final entry in kLetterPatterns.entries) {
      if (entry.value == bits) return LetterGlyph(entry.key, 0);
    }
    for (final entry in kDigitPatterns.entries) {
      if (entry.value == bits) return DigitGlyph(entry.key, 0);
    }

    // 근사 매칭. 최소 거리 후보가 유일할 때만 받아들인다.
    var bestDistance = Seg.count + 1;
    GlyphMatch? best;
    var tie = false;

    void consider(int pattern, GlyphMatch Function(int distance) build) {
      final distance = _hamming(bits, pattern);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = build(distance);
        tie = false;
      } else if (distance == bestDistance) {
        tie = true;
      }
    }

    for (final entry in kDigitPatterns.entries) {
      consider(entry.value, (d) => DigitGlyph(entry.key, d));
    }
    for (final entry in kLetterPatterns.entries) {
      consider(entry.value, (d) => LetterGlyph(entry.key, d));
    }

    if (bestDistance > maxDistance) {
      return const UnknownGlyph(UnknownReason.tooFar);
    }
    if (tie) return const UnknownGlyph(UnknownReason.ambiguous);
    return best!;
  }

  static int _hamming(int a, int b) {
    var x = a ^ b;
    var count = 0;
    while (x != 0) {
      count += x & 1;
      x >>= 1;
    }
    return count;
  }
}
