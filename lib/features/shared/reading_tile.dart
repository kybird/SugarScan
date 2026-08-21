import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../domain/models/glucose_reading.dart';
import '../../domain/models/glucose_unit.dart';
import '../../l10n/generated/app_localizations.dart';
import 'tag_labels.dart';

/// 기록 한 줄.
///
/// 값에 "정상/위험" 같은 색이나 문구를 붙이지 않는다. 그건 판정이고, 이 앱은
/// 판정하지 않는다(일반 건강관리 도구 분류를 지키는 선). 시간·태그·출처처럼
/// 서술적인 정보만 보여 준다.
class ReadingTile extends StatelessWidget {
  const ReadingTile({
    super.key,
    required this.reading,
    required this.unit,
    this.onTap,
  });

  final GlucoseReading reading;
  final GlucoseUnit unit;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final locale = Localizations.localeOf(context).toString();

    // 측정 시점의 벽시계 시각으로 보여 준다. UTC 로 표시하면 여행 중 기록이
    // 엉뚱한 시간에 찍힌 것처럼 보인다.
    final local = reading.measuredAtLocalWallClock;
    final timeText = DateFormat.yMMMd(locale).add_jm().format(local);

    // 스크린리더에게 타일 전체를 한 문장으로 읽어 준다. 값만 낭독되면 단위가
    // 생략되는데, 혈당에서 단위는 숫자의 뜻을 바꾼다. 라벨은 보이는 내용과
    // 같게만 — 여기에 판정을 덧붙이지 않는다. 라벨 문구는 전부 이미 l10n 을
    // 거친 조각(값·기호·시각·태그·출처)으로 짜맞춘다.
    final semanticsLabel =
        '${reading.formatted(unit)} ${unit.symbol}, $timeText, '
        '${reading.tag.label(l10n)}, ${reading.source.label(l10n)}';

    return Semantics(
      label: semanticsLabel,
      child: ListTile(
        onTap: onTap,
        // 값과 단위는 라벨이 대신 읽어 주므로 개별 낭독에서 뺀다.
        title: Semantics(
          excludeSemantics: true,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                reading.formatted(unit),
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w600,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
              const SizedBox(width: 6),
              Text(
                unit.symbol,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        subtitle: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 시각·태그·출처도 라벨이 커버한다. 메모는 라벨 문자열에 직접
            // 넣지 않지만 의미론 노드가 같아서 이어서 읽힌다 — 보이는 내용과
            // 낭독 내용이 같아진다.
            Semantics(
              excludeSemantics: true,
              child: Text(
                '$timeText · ${reading.tag.label(l10n)} · ${reading.source.label(l10n)}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
            // 메모는 서술 정보다. 아이콘도 색도 붙이지 않고 부제와 같은 몸으로
            // 한 줄만 보여 준다. 없으면 아예 그리지 않는다 — 빈 줄이 생기면
            // 메모 없는 기록의 높이가 달라진다.
            if (reading.note != null && reading.note!.trim().isNotEmpty)
              Text(
                reading.note!,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
