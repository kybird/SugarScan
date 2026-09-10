import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// ARB 6개 파일의 정합성을 파일에서 직접 검사한다(G12).
///
/// 생성 코드(`lib/l10n/generated/`)를 읽으면 생성 전 상태를 못 잡는다 —
/// `flutter gen-l10n` 을 돌리지 않은 커밋도 이 테스트는 잡는다.
///
/// 네 검사:
/// 1. 6개 ARB 의 키 집합이 완전히 같다(어느 파일에 무엇이 빠졌는지 이름을 찍는다).
/// 2. 번역본에 키 메타데이터(`@key`)가 없다. `app_en.arb` 에만 있어야 한다.
///    `@@locale` 은 파일 규격의 로케일 선언이라 제외한다.
/// 3. 플레이스홀더가 파일 간에 일치한다. `{count}` 가 한 언어에서만 빠지면
///    `gen-l10n` 은 통과해도 런타임에 그 언어만 깨진다.
/// 4. `lib/` 어디에서도 참조되지 않는 키가 없다(게터 이름을 소스에서 찾는다).
void main() {
  final dir = Directory('lib/l10n');
  final files = dir
      .listSync()
      .whereType<File>()
      .where((f) => f.path.endsWith('.arb'))
      .toList()
    ..sort((a, b) => a.path.compareTo(b.path));

  final Map<String, Map<String, dynamic>> arbs = {
    for (final f in files)
      f.path.split(Platform.pathSeparator).last:
          jsonDecode(f.readAsStringSync()) as Map<String, dynamic>,
  };

  Set<String> keysOf(String file) =>
      arbs[file]!.keys.where((k) => !k.startsWith('@')).toSet();

  /// `{name}` 플레이스홀더 집합. 선택 플레이스홀더 문법은 이 앱이 안 쓴다.
  Set<String> placeholdersOf(String text) =>
      RegExp(r'\{([a-zA-Z][a-zA-Z0-9]*)\}')
          .allMatches(text)
          .map((m) => m.group(1)!)
          .toSet();

  /// ARB 키 → gen-l10n 게터 이름(snake_case → lowerCamelCase).
  /// 지금 키는 전부 camelCase 라 사실상 항등이지만, 키 추가 관례가 바뀌어도
  /// 이 테스트가 조용히 오탐을 내지 않게 한다.
  String getterOf(String key) {
    final parts = key.split('_');
    return parts.first + parts.skip(1).map((p) => p.capitalize).join();
  }

  test('ARB 파일이 정확히 6개(en·ko·es·pt·de·fr)다', () {
    expect(arbs.keys, [
      'app_de.arb',
      'app_en.arb',
      'app_es.arb',
      'app_fr.arb',
      'app_ko.arb',
      'app_pt.arb',
    ]);
  });

  test('6개 ARB 의 키 집합이 완전히 같다', () {
    final base = keysOf('app_en.arb');
    for (final file in arbs.keys) {
      final keys = keysOf(file);
      final missing = base.difference(keys).toList()..sort();
      final extra = keys.difference(base).toList()..sort();
      expect(
        missing,
        isEmpty,
        reason: '$file 에 없는 키: $missing',
      );
      expect(
        extra,
        isEmpty,
        reason: '$file 에만 있는 키: $extra',
      );
    }
  });

  test('번역본에 키 메타데이터(@key)가 없다 — @@locale 은 제외', () {
    for (final file in arbs.keys) {
      if (file == 'app_en.arb') continue;
      final meta = arbs[file]!.keys
          .where((k) => k.startsWith('@') && k != '@@locale')
          .toList()
        ..sort();
      expect(
        meta,
        isEmpty,
        reason: '$file 에 키 메타데이터가 있다: $meta — 원본 app_en.arb 에만 '
            '둔다(@@locale 은 파일 규격의 로케일 선언이라 예외)',
      );
    }
  });

  test('플레이스홀더가 파일 간에 일치한다', () {
    final base = 'app_en.arb';
    for (final key in keysOf(base)) {
      final expected = placeholdersOf('${arbs[base]![key]}');
      for (final file in arbs.keys) {
        final actual = placeholdersOf('${arbs[file]![key]}');
        expect(
          actual,
          equals(expected),
          reason: '$file 의 "$key" 플레이스홀더가 영문 원본과 다르다 — '
              '기대 $expected, 실제 $actual. gen-l10n 을 통과해도 그 언어에서만 '
              '런타임에 깨진다',
        );
      }
    }
  });

  test('lib/ 어디에서도 참조되지 않는 키가 없다', () {
    final sources = StringBuffer();
    for (final f in Directory('lib').listSync(recursive: true)) {
      if (f is! File || !f.path.endsWith('.dart')) continue;
      // 생성 코드는 게터를 정의만 하지 참조하지 않는다 — 세면 전부 미참조가 된다.
      if (f.path.contains('${Platform.pathSeparator}generated')) continue;
      sources.write(f.readAsStringSync());
    }
    final source = sources.toString();

    final unreferenced = [
      for (final key in keysOf('app_en.arb')..toList())
        if (!RegExp('\\b${getterOf(key)}\\b').hasMatch(source)) key,
    ]..sort();

    expect(
      unreferenced,
      isEmpty,
      reason: 'lib/ 에서 참조되지 않는 키: $unreferenced — 죽은 문구는 의료 문구 '
          '검토 대상만 늘린다. 지우기 어려운 사정이 있으면 이 테스트의 예외 '
          '목록에 키와 이유를 적어 둘 것',
    );
  });
}

extension on String {
  String get capitalize => length < 2
      ? this
      : '${this[0].toUpperCase()}${substring(1)}';
}
