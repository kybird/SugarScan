import 'package:sugarscan/ocr/testing.dart';

/// 테스트용 7-세그먼트 표시 렌더러.
///
/// 판독기를 실제 사진 없이 끝까지 돌려보기 위한 것이다. 디코더와 같은 기하
/// 정의를 공유하되, **샘플 영역보다 넓은 실제 획**을 그린다. 두 좌표가 정확히
/// 같으면 테스트가 자기 자신을 검증하는 꼴이 되므로 획을 조금 크게 그려
/// 샘플 영역이 획 안쪽에 들어가도록 한다.
class SevenSegmentRenderer {
  const SevenSegmentRenderer({
    this.width = 480,
    this.height = 160,
    this.digitCount = 4,
    this.gapRatio = 0.03,
    this.backgroundLevel = 220,
    this.strokeLevel = 40,
  });

  final int width;
  final int height;
  final int digitCount;
  final double gapRatio;

  /// 반사형 LCD 를 가정한다: 밝은 배경 위의 어두운 획.
  final int backgroundLevel;
  final int strokeLevel;

  /// 획의 실제 모양. 셀 크기에 대한 비율(left, top, right, bottom).
  static const Map<int, List<double>> _strokes = {
    0: [0.22, 0.03, 0.78, 0.15], // A
    1: [0.77, 0.13, 0.91, 0.43], // B
    2: [0.77, 0.57, 0.91, 0.87], // C
    3: [0.22, 0.85, 0.78, 0.97], // D
    4: [0.09, 0.57, 0.23, 0.87], // E
    5: [0.09, 0.13, 0.23, 0.43], // F
    6: [0.22, 0.44, 0.78, 0.56], // G
  };

  static const List<double> _decimalStroke = [0.90, 0.88, 0.99, 0.98];

  /// `102.5`, `98`, `LO`, `HI` 같은 표시를 그린다. 값은 오른쪽 정렬한다.
  GrayImage render(String text) {
    final image = GrayImage.filled(width, height, backgroundLevel);
    final cells = _layout(text);

    final totalGap = gapRatio * (digitCount - 1);
    final cellWidth = (1.0 - totalGap) / digitCount;

    for (var i = 0; i < digitCount; i++) {
      final cell = cells[i];
      if (cell == null) continue;

      final left = i * (cellWidth + gapRatio) * width;
      final cellPixelWidth = cellWidth * width;

      final bits = _patternFor(cell.glyph);
      for (var s = 0; s < 7; s++) {
        if (bits & Seg.ordered[s] == 0) continue;
        _fill(image, _strokes[s]!, left, cellPixelWidth);
      }
      if (cell.decimalPoint) {
        _fill(image, _decimalStroke, left, cellPixelWidth);
      }
    }
    return image;
  }

  /// 표시 문자열을 셀 배열로 바꾼다. 짧으면 앞을 비운다(오른쪽 정렬).
  List<_RenderedCell?> _layout(String text) {
    final parsed = <_RenderedCell>[];
    for (final char in text.split('')) {
      if (char == '.') {
        if (parsed.isEmpty) continue;
        parsed[parsed.length - 1] =
            _RenderedCell(parsed.last.glyph, decimalPoint: true);
        continue;
      }
      parsed.add(_RenderedCell(char));
    }

    final cells = List<_RenderedCell?>.filled(digitCount, null);
    final offset = digitCount - parsed.length;
    for (var i = 0; i < parsed.length; i++) {
      final index = offset + i;
      if (index >= 0 && index < digitCount) cells[index] = parsed[i];
    }
    return cells;
  }

  int _patternFor(String glyph) {
    // O 와 I 는 각각 0, 1 과 같은 획을 쓴다. 실제 혈당계도 그렇다.
    return switch (glyph) {
      'L' => kLetterPatterns['L']!,
      'H' => kLetterPatterns['H']!,
      'O' => kDigitPatterns[0]!,
      'I' => kDigitPatterns[1]!,
      _ => kDigitPatterns[int.parse(glyph)]!,
    };
  }

  void _fill(
    GrayImage image,
    List<double> box,
    double cellLeft,
    double cellWidth,
  ) {
    final x0 = (cellLeft + box[0] * cellWidth).round().clamp(0, image.width);
    final y0 = (box[1] * image.height).round().clamp(0, image.height);
    final x1 = (cellLeft + box[2] * cellWidth).round().clamp(0, image.width);
    final y1 = (box[3] * image.height).round().clamp(0, image.height);

    for (var y = y0; y < y1; y++) {
      for (var x = x0; x < x1; x++) {
        image.set(x, y, strokeLevel);
      }
    }
  }
}

class _RenderedCell {
  const _RenderedCell(this.glyph, {this.decimalPoint = false});
  final String glyph;
  final bool decimalPoint;
}

/// 초점이 나간 프레임을 흉내 낸다. 박스 블러를 반복 적용한다.
GrayImage blur(GrayImage source, {int radius = 4, int passes = 3}) {
  var current = source;
  for (var pass = 0; pass < passes; pass++) {
    final out = GrayImage.filled(current.width, current.height);
    for (var y = 0; y < current.height; y++) {
      for (var x = 0; x < current.width; x++) {
        var sum = 0;
        var count = 0;
        for (var dy = -radius; dy <= radius; dy++) {
          for (var dx = -radius; dx <= radius; dx++) {
            final nx = x + dx;
            final ny = y + dy;
            if (nx < 0 || ny < 0 || nx >= current.width || ny >= current.height) {
              continue;
            }
            sum += current.at(nx, ny);
            count++;
          }
        }
        out.set(x, y, (sum / count).round());
      }
    }
    current = out;
  }
  return current;
}
