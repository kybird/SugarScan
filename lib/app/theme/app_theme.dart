import 'package:flutter/material.dart';

/// 앱 테마.
///
/// 라이트/다크를 같은 시드에서 함께 정의한다. 스캔 화면은 카메라 프리뷰 위에
/// 얹히므로 테마와 무관하게 어두운 오버레이를 쓴다.
abstract final class AppTheme {
  /// 의료 앱의 관습적인 파랑을 피하고, 경고색(빨강/노랑)을 상태 표시에
  /// 온전히 남겨 두기 위해 청록 계열을 시드로 쓴다.
  static const Color seed = Color(0xFF0F766E);

  static ThemeData light() => _build(Brightness.light);
  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: seed,
      brightness: brightness,
    );
    return ThemeData(
      colorScheme: scheme,
      useMaterial3: true,
      // 독일어·스페인어에서 라벨이 20~40% 길어진다. 버튼 최소 높이를 고정하고
      // 가로 폭은 내용에 맡겨 줄바꿈이 가능하도록 둔다.
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(0, 48),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: scheme.surfaceContainerHighest,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
      ),
    );
  }
}
