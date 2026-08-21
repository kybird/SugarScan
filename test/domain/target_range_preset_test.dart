import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/target_range_preset.dart';
import 'package:sugarscan/domain/services/glucose_statistics.dart';

void main() {
  group('지침 숫자', () {
    // 이 값들은 지침이 직접 발표한 쌍이다. 임의로 고치면 앱이 없는 근거를
    // 가진 범위를 보여 주게 된다.
    test('관찰 범위는 70–180 mg/dL / 3.9–10.0 mmol/L', () {
      const preset = TargetRangePreset.observation;

      expect(preset.lowMgdl, 70);
      expect(preset.highMgdl, 180);
      expect(preset.labelFor(GlucoseUnit.mgdl), '70–180');
      expect(preset.labelFor(GlucoseUnit.mmoll), '3.9–10.0');
    });

    test('식전 목표는 80–130 mg/dL / 4.4–7.2 mmol/L', () {
      const preset = TargetRangePreset.preMeal;

      expect(preset.lowMgdl, 80);
      expect(preset.highMgdl, 130);
      expect(preset.labelFor(GlucoseUnit.mgdl), '80–130');
      expect(preset.labelFor(GlucoseUnit.mmoll), '4.4–7.2');
    });

    test('좁은 범위는 70–140 mg/dL / 3.9–7.8 mmol/L', () {
      const preset = TargetRangePreset.tight;

      expect(preset.lowMgdl, 70);
      expect(preset.highMgdl, 140);
      expect(preset.labelFor(GlucoseUnit.mgdl), '70–140');
      expect(preset.labelFor(GlucoseUnit.mmoll), '3.9–7.8');
    });

    // 표시값을 손으로 박아 두었지만, 정본에서 변환한 결과와 어긋나면
    // 사용자가 화면의 숫자와 실제 판정이 다르다고 느낀다.
    test('표시값이 정본을 변환한 값과 일치한다', () {
      for (final preset in TargetRangePreset.values) {
        final low = GlucoseUnit.mmoll.format(
          GlucoseUnit.mmoll.fromMgdl(preset.lowMgdl),
        );
        final high = GlucoseUnit.mmoll.format(
          GlucoseUnit.mmoll.fromMgdl(preset.highMgdl),
        );

        expect(
          preset.mmollLabel,
          '$low–$high',
          reason: '${preset.wireName} 의 mmol/L 표기가 변환값과 다르다',
        );
      }
    });
  });

  group('저장', () {
    test('wireName 으로 되살린다', () {
      for (final preset in TargetRangePreset.values) {
        expect(TargetRangePreset.fromWireName(preset.wireName), preset);
      }
    });

    // Dart enum 이름이 아니라 wireName 이 정본이다. 식별자를 바꿔도 저장된
    // 설정이 깨지지 않아야 한다.
    test('식전 목표의 저장 이름은 pre_meal 이다', () {
      expect(TargetRangePreset.preMeal.wireName, 'pre_meal');
    });

    test('모르는 값은 기본값으로 떨어진다', () {
      expect(
        TargetRangePreset.fromWireName('없는_범위'),
        TargetRangePreset.fallback,
      );
    });

    // 기본값이 치료 목표면 앱이 그 목표를 권하는 것처럼 읽힌다.
    test('기본값은 치료 목표가 아니라 관찰 범위다', () {
      expect(TargetRangePreset.fallback, TargetRangePreset.observation);
    });
  });

  group('통계와의 연결', () {
    test('프리셋으로 만든 범위가 판정에 그대로 쓰인다', () {
      final tight = TargetRange.of(TargetRangePreset.tight);

      expect(tight.contains(140), isTrue, reason: '경계값은 범위 안이다');
      expect(tight.contains(141), isFalse);
      expect(tight.contains(70), isTrue);
      expect(tight.contains(69), isFalse);
    });

    // 같은 기록이 사용자 단위에 따라 다르게 판정되면 안 된다. 비교는 언제나
    // mg/dL 정본으로 한다.
    test('단위를 바꿔도 같은 값은 같게 판정된다', () {
      final range = TargetRange.of(TargetRangePreset.observation);
      const mgdl = 137.0;

      // mmol/L 로 표시하든 말든 판정에 쓰이는 값은 하나다.
      expect(range.contains(mgdl), isTrue);
      expect(
        range.contains(GlucoseUnit.mmoll.toMgdl(
          GlucoseUnit.mmoll.fromMgdl(mgdl),
        )),
        isTrue,
      );
    });
  });
}
