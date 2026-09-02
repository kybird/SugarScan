import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/domain/models/glucose_unit.dart';
import 'package:sugarscan/domain/models/measurement_tag.dart';
import 'package:sugarscan/domain/models/reading_source.dart';
import 'package:sugarscan/domain/models/target_range_preset.dart';
import 'package:sugarscan/domain/models/wire_name.dart';

/// **동기화되는 기록 필드는 모르는 값을 기본값으로 치환하지 않는다.**
///
/// 치환하면 구버전 앱이 새 버전의 값을 아는 값으로 바꿔 저장했다가, 그 기록을
/// 수정하는 순간 push 가 치환된 값을 서버에 덮어써 원본을 파괴한다. 모르면 그
/// 행을 건너뛰는 쪽이 옳다 — 구버전에서 잠깐 안 보이는 것은 앱을 업데이트하면
/// 낫지만, 덮어쓴 값은 업데이트해도 못 살린다.
void main() {
  group('동기화되는 기록 필드 — 던진다', () {
    test('MeasurementTag 는 모르는 값에서 던진다', () {
      expect(
        () => MeasurementTag.fromWireName('post_snack'),
        throwsA(isA<UnknownWireNameException>()),
      );
    });

    test('ReadingSource 는 모르는 값에서 던진다', () {
      expect(
        () => ReadingSource.fromWireName('cgm_stream'),
        throwsA(isA<UnknownWireNameException>()),
      );
    });

    // 단위를 추측하면 값의 의미가 뒤집힌다 — 10~50 정수는 두 단위 모두 검증을
    // 통과해서 mg/dL 로는 중증 저혈당, mmol/L 로는 중증 고혈당이다.
    test('GlucoseUnit 은 모르는 값에서 던진다', () {
      expect(
        () => GlucoseUnit.fromWireName('mmol_per_liter'),
        throwsA(isA<UnknownWireNameException>()),
      );
    });

    test('아는 값은 그대로 되살아난다', () {
      for (final t in MeasurementTag.values) {
        expect(MeasurementTag.fromWireName(t.wireName), t);
      }
      for (final s in ReadingSource.values) {
        expect(ReadingSource.fromWireName(s.wireName), s);
      }
      for (final u in GlucoseUnit.values) {
        expect(GlucoseUnit.fromWireName(u.wireName), u);
      }
    });

    // 로그에서 어느 열이 문제인지 바로 보여야 한다. 예전 `Bad state: No element`
    // 로는 열도 값도 알 수 없었다.
    test('예외 문구에 타입과 원문이 들어간다', () {
      final e = const UnknownWireNameException('MeasurementTag', 'post_snack');
      expect(e.toString(), contains('MeasurementTag'));
      expect(e.toString(), contains('post_snack'));
    });
  });

  // 서버로 되돌아 나가지 않는 값은 파괴 경로가 없다. 사용자가 다시 고르면 된다.
  group('동기화되지 않는 로컬 설정 — 기본값으로 떨어진다', () {
    test('TargetRangePreset 은 기본값으로 떨어진다', () {
      expect(
        TargetRangePreset.fromWireName('없는_범위'),
        TargetRangePreset.fallback,
      );
    });
  });
}
