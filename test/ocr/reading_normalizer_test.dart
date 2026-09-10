import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/services/glucose_validator.dart';
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

  group('혈당계 에러 표시', () {
    test('E-1 · ER · ERR-5 · ERROR2 를 값으로 만들지 않는다', () {
      // 에러 표시는 혈당 정보가 아니고 뜻이 제조사마다 다르다. E 가 떨어져
      // 나가 '1' 이 되는 순간 mmol/L 하한(0.6)을 통과하는 혈당값이 된다.
      const codes = [
        'E-1', 'E-2', 'E-3', 'E-4', 'E-5', 'E-6', 'E-7', 'E-8', 'E-9',
        'ER', 'ERR', 'ERR-5', 'ERROR2',
        'E1', 'err-5', 'error 2',
      ];
      for (final raw in codes) {
        expect(normalizer.normalize(raw), isA<UnreadableReading>(),
            reason: 'normalize("$raw") 가 에러 표시를 값으로 정리했다');
      }
    });

    test('mmol/L 로도 검증기를 통과하지 않는다', () {
      // mg/dL 하한(10)은 '1' 을 우연히 막는다. mmol/L 하한(0.6)은 못 막는다 —
      // 그래서 mg/dL 로만 테스트하면 이 구멍이 보이지 않는다.
      const validator = GlucoseValidator();
      for (final raw in ['E-1', 'E-5', 'ERR-5', 'ERROR2']) {
        final normalized = normalizer.normalize(raw);
        // 스캐너와 같은 흐름: 숫자로 나와야만 검증기에 도달할 수 있다.
        if (normalized is NormalizedNumber) {
          expect(validator.parse(normalized.text, GlucoseUnit.mmoll).isOk,
              isFalse,
              reason: 'normalize("$raw") → "${normalized.text}" 이 '
                  'mmol/L 검증을 통과했다');
        } else {
          expect(normalized, isA<UnreadableReading>(),
              reason: 'normalize("$raw") 가 예상 밖의 결과: $normalized');
        }
      }
      // 검증기만으로는 못 막는다 — mmol/L 에서 '1' 은 물리 범위 안이다.
      // 그래서 이 판정은 정규화 안에 있어야 한다.
      expect(validator.parse('1', GlucoseUnit.mmoll).isOk, isTrue);
    });

    test('숫자 뒤에 붙은 E 는 에러로 보지 않는다', () {
      expect(number('123E'), '123');
    });

    test('E 단독 · E- 는 읽을 수 없다', () {
      expect(normalizer.normalize('E'), isA<UnreadableReading>());
      expect(normalizer.normalize('E-'), isA<UnreadableReading>());
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
