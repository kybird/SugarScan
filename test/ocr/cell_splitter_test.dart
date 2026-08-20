import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

void main() {
  test('나누어떨어지면 균등하게 자른다', () {
    final cells = splitIntoCells(300, 3);

    expect(cells, hasLength(3));
    expect(cells.map((c) => c.left), [0, 100, 200]);
    expect(cells.map((c) => c.width), [100, 100, 100]);
  });

  test('나머지 픽셀은 앞쪽 셀부터 1픽셀씩 나눠 갖는다', () {
    // 마지막 셀에 몰아주면 그 자리만 계속 넓어져 인식이 치우친다.
    final cells = splitIntoCells(302, 3);

    expect(cells.map((c) => c.width), [101, 101, 100]);
    expect(cells.last.right, 302);
  });

  test('셀은 빈틈 없이 이어지고 ROI 를 정확히 덮는다', () {
    for (final width in [97, 100, 101, 255, 640]) {
      for (final count in [1, 2, 3, 4]) {
        final cells = splitIntoCells(width, count);
        expect(cells.first.left, 0);
        expect(cells.last.right, width, reason: 'w=$width n=$count');
        for (var i = 1; i < cells.length; i++) {
          expect(cells[i].left, cells[i - 1].right);
        }
      }
    }
  });

  test('자릿수가 폭보다 많으면 자르지 않는다', () {
    expect(splitIntoCells(2, 3), isEmpty);
  });

  test('잘못된 입력은 빈 목록', () {
    expect(splitIntoCells(0, 3), isEmpty);
    expect(splitIntoCells(300, 0), isEmpty);
    expect(splitIntoCells(-1, 3), isEmpty);
  });
}
