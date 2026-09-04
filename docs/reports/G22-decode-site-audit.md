# G22 — 이미지 디코드 자리 전수 감사

- 브랜치: `glm/G22-decode-audit`
- 상태: 완료 · **코드 변경 0줄 (어긋남 0건 — 다섯 번째 파일은 없었다)**
- 작성: 2026-09-04

## 무엇을 했나

- `assets_dev/`·`tools/` 전체에서 이미지를 여는 자리를 두 단계 grep 으로 찾았다
  (지시서 파탄 + 확장 패턴 `matplotlib/tf.image/imdecode/read_file/decode_png/
  decode_jpeg/load_img` — 확장 쪽은 추가 경로 0건).
- **자리마다 코드를 직접 읽어 판정했다** — "무처리일 것이다"를 추측으로 적지
  않았다(G20 지시서가 저지른 실수, `doc/raw/2026-09-02.md` Case 13).
- 좌표를 물리지 않는 자리는 EXIF 유무를 **실측**했다(표본 수치 아래 표).
- `_diag/`(세션 진단 스크립트, gitignored)와 `_legacy/`(2026-09-04 사용 중지
  격리)는 운영 소비자가 없어 본표에서 제외하고 맨 아래 한 줄로 둔다.

## 감사 표 — 운영 디코드 자리 15곳

| # | 파일:줄 | 디코더 | EXIF 처리(실측/코드 확인) | 물리는 좌표의 좌표계 | 판정 |
|---|---|---|---|---|---|
| 1 | `build_cache_v2.py:96` | PIL | `exif_transpose` 적용(G20) — 검증: 표본 10장 전부 정립, 회전 0 | GM 쿼드 = 표시 | 일치 |
| 2 | `build_cache_v2.py:40` | cv2.imread(PNG) | 합성 PNG **전체간격 표본 100/100 orientation=1** → 적용할 EXIF 자체가 없음 | 합성 라벨(키↔값 인덱스) | 무관 |
| 3 | `detect_datumo_gm.py:33` | PIL 단일 로더 | `exif_transpose` 적용(G20) — 검증: 재실행 2,007/2,512 동일·오버레이 7/9 유리 | 출력 자체가 표시 좌표계 | 일치 |
| 4 | `eval_reader.py:63` | PIL | `exif_transpose` 적용(`b015830`) — 실측: 유무로 완전일치 14.7%↔90.7%(n=300) | GM 쿼드 = 표시 | 일치 |
| 5 | `build_gmft_dataset.py:72` | PIL | `exif_transpose` 적용 — 검증: ft2 학습으로 회수 박스 유리 부착 8/8 | screen_boxes = 표시 | 일치 |
| 6 | `webtool.py:266` `_oriented_size` | PIL 헤더만 | orientation 5~8 **수동 스왑**으로 표시 크기 계산 | 라벨 ow/oh = 표시 | 일치 |
| 7 | `webtool.py:294/302` `/api/image` | PIL | `exif_transpose` + **헤더 계산과 어긋나면 에러 반환**(이중 방어) | 캔버스 ow/oh = 표시 | 일치 |
| 8 | `webtool.py:324` `_load_gray` | PIL | `exif_transpose` 적용(펼치기 검수용, 주석 명시) | 라벨 박스 = 표시 | 일치 |
| 9 | `webtool.py:730` 캐시 무결성 점검 | PIL | webtool 자체 생성 캐시 JPEG(EXIF 없음)의 종횡비를 `_oriented_size`(표시)와 대조 | 표시 | 일치 |
| 10 | `audit_oob.py:22` | PIL 헤더만 | orientation 5~8 **수동 스왑**으로 표시 치수 | screen_boxes = 표시 | 일치 |
| 11 | `repair_prevframe_labels.py:34` | PIL 헤더만 | 수동 스왑(`oriented_size`) — 일회성 복구 도구(이미 적용 완료) | 라벨 = 표시 | 일치 |
| 12 | `repair_unrotated_band_labels.py:34` | PIL 헤더만 | orientation 반환 + 명시 회전 사상(`unrotate`, ori=6 등) — 회전 좌표→표시 변환 전용 도구 | 변환 자체가 목적 | 일치 |
| 13 | `golden_bench.dart:245` | `package:image` decodeImage | **디코드 시점에 orientation 을 픽셀에 굽고 태그 제거**(G20 실측 ori 5~8 표본 242/242, 예외 0) — `bakeOrientation` 추가는 no-op 이므로 하지 않음 | GM 쿼드 = 표시 | 일치 |
| 14 | `scene_bench.dart:88` | decodeImage | 합성 PNG(EXIF 없음) | 합성 라벨 | 무관 |
| 15 | `cell_bench.dart:95` | decodeImage | 셀 jpg **클래스별 간격 표본 110/110 orientation=1** | 좌표 없음(셀 이미지를 엔진에 직접 투입) | 무관 |

부록 — 브라우저 캔버스(`webtool.html`): `new Image()` 로 받는 JPEG 은
전부 #7(`/api/image`, 표시 좌표계로 구워 서빙) 또는 #9 캐시에서 오므로 별도
디코드 자리가 아니다.

## 검증

- 코드 변경 0줄이므로 `flutter analyze`·`flutter test` 재실행 대상 없음
  (main HEAD `f3dc4fa` 기준 무경고·통과 상태 그대로).
- EXIF 실측 수치(이 보고서의 새 측정):
  - 합성 PNG: 전체 간격 표본 100/100 orientation=1
  - 셀 데이터셋 jpg: 클래스별(11개) 간격 표본 110/110 orientation=1
- 어긋남이 0건이므로 "고친 뒤 숫자"를 붙일 자리도 0건이다.

## 건드리지 않고 남긴 것

- `_diag/` 진단 스크립트 15여 개: 대부분 `exif_transpose` 명시 사용(작성 시부터),
  나머지는 자체 생성 PNG 열기 — 운영 소비자가 없어 수정하지 않았다.
- `lib/`(앱 사진 경로): 지시서 금지. 참고로 앱의 `photo_preprocessor.dart` 는
  `package:image` 를 써서 방향이 이미 굽혀져 들어온다(G20 실측) — 앱쪽도
  현재 관례상 문제 없음.
- 셀/합성 데이터셋에 orientation 태그가 아예 없다는 실측(#2·#15)은 "지금은
  무관"이라는 뜻이지 "앞으로도 영원히 무관"은 아니다 — 외부 데이터를 새로
  들일 때마다 이 표의 해당 칸을 다시 잰다는 조건이다.

## 막힌 것

- 없음.
