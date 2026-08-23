# 스캔 화면 사진 불러오기 — 개발 전용 판독 경로 테스트 구멍

- 브랜치: `glm/scan-photo-import`
- 상태: 완료 (사용자 직접 지시 작업 — GLM_TASKS 항목 아님)

## 무엇을 했나

- `lib/features/scan/photo_import_sheet.dart` 신규 — 폴더 경로와 PNG 목록을
  보여 주고 파일을 고르면 `File` 을 돌려주는 바텀 시트. 기본 경로는 합성
  데이터 생성기 출력(`assets_dev/synth/images`).
- `lib/features/scan/scan_screen.dart` 수정
  - **debug 빌드에서만** 보이는 "사진 불러오기" 버튼(`kDebugMode`).
  - 고른 PNG 를 `OcrFrame(format: png, roi: null)` 로 만들어
    `GlucoseScanner.offer` 에 **3번** 넘긴다 — 프레임 합의(기본 3연속)를
    정적 사진으로 채워 카메라와 동일한 확정 조건을 지나게 한다.
    ROI 를 주지 않아 전체 프레임을 판독한다(가이드 박스는 카메라 전용).
  - 카메라가 없어 `_boot` 가 막힌 환경(Windows)에서도 사진 경로가 스스로
    `scanner.start()` 를 호출한다(`_ensureScannerStarted`).
  - 사진 모드(`_importedPhoto`)에서는 프리뷰에 사진을, 상태 텍스트에는
    판독 결과를 보여 준다.
- l10n 키 3개(`scanImportPhotoCta`·`scanImportPickTitle`·`scanImportNoImages`)
  를 6개 언어 ARB 전부에 추가.
- 위젯 테스트 3개(`test/features/scan_photo_import_test.dart`).

## 왜 그렇게 했나

- **새 패키지를 넣지 않았다.** 제품 수준의 갤러리 픽커는 보통
  `image_picker` 패키지가 필요한데 §2.7 이 금지한다. 대신 이미 공개된
  경로를 썼다 — `OcrFrame` 이 원래 `png`/`jpeg` 바이트를 받고
  `SegmentRuleEngine` 이 직접 디코드한다. 그래서 카메라 프레임과 **완전히
  같은 경로**(offer → 합의 → 확인 시트)를 돌며, lib/ 은 한 줄도 안 고쳤다.
  제품 기능으로 갤러리 불러오기를 원하면 그때 패키지 추가를 결정해야 한다.
- **debug 전용으로 제한했다.** 목적이 합성 데이터로 판독 경로를 눈으로
  확인하는 것이고, release 노출 여부는 제품 결정이기 때문이다.
- `ScanScreen` 에 스캐너 주입 파라미터를 추가했다 — 기존 화면들이 DB
  프로바이더를 주입해 테스트하는 것과 같은 구조다.

## 테스트하면서 밝혀진 것 (G13/G14 에 관련)

1. **확정 직후 햅틱 채널이 위젯 테스트에서 pending 에 걸린다.**
   `HapticFeedback.mediumImpact()` 를 mock 채널 없이 기다리면 확인 시트
   push 까지 도달하지 않는다. 테스트에서 `SystemChannels.platform` 을
   mock 했다.
2. **카메라 부트의 `timeout(6초)` 타이머가 테스트 끝에 남는다.**
   `availableCameras()` 가 테스트 환경에서 즉시 실패하지 않으면 6초
   타이머가 살아 있어 "Timer is still pending" 으로 죽는다. 트리를 내린
   뒤 `pump(7초)` 로 소화한다.
3. **확인 시트의 Cancel 탭이 위젯 테스트에서 시트를 닫지 않았다.**
   탭은 명중(warnIfMissed 없음)하는데 `pop` 이 일어나지 않는다. 실기기
   버그인지 테스트 환경 한정인지는 확인 못 했다. 확인 시트는 G14 가
   정식으로 다루므로 거기서 조사할 것. **이 테스트는 시트 등장까지만
   검증한다.**

## 검증

```
flutter analyze  → No issues found! (ran in 8.9s)
flutter test     → 00:08 +339: All tests passed! (기존 336 + 신규 3)
```

## 사용법 (Windows debug)

```bash
flutter run -d windows
```

스캔 화면 → "사진 불러오기" → 목록에서 장면 선택. 합성 데이터
(2000장)가 기본 폴더에 있다. 판독이 확정되면 확인 시트가 뜨고, 값이
나오지 않으면 상태 텍스트가 진행 상황을 보여 준다. 합성 이미지에 대한
정량 결과는 G17(장면 벤치)이 정식으로 잰다 — 이 기능은 눈 확인용이다.

## 막힌 것

- 없음
