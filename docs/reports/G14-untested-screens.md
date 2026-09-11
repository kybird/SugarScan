# G14 — 테스트 없는 화면 넷 채우기

- 브랜치: `glm/G14-untested-screens`
- 커밋: 이 보고서와 함께 하나
- 상태: 완료 — **화면 코드는 한 줄도 고치지 않았다.**

## 무엇을 했나

| 신규 테스트 | 고정한 것 |
|---|---|
| `test/features/settings_screen_test.dart` (3건) | 단위 변경 안내 스낵바 + 선택 이동 · 목표 범위 선택이 저장돼 라디오가 옮겨 감 · 서버 미설정 빌드에서 동기화·계정 영역 숨김 |
| `test/features/manual_entry_sheet_test.dart` (3건) | 범위 밖 값(999 mg/dL) 거절·안내 후 같은 자리 수정으로 저장 · 쉼표 소수점 `7,6` → 7.6 해석 · 고른 태그가 결과에 반영 |
| `test/features/confirm_sheet_test.dart` (4건) | 인식값 그대로 표시(137 + mg/dL) · 보정하면 `adjustedByUser` 선다 · **값을 고쳤어도 저장 버튼 없이는 결과가 나오지 않는다(취소 → null)** · 고치지 않고 저장하면 `adjustedByUser` 거짓 |
| `test/features/sync_status_banner_test.dart` (5건) | 막힘 띠(문구+다시 시도) · 대기/유휴는 아무것도 그리지 않음 · 로그아웃 띠에는 다시 시도 없음 · 서버 미설정은 **실제 공급자 사슬**로 숨김 확인 · "다시 시도"가 retrySyncProvider 호출(기록 콜백 1회) |

합계 15건. `flutter test` 전체 **402 통과**(이 브랜치 기준 387 + 15).

## 왜 그렇게 했나

- **설정 화면의 "단위 변경 시 경고"는 안내 스낵바(`settingsUnitChanged`)로
  읽었다.** 화면 소스에 경고 다이얼로그는 없다(실측). 단위 확인 게이트 자체는
  온보딩의 `UnitGate` 영역이라 여기 범위 밖이다.
- **배너의 "막힘이 대기·로그아웃보다 먼히"는 표현으로 검증했다** — 우선순위
  판정 자체는 `test/app/sync_status_test.dart` 가 이미 고정하므로(지시서 각주),
  여기서는 막힘 상태가 막힘 띠로(로그아웃 띠가 아니라) 나타나는지를 봤다.
  서버 미설정 숨김만 오버라이드 없이 실제 사슬(remoteBackendProvider 기본값
  RemoteDisabled → syncStatusProvider 조기 복귀)로 돌렸다.
- 수동 입력의 범위 밖 값은 `999` 를 썼다 — 검증기의 모양 검사가 1~3자리만
  허용해 `9999` 는 범위가 아니라 "숫자가 아니다"로 거절된다(프로브로 확인).
- §3.2 규칙 준수: 시트 저장 버튼 전 `ensureVisible`, `pumpAndSettle` 0건,
  트리 본문 안에서 내리고 `pump(100ms)`, Drift 는
  `AppDatabase(NativeDatabase.memory())` 오버라이드.
- 선택 상태 확인은 `RadioGroup.groupValue` — 타일의 groupValue 는 조상에서
  물려받는 값이라 화면이 넣지 않고, raw 타입 `find.byType(RadioListTile)` 는
  제네릭 인스턴스(`RadioListTile<GlucoseUnit>`)와 맞지 않아 쓸 수 없었다.

## 발견한 것 (화면 코드 수정 없음 — 지시서대로 보고만)

- 없다. 네 화면 모두 기대한 대로 동작해서 프로덕션 코드를 고친 것은 0줄이다.
  프로브 과정에서 알게 된 사실 하나: **수동 입력에서 네 자리 숫자는 범위 밖
  메시지가 아니라 "숫자를 입력하세요"로 거절된다**(모양 검사가 먼저다). 값이
  600 초과든 9999 든 물리적으로 불가능한 값이므로 안전에는 무관하나, 문구가
  사용자에게 덜 정확한 안내를 준다 — 고칠지는 사람이 정한다.

## 검증

```text
flutter analyze  → No issues found!
flutter test     → All tests passed! (402 tests)
```

## 건드리지 않고 남긴 것

- 위 모양 검사 문구 문제.
- 프로브용 임시 테스트(`_probe_test.dart`)는 삭제했다.

## 막힌 것

없음.
