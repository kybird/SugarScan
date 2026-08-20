import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/ocr/testing.dart';

void main() {
  StabilizerOutcome feed(ReadingStabilizer s, List<(String, double)> frames) {
    late StabilizerOutcome outcome;
    for (final (value, confidence) in frames) {
      outcome = s.add(StabilizerObservation(value, confidence));
    }
    return outcome;
  }

  test('같은 값이 연속 3회 + 확신도 충족 → 확정', () {
    final s = ReadingStabilizer();
    final outcome = feed(s, [('138', 0.9), ('138', 0.92), ('138', 0.88)]);

    expect(outcome, isA<StabilizerConfirmed>());
    final confirmed = outcome as StabilizerConfirmed;
    expect(confirmed.value, '138');
    expect(confirmed.averageConfidence, closeTo(0.90, 0.001));
  });

  test('연속 횟수가 모자라면 확정하지 않는다', () {
    final s = ReadingStabilizer();
    final outcome = feed(s, [('138', 0.99), ('138', 0.99)]);

    expect(outcome, isA<StabilizerPending>());
    expect((outcome as StabilizerPending).consecutiveCount, 2);
  });

  test('단일 프레임 오인식은 확정을 막는다 — 이 컴포넌트의 존재 이유', () {
    final s = ReadingStabilizer();
    final outcome = feed(s, [('138', 0.95), ('198', 0.93), ('138', 0.95)]);

    expect(outcome, isA<StabilizerPending>());
    expect((outcome as StabilizerPending).consecutiveCount, 1);
  });

  test('연속이어도 확신도가 낮으면 확정하지 않는다', () {
    final s = ReadingStabilizer();
    final outcome = feed(s, [('138', 0.5), ('138', 0.55), ('138', 0.6)]);

    expect(outcome, isA<StabilizerPending>());
  });

  test('오인식 후 안정되면 확정된다', () {
    final s = ReadingStabilizer();
    final outcome = feed(s, [
      ('198', 0.7),
      ('138', 0.9),
      ('138', 0.91),
      ('138', 0.93),
    ]);

    expect(outcome, isA<StabilizerConfirmed>());
    expect((outcome as StabilizerConfirmed).value, '138');
  });

  test('윈도우 크기를 넘어서면 오래된 관측을 버린다', () {
    final s = ReadingStabilizer(windowSize: 4);
    feed(s, [('1', 0.9), ('2', 0.9), ('3', 0.9), ('4', 0.9), ('5', 0.9)]);
    expect(s.observationCount, 4);
  });

  test('reset 후에는 다시 처음부터 센다', () {
    final s = ReadingStabilizer();
    feed(s, [('138', 0.9), ('138', 0.9)]);
    s.reset();
    expect(s.observationCount, 0);

    final outcome = s.add(const StabilizerObservation('138', 0.99));
    expect(outcome, isA<StabilizerPending>());
  });

  test('임계값을 조정할 수 있다', () {
    final s = ReadingStabilizer(requiredConsecutive: 2, minAverageConfidence: 0.5);
    final outcome = feed(s, [('7.6', 0.6), ('7.6', 0.6)]);
    expect(outcome, isA<StabilizerConfirmed>());
  });
}
