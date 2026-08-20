import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

void main() {
  const normalizer = ReadingNormalizer();

  String number(String raw) {
    final result = normalizer.normalize(raw);
    expect(result, isA<NormalizedNumber>(),
        reason: 'normalize("$raw") 가 숫자를 내지 않았다: $result');
    return (result as NormalizedNumber).text;
  }

  group('숫자 정리', () {
    test('그대로 숫자인 경우', () {
      expect(number('138'), '138');
      expect(number('7.6'), '7.6');
    });

    test('유럽식 쉼표 소수점', () {
      expect(number('7,6'), '7.6');
    });

    test('단위 표기를 떼어낸다', () {
      expect(number('138 mg/dL'), '138');
      expect(number('7.6 mmol/L'), '7.6');
      expect(number('138mgdl'), '138');
    });

    test('선행 0 을 제거한다', () {
      expect(number('093'), '93');
      expect(number('0093'), '93');
    });

    test('소수점으로 시작하거나 끝나는 형태를 정리한다', () {
      expect(number('.8'), '0.8');
      expect(number('7.'), '7');
    });

    test('소수점이 중복되면 첫 번째만 남긴다', () {
      expect(number('7.6.'), '7.6');
    });
  });

  group('7-세그먼트 글자 오인식 교정', () {
    test('I/L → 1, O/D → 0, S → 5, B → 8', () {
      expect(number('I38'), '138');
      expect(number('1O5'), '105');
      expect(number('S6'), '56');
      expect(number('B8'), '88');
    });

    test('단위 제거가 글자 교정보다 먼저 일어난다', () {
      // 순서가 뒤바뀌면 mg/dL 의 D 와 L 이 0 과 1 로 교정되어 13801 이 된다.
      expect(number('138 mg/dL'), '138');
    });
  });

  group('혈당계 범위 초과 표시', () {
    MeterRangeKind range(String raw) {
      final result = normalizer.normalize(raw);
      expect(result, isA<MeterRangeReading>(),
          reason: 'normalize("$raw") 가 범위 표시로 판정되지 않았다: $result');
      return (result as MeterRangeReading).kind;
    }

    test('LO 를 값 10 으로 오독하지 않는다', () {
      // L→1, O→0 교정이 그대로 적용되면 정상 범위 값이 되어버린다.
      // 사용자가 실제로는 저혈당인데 앱에는 아무 일 없는 숫자가 남는다.
      expect(range('LO'), MeterRangeKind.low);
      expect(range('Lo'), MeterRangeKind.low);
      expect(range('LOW'), MeterRangeKind.low);
    });

    test('HI 도 값으로 해석하지 않는다', () {
      expect(range('HI'), MeterRangeKind.high);
      expect(range('HIGH'), MeterRangeKind.high);
      // H 가 세그먼트 손실로 I 만 남는 변형.
      expect(range('H1'), MeterRangeKind.high);
    });
  });

  group('읽을 수 없음', () {
    test('빈 입력', () {
      expect(normalizer.normalize(''), isA<UnreadableReading>());
      expect(normalizer.normalize('   '), isA<UnreadableReading>());
    });

    test('단위만 있는 경우', () {
      expect(normalizer.normalize('mg/dL'), isA<UnreadableReading>());
    });
  });
}
