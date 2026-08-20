import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

void main() {
  group('정확한 매칭', () {
    test('0~9 모두 자기 패턴으로 되돌아온다', () {
      for (final entry in kDigitPatterns.entries) {
        final match = SegmentPatternTable.match(entry.value);
        expect(match, isA<DigitGlyph>(), reason: '숫자 ${entry.key}');
        expect((match as DigitGlyph).digit, entry.key);
        expect(match.hammingDistance, 0);
      }
    });

    test('L 과 H 는 어떤 숫자와도 겹치지 않는다', () {
      // 이 성질이 LO/HI 판정의 근거다. 겹치면 표시 전체를 구분할 수 없다.
      for (final letter in kLetterPatterns.values) {
        expect(kDigitPatterns.values.contains(letter), isFalse);
      }
      expect(SegmentPatternTable.match(kLetterPatterns['L']!),
          isA<LetterGlyph>());
      expect(SegmentPatternTable.match(kLetterPatterns['H']!),
          isA<LetterGlyph>());
    });

    test('O 와 I 는 각각 0, 1 과 패턴이 같다', () {
      // 그래서 글자 하나만으로는 구분할 수 없고, 조립 단계에서 L/H 를 닻으로
      // 삼아야 한다.
      expect(kDigitPatterns[0], 0x7E);
      expect(kDigitPatterns[1], 0x30);
    });

    test('아무 세그먼트도 켜지지 않으면 공백', () {
      expect(SegmentPatternTable.match(0), isA<BlankGlyph>());
    });
  });

  group('근사 매칭', () {
    test('세그먼트 하나가 날아가도 복구한다', () {
      // 8(1111111)에서 F 가 반사로 꺼진 경우 → 9(1111011)와 정확히 같아진다.
      // 이건 복구가 아니라 진짜 모호함이므로 아래 별도 케이스로 다룬다.
      // 여기서는 어떤 숫자와도 겹치지 않는 손상을 쓴다: 0에서 A 가 꺼짐.
      final damaged = kDigitPatterns[0]! & ~Seg.a; // 0111110
      final match = SegmentPatternTable.match(damaged);

      expect(match, isA<DigitGlyph>());
      expect((match as DigitGlyph).digit, 0);
      expect(match.hammingDistance, 1);
    });

    test('거리가 2 이상이면 판독을 포기한다', () {
      // 가운데 획 하나만 켜진 상태는 어떤 글자도 아니다.
      // 억지로 가장 비슷한 숫자를 돌려주지 않는다.
      final match = SegmentPatternTable.match(Seg.g);

      expect(match, isA<UnknownGlyph>());
      expect((match as UnknownGlyph).reason, UnknownReason.tooFar);
    });

    test('두 획이 손상되면 다른 글자로 정확히 떨어지는 경우가 많다', () {
      // 이것이 허용 거리를 1 로 묶어 두는 이유다. 거리 2 까지 받아들이면
      // "복구"가 아니라 조용한 오독이 된다.
      expect(kDigitPatterns[8]! & ~Seg.a & ~Seg.d, kLetterPatterns['H']);
      expect(kDigitPatterns[8]! & ~Seg.b & ~Seg.e, kDigitPatterns[5]);

      // 8 에서 A·D 가 날아가면 H 로 정확히 일치해 버린다.
      final match = SegmentPatternTable.match(
        kDigitPatterns[8]! & ~Seg.a & ~Seg.d,
      );
      expect(match, isA<LetterGlyph>());
    });

    test('최소 거리 후보가 동점이면 판독을 포기한다', () {
      // 1(0110000)에 G 만 켜진 상태(0110001)는 4(0110011)와 7(1110000) 등
      // 여러 후보에서 같은 거리가 나올 수 있다. 동점이면 고르지 않는다.
      var ambiguousFound = false;
      for (var bits = 1; bits < 128; bits++) {
        final match = SegmentPatternTable.match(bits);
        if (match is UnknownGlyph && match.reason == UnknownReason.ambiguous) {
          ambiguousFound = true;
          break;
        }
      }
      expect(ambiguousFound, isTrue,
          reason: '동점 케이스가 하나도 없다면 판정 로직을 다시 봐야 한다');
    });

    test('허용 거리를 0 으로 좁히면 정확 일치만 받는다', () {
      final damaged = kDigitPatterns[0]! & ~Seg.a;
      expect(SegmentPatternTable.match(damaged, maxDistance: 0),
          isA<UnknownGlyph>());
    });
  });

  test('모든 비트열에 대해 예외 없이 판정한다', () {
    // 128가지 상태 전부가 네 가지 결과 중 하나로 떨어져야 한다.
    for (var bits = 0; bits < 128; bits++) {
      final match = SegmentPatternTable.match(bits);
      expect(
        match,
        anyOf(
          isA<DigitGlyph>(),
          isA<LetterGlyph>(),
          isA<BlankGlyph>(),
          isA<UnknownGlyph>(),
        ),
        reason: 'bits=$bits',
      );
    }
  });

  test('비트 위치가 문서와 일치한다 (A 가 최상위)', () {
    // 순서가 어긋나면 2 와 5 처럼 좌우 대칭인 숫자가 조용히 뒤바뀐다.
    expect(Seg.a, 1 << 6);
    expect(Seg.g, 1 << 0);
    expect(Seg.ordered.length, Seg.count);
    expect(kDigitPatterns[1], Seg.b | Seg.c);
    expect(kDigitPatterns[7], Seg.a | Seg.b | Seg.c);
  });
}
