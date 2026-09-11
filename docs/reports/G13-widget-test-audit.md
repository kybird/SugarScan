# G13 — 위젯 테스트 함정 전수 감사

- 브랜치: `glm/G13-widget-test-audit`
- 커밋: 이 보고서 + 작업 목록 이관 커밋 하나
- 상태: 완료 — **무의미한 테스트 0건. 코드 변경 0줄.**

## 무엇을 했나

`test/features/`·`test/app/` 의 위젯 테스트 전부에서 네 신호를 찾고, 의심
항목은 **일부러 반대로 바꿔 돌린 뒤 복원**하는 방식으로 검증했다(붕괴 실행분은
커밋에 남기지 않았다 — `git checkout` 복원 완료).

1. `ensureVisible`/`scrollUntilVisible` 없이 하는 `tap` — 13곳
2. "없음"을 단정하는 `findsNothing` — 11곳
3. `pumpAndSettle` — **0곳** (쓰지 말라는 주석 4곳만)
4. 인자 없는 `pump()` — 16곳

## 감사 표

| 테스트 파일 | tap | findsNothing | 무인자 pump | 판정 |
|---|---|---|---|---|
| `dashboard_screen_test` | 0 | 1 (`boom` — 예외 원문 미노출) | 1 (첫 프레임 + 300ms×2 관용구) | **검증됨** |
| `edit_reading_sheet_test` | 2 — `open`(시트 열기)·저장 버튼(**`ensureVisible` 선행 — W12 수정분 그대로**) | 0 | 6 (전부 프레임 펌프 + `save()` 헬퍼의 시간 진행) | **검증됨** |
| `history_screen_test` | 1 (`Undo` 스낵바 액션) | 3 (`137`·`SqliteException`·`No readings yet`) | 1 (관용구) | **검증됨** |
| `stats_screen_test` | 1 (`30 days` 세그먼트) | 3 (`Average`·`Bedtime`·`137`) | 0 | **검증됨** |
| `scan_photo_import_test` | 9 (`open`·항목 선택·`Load photo`·새로고침 — 시트 내부 위젯) | 1 (사진용 안내문구) | 6 (프레임 펌프 후 시간 진행) | **검증됨** |
| `reading_tile_test` | 0 | 0 | 0 | 대상 신호 없음 |
| `scan_lcd_band_detector_test` | 0 | 0 | 0 | 대상 신호 없음 |
| `app/app_smoke_test` | 0 | 3 (`NavigationBar`·`FloatingActionButton`·진행 표시) | 2 (관용구) | **검증됨** |

(위젯 테스트가 아닌 순수 Dart 테스트 — `camera_frame_converter`·
`scan_photo_preprocessor`·`scan_photo_perspective_warp` — 은 이 감사의 대상이
아니어서 표에서 뺐다. 뷰포트가 없으면 이 함정들이 성립하지 않는다.)

## 검증 방법과 결과

- **tap 13곳**: 전 위젯 테스트 실행 출력에서 화면 밖 탭 경고(off-screen hit
  test)를 검색 — **0건**. 모든 탭이 실제 보이는 위젯에 랜딩한다. 저장 버튼
  스크롤이 필요한 자리(편집 시트)는 이미 `ensureVisible` 이 붙어 있다.
- **findsNothing 11곳**: 전부 `findsWidgets` 로 뒤집어 실행 — **11/11 실패**
  ("Found 0 widgets"). 즉 어느 것도 뷰포트 밖이라 비어 보인 것이 아니라
  트리에 실제로 없는 것을 단정하고 있다. 뒤집기 실행 후 전부 복원했다.

  ```text
  stats    Average / Bedtime / 137        → Found 0 widgets (3/3 실패)
  history  137 / SqliteException / No readings yet → Found 0 widgets (2 테스트 실패, 3 단정 모두 진짜)
  smoke    NavigationBar / FloatingActionButton / CircularProgressIndicator → Found 0 widgets
  photo    사진용 안내문구                 → Found 0 widgets
  dash     boom                            → Found 0 widgets
  ```

- **무인자 pump 16곳**: 전부 같은 관용구다 — `pump()` 로 한 프레임을 세운 뒤
  `pump(Duration(...))` 로 시계를 넘긴다. "무인자 pump 만으로 DB 파생 상태를
  단정하는" 함정 사례는 0곳이었다.
- **pumpAndSettle**: 사용 0곳.

## 결론

세 번째 함정 사례는 없다 — 무의미한 테스트를 고칠 대상이 발견되지 않았다.
W12·W11 에서 이미 잡힌 패턴(저장 버튼 `ensureVisible`, 태그 목록)이 현재도
지켜지고 있고, 그 외의 탭·부재 단정은 전부 살아 있다.

## 검증

```text
flutter analyze  → No issues found!
flutter test     → All tests passed! (387 tests — 이 브랜치 기준)
flutter test test/features/ → +58 All tests passed! (화면 밖 탭 경고 0건)
```

## 건드리지 않고 남긴 것

- 없음 — 고친 코드가 없다.

## 막힌 것

없음.
