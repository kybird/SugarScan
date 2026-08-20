import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

void main() {
  CellReading digit(int value, {bool dot = false, double margin = 1.0}) =>
      CellReading(
        glyph: DigitGlyph(value, 0),
        decimalPoint: dot,
        margin: margin,
      );

  CellReading letter(String value) => CellReading(
        glyph: LetterGlyph(value, 0),
        decimalPoint: false,
        margin: 1.0,
      );

  const blank = CellReading(
    glyph: BlankGlyph(),
    decimalPoint: false,
    margin: 1.0,
  );

  const unknown = CellReading(
    glyph: UnknownGlyph(UnknownReason.tooFar),
    decimalPoint: false,
    margin: 0.2,
  );

  String textOf(AssembledReading reading) => (reading as ReadingText).text;

  group('정수 표시', () {
    test('앞자리 공백을 건너뛴다', () {
      final reading = DisplayAssembler.assemble([blank, blank, digit(9), digit(8)]);
      expect(textOf(reading), '98');
    });

    test('세 자리', () {
      final reading =
          DisplayAssembler.assemble([blank, digit(1), digit(0), digit(2)]);
      expect(textOf(reading), '102');
    });

    test('숫자 뒤의 공백은 표시의 끝으로 본다', () {
      final reading =
          DisplayAssembler.assemble([digit(9), digit(8), blank, blank]);
      expect(textOf(reading), '98');
    });
  });

  group('소수점', () {
    test('102.5', () {
      final reading = DisplayAssembler.assemble(
        [digit(1), digit(0), digit(2, dot: true), digit(5)],
      );
      expect(textOf(reading), '102.5');
    });

    test('5.6', () {
      final reading = DisplayAssembler.assemble(
        [blank, blank, digit(5, dot: true), digit(6)],
      );
      expect(textOf(reading), '5.6');
    });

    test('소수점이 두 개면 수로 성립하지 않는다', () {
      final reading = DisplayAssembler.assemble(
        [digit(1, dot: true), digit(0), digit(2, dot: true), digit(5)],
      );
      expect(reading, isA<ReadingUnreadable>());
      expect((reading as ReadingUnreadable).problem, ReadingProblem.malformed);
    });

    test('마지막 자리에 소수점이 붙으면 거부한다', () {
      final reading =
          DisplayAssembler.assemble([blank, digit(9), digit(8, dot: true)]);
      expect((reading as ReadingUnreadable).problem, ReadingProblem.malformed);
    });
  });

  group('LO / HI', () {
    test('L 이 보이면 표시 전체가 LO 다', () {
      // O 는 0 과 패턴이 같아 스스로는 구분되지 않는다. L 이 닻이다.
      final reading = DisplayAssembler.assemble(
        [blank, blank, letter('L'), digit(0)],
      );
      expect(textOf(reading), 'LO');
    });

    test('H 가 보이면 HI 다', () {
      final reading = DisplayAssembler.assemble(
        [blank, blank, letter('H'), digit(1)],
      );
      expect(textOf(reading), 'HI');
    });

    test('L 이 없으면 같은 패턴이 숫자 10 으로 읽힌다', () {
      // 이것이 닻 없이는 LO 가 10 이 되어버리는 이유다.
      final reading = DisplayAssembler.assemble(
        [blank, blank, digit(1), digit(0)],
      );
      expect(textOf(reading), '10');
    });
  });

  group('판독 실패', () {
    test('한 자리라도 못 읽으면 전체를 버린다', () {
      // 부분 판독은 102 를 12 로 만든다. 값을 틀리게 읽는 것보다 나을 게 없다.
      final reading =
          DisplayAssembler.assemble([digit(1), unknown, digit(2)]);
      expect((reading as ReadingUnreadable).problem,
          ReadingProblem.unknownGlyph);
    });

    test('전부 공백이면 blank', () {
      final reading = DisplayAssembler.assemble([blank, blank, blank]);
      expect((reading as ReadingUnreadable).problem, ReadingProblem.blank);
    });

    test('셀이 없으면 blank', () {
      expect(DisplayAssembler.assemble([]), isA<ReadingUnreadable>());
    });
  });

  group('신뢰도', () {
    test('가장 약한 자리를 따른다', () {
      final reading = DisplayAssembler.assemble([
        digit(1, margin: 0.95),
        digit(0, margin: 0.40),
        digit(2, margin: 0.90),
      ]);
      expect((reading as ReadingText).confidence, closeTo(0.40, 0.001));
    });

    test('근사 매칭된 자리는 감점된다', () {
      final reading = DisplayAssembler.assemble([
        const CellReading(
          glyph: DigitGlyph(0, 1),
          decimalPoint: false,
          margin: 1.0,
        ),
        digit(8, margin: 1.0),
      ]);
      expect((reading as ReadingText).confidence,
          closeTo(DisplayAssembler.approximateMatchPenalty, 0.001));
    });
  });
}
