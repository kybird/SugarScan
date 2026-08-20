import 'segment_patterns.dart';

/// 셀 하나의 해석 결과.
class CellReading {
  const CellReading({
    required this.glyph,
    required this.decimalPoint,
    required this.margin,
  });

  final GlyphMatch glyph;
  final bool decimalPoint;

  /// 0~1. 이 셀의 판정이 경계에서 얼마나 떨어져 있었는지.
  final double margin;
}

sealed class AssembledReading {
  const AssembledReading();
}

final class ReadingText extends AssembledReading {
  const ReadingText(this.text, this.confidence);

  /// `102.5`, `98`, `LO`, `HI`.
  final String text;
  final double confidence;

  @override
  String toString() => 'ReadingText("$text", ${confidence.toStringAsFixed(2)})';
}

final class ReadingUnreadable extends AssembledReading {
  const ReadingUnreadable(this.problem);
  final ReadingProblem problem;

  @override
  String toString() => 'ReadingUnreadable(${problem.name})';
}

enum ReadingProblem {
  /// 켜진 자리가 하나도 없다.
  blank,

  /// 어떤 자리를 판독하지 못했다.
  unknownGlyph,

  /// 자릿수는 읽었지만 수로 성립하지 않는다(소수점이 두 개, 끝에 소수점 등).
  malformed,
}

/// 셀별 판독을 표시 문자열로 조립한다.
///
/// 자릿수 판독과 조립을 분리하는 이유: `98`, `102.5`, `5.6`, `LO` 처럼 길이와
/// 형태가 제각각인 표시를 한 곳에서 다루기 위해서다. 셀 디코더는 "이 자리가
/// 무엇인가"만 답하고, 전체가 수로 성립하는지는 여기서 판정한다.
abstract final class DisplayAssembler {
  /// 해밍 거리 1 로 근사 매칭된 자리에 매기는 신뢰도 감점.
  static const double approximateMatchPenalty = 0.75;

  static AssembledReading assemble(List<CellReading> cells) {
    if (cells.isEmpty) return const ReadingUnreadable(ReadingProblem.blank);

    // ── 1. LO / HI 우선 판정 ────────────────────────────────────────────
    // L 과 H 는 어떤 숫자 패턴과도 겹치지 않는다. 따라서 이 글자가 하나라도
    // 보이면 표시 전체가 범위 초과 알림이다. 뒤따르는 O·I 는 각각 0·1 과
    // 패턴이 같아 스스로는 구분되지 않으므로, 이 닻이 없으면 `LO` 가 `10`
    // 으로 읽힌다.
    for (final cell in cells) {
      final glyph = cell.glyph;
      if (glyph is LetterGlyph) {
        return ReadingText(
          glyph.letter == 'L' ? 'LO' : 'HI',
          _confidence(cells.where((c) => c.glyph is! BlankGlyph)),
        );
      }
    }

    // ── 2. 숫자 조립 ───────────────────────────────────────────────────
    final buffer = StringBuffer();
    final used = <CellReading>[];
    var seenDigit = false;
    var decimalCount = 0;

    for (final cell in cells) {
      switch (cell.glyph) {
        case BlankGlyph():
          // 혈당계는 값을 오른쪽 정렬해 표시하므로 공백은 앞자리에만 나온다.
          // 숫자가 시작된 뒤의 공백은 표시의 끝으로 본다.
          if (seenDigit) {
            return _finish(buffer.toString(), used, decimalCount);
          }
          continue;

        case UnknownGlyph():
          // 한 자리라도 못 읽으면 전체를 버린다. 부분 판독은 `102` 를 `12` 로
          // 만들 수 있고, 그건 값을 틀리게 읽는 것보다 나을 게 없다.
          return const ReadingUnreadable(ReadingProblem.unknownGlyph);

        case LetterGlyph():
          return const ReadingUnreadable(ReadingProblem.malformed);

        case DigitGlyph(:final digit):
          seenDigit = true;
          used.add(cell);
          buffer.write(digit);
          if (cell.decimalPoint) {
            buffer.write('.');
            decimalCount++;
          }
      }
    }

    return _finish(buffer.toString(), used, decimalCount);
  }

  static AssembledReading _finish(
    String text,
    List<CellReading> used,
    int decimalCount,
  ) {
    if (text.isEmpty) return const ReadingUnreadable(ReadingProblem.blank);
    if (decimalCount > 1 || text.endsWith('.')) {
      return const ReadingUnreadable(ReadingProblem.malformed);
    }
    return ReadingText(text, _confidence(used));
  }

  static double _confidence(Iterable<CellReading> cells) {
    var confidence = 1.0;
    var any = false;

    for (final cell in cells) {
      any = true;
      var cellConfidence = cell.margin;
      final glyph = cell.glyph;
      final distance = switch (glyph) {
        DigitGlyph(:final hammingDistance) => hammingDistance,
        LetterGlyph(:final hammingDistance) => hammingDistance,
        _ => 0,
      };
      if (distance > 0) cellConfidence *= approximateMatchPenalty;

      // 전체 신뢰도는 가장 약한 자리를 따른다.
      if (cellConfidence < confidence) confidence = cellConfidence;
    }

    return any ? confidence : 0.0;
  }
}
