# G11 — 남은 미지역화 문자열 감사

- 브랜치: `glm/G11-untranslated-audit`
- 커밋: 이 보고서 + 작업 목록 이관 커밋 하나
- 상태: 완료 — **지역화 대상 0건. 코드·ARB 변경 0줄.**

## 무엇을 했나

지시서의 grep 전량(`Text('`·`Text("`·`label:`/`hintText:`/`helperText:`/`tooltip:`
/`semanticLabel:`·`SnackBar(`)에 한국어 문자열 리터럴 전수
(`'[가-힣]'`)과 영문 하드코딩 후보를 더해 `lib/` 를 훑었다
(`lib/l10n/generated/` 제외). 후보 전부의 소비 경로를 읽어 분류했다.

## 감사 표

| 파일:줄 | 문자열 | 사용자에게 보이는가 | 판정 |
|---|---|---|---|
| `features/scan/photo_import_sheet.dart:159` | `'..'` | 예 — 사진 가져오기 파일 브라우저의 상위 폴더 행 | **대상 아님** — 파일시스템 관례 기호 |
| `features/scan/photo_align_screen.dart:509-510` | `'9:16'`·`'3:4'` | 디버그 빌드에서만 | **대상 아님** — 종횡비 기호·디버그 전용 |
| `features/scan/photo_align_screen.dart:204,209,452-533,556-582` | 타이틀 "사진 정렬 테스트 (디버그)"·툴팁 12개("원래대로"…"확대")·상태 배지("판독","대기" 등) | **아니오** — 진입이 `scan_screen.dart:484` 의 `if (kDebugMode)` 블록 뒤에만 있다. 출시 빌드에서는 이 화면에 도달할 수 없다 | **대상 아님** — 디버그 전용 화면 |
| `features/scan/scan_screen.dart:503` | 툴팁 "가이드 정렬 테스트 (디버그)" | **아니오** — 같은 `kDebugMode` 블록 안 | **대상 아님** — 디버그 전용 |
| `features/scan/confirm_sheet.dart:93,118` | `'-${unit.format(_step)}'`·`'+…'` | 예 — 단계 조절 버튼 툴팁 | **대상 아님** — 숫자·단위 기호 |
| `data/remote/reading_dto.dart:64,87` | `FormatException('숫자가 아니다…')`·`'(id 불명)'` | 아니오 — pull 로그·건너뛴 행 식별 | 대상 아님 — 진단 |
| `data/remote/remote_backend.dart:57,73`·`data/sync/reading_api.dart:131`·`features/dashboard/dashboard_screen.dart:117`·`features/history/history_screen.dart:26` | debugPrint 한국어 | 아니오 — 로그 | 대상 아님 — 디버그 로그 |
| `data/remote/supabase_config.dart:50-51`·`domain/models/wire_name.dart:30-31`·`ocr/src/engine/ocr_engine_registry.dart:40-58` | 설정 오용·wireName·등록 오류 예외문 | 아니오 — 개발자 오류 | 대상 아님 — 진단 |
| `ocr/src/engines/segment_rule/frame_quality.dart:38`·`segment_rule_engine.dart:92,104,132`·`sevenseg_cnn/seven_seg_cnn_engine.dart:87,97,109,120` | "초점이 흐립니다", "프레임을 디코딩하지 못했습니다" 등 | **아니오 — 실측으로 확인.** `OcrFailure.reason` 을 `lib/features/`·`lib/app/` 어디에서도 읽지 않는다(grep 0건). `scan_screen._statusText` 는 결과를 l10n 키(`meterShowsHigh` 등)로만 매핑한다 | 대상 아님 — UI 미도달 |
| `domain/models/target_range_preset.dart:21-40` | `'70–180'` 등 | 예 — 스낵바 안 | **대상 아님** — 로케일 중립 숫자 범위 |

그 외 `label:`/`hintText:`/`SnackBar(` 전부 `l10n.*` 호출이었다.

## 왜 이렇게 판정했나 (판단이 갈렸던 두 지점)

- **photo_align_screen 전체**: 한국어 문자열이 가장 많은 화면이지만 진입
  경로가 디버그 게이트(`kDebugMode`, scan_screen:484)뒤에만 있다. "디버그
  로그는 지역화 대상이 아니다"(지시서)와 같은 기준을 적용했다. 출시 빌드
  사용자에게는 존재하지 않는 화면이다.
- **OCR 엔진 실패 문구**: 모듈 경계(`lib/ocr` 은 Flutter 의존 0)상 l10n 을
  import 할 수 없어 구조적으로 지역화 불가능하다. 다만 실측 결과 UI 에
  도달하지도 않으므로 지금은 문제가 아니다. **언젠가 `failure.reason` 을
  화면에 보이는 수정이 들어오면 그때 이 표를 다시 봐야 한다** — "UI 미도달"은
  현재 사실이지 영구 면책이 아니다.

## 검증

코드를 한 줄도 바꾸지 않았으므로 게이트는 확인만 한다.

```text
flutter analyze  → No issues found!
flutter test     → All tests passed! (390 tests)
```

## 건드리지 않고 남긴 것

- OCR 엔진 실패 문구의 한국어 하드코딩 자체(위 판단 근거 참조).
- `flutter gen-l10n` 재생성 불필요(ARB 무변경).

## 막힌 것

없음.
