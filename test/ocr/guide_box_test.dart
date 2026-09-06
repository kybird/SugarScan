import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/ocr.dart';

void main() {
  group('가이드 박스', () {
    // 정규화 상수 하나로는 못 맞춘다는 것이 이 함수의 존재 이유다.
    // 센서가 달라도 **그려지는 모양**은 같아야 한다.
    test('센서 비가 달라도 실제 비는 같다', () {
      const target =
          NormalizedRect.digitCellAspect * NormalizedRect.guideDigitCount;
      for (final frameAspect in <double>[9 / 16, 3 / 4, 1 / 2]) {
        final box = NormalizedRect.guideBoxFor(frameAspect);
        final rendered = (box.width * frameAspect) / box.height;
        expect(rendered, closeTo(target, 1e-9),
            reason: 'frameAspect=$frameAspect');
      }
    });

    test('세로 중앙에 놓이고 폭은 화면의 80%', () {
      final box = NormalizedRect.guideBoxFor(9 / 16);
      expect(box.width, closeTo(0.80, 1e-9));
      expect(box.left, closeTo(0.10, 1e-9));
      expect(box.top + box.height / 2, closeTo(0.5, 1e-9));
    });

    // 자릿수는 엔진의 등폭 분할 개수와 같아야 한다. 갈리면 셀 하나가
    // 숫자 하나를 감싸지 못한다.
    test('자릿수는 엔진의 셀 분할 개수와 같다', () {
      expect(NormalizedRect.guideDigitCount, 3);
    });
  });
}
