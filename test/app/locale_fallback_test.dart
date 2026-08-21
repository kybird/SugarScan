import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sugarscan/app/app.dart';
import 'package:sugarscan/l10n/generated/app_localizations.dart';

void main() {
  test('지원 언어는 그 언어로 잡는다', () {
    expect(
      resolveAppLocale(const Locale('de'), AppLocalizations.supportedLocales),
      const Locale('de'),
    );
    expect(
      resolveAppLocale(const Locale('ko'), AppLocalizations.supportedLocales),
      const Locale('ko'),
    );
  });

  test('국가 코드만 다르면 언어 코드로 맞춘다', () {
    // 앱의 pt 는 브라질 어투 번역이지만 로케일 자체는 언어 코드만 있다.
    expect(
      resolveAppLocale(
        const Locale('pt', 'BR'),
        AppLocalizations.supportedLocales,
      ),
      const Locale('pt'),
    );
    expect(
      resolveAppLocale(
        const Locale('en', 'US'),
        AppLocalizations.supportedLocales,
      ),
      const Locale('en'),
    );
  });

  // gen-l10n 이 supportedLocales 를 알파벳순으로 만들어 de 가 첫 항목이다.
  // 콜백이 없으면 기본 해석이 첫 항목으로 떨어져서 지원 밖 언어 기기이
  // 독일어를 보게 된다. 폴백은 영어여야 한다.
  test('지원하지 않는 언어는 영어로 떨어뜨린다', () {
    expect(
      resolveAppLocale(const Locale('ja'), AppLocalizations.supportedLocales),
      const Locale('en'),
    );
    expect(
      resolveAppLocale(
        const Locale('zh', 'CN'),
        AppLocalizations.supportedLocales,
      ),
      const Locale('en'),
    );
    expect(
      resolveAppLocale(null, AppLocalizations.supportedLocales),
      const Locale('en'),
    );
  });
}
