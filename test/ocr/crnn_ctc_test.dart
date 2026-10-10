import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

/// CTC greedy 디코드 — reader_crnn.decode_greedy 와 같은 알고리즘인지
/// 합성 logits 으로 검증한다(접힘·blank·확신도).
void main() {
  /// 기본 프레임: blank(10) 가 3.0, 숫자는 0. 원하는 프레임에 숫자 로짓을 얹는다.
  Float32List logits(Map<int, int> digits) {
    final out = Float32List(36 * 11);
    for (var t = 0; t < 36; t++) {
      out[t * 11 + 10] = 3.0;
    }
    digits.forEach((t, c) => out[t * 11 + c] = 5.0);
    return out;
  }

  test('숫자를 이어 붙인다', () {
    final reading = CrnnCtc.greedy(logits({5: 1, 12: 2, 20: 7}));
    expect(reading.text, '127');
    expect(reading.perCharConfidence, hasLength(3));
  });

  test('연속 중복은 접는다', () {
    // 5·6 프레임이 같은 1 — blank 없이 붙어 있으면 한 자리다.
    expect(CrnnCtc.greedy(logits({5: 1, 6: 1})).text, '1');
  });

  test('blank 를 사이에 둔 같은 숫자는 두 자리로 살린다', () {
    // '77' — CTC 에서 실제 연속은 blank 가 사이에 있어야 성립한다.
    expect(CrnnCtc.greedy(logits({5: 7, 7: 7})).text, '77');
  });

  test('모두 blank 면 빈 문자열', () {
    final reading = CrnnCtc.greedy(logits({}));
    expect(reading.text, '');
    expect(reading.confidence, 0);
  });

  test('확신도는 글자가 나온 프레임의 softmax 최대 확률이다', () {
    // 숫자 5.0 · blank 3.0 · 나머지 0 →
    // 1 / (1 + 9·e^(0−5) + e^(3−5)) = 1/1.195977 ≈ 0.83614
    final reading = CrnnCtc.greedy(logits({5: 4}));
    expect(reading.perCharConfidence[0], closeTo(0.83614, 1e-4));
    // 후보 확신도는 가장 약한 자리를 따른다.
    expect(reading.confidence, reading.perCharConfidence[0]);
  });
}
