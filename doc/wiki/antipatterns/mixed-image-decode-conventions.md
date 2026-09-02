---
status: active
version_context: "OpenCV 4.11 · Pillow 12.3 · Dart package:image"
tags: [geometry, anti-pattern]
aliases: [EXIF 관례 불일치, cv2 vs PIL, exif_transpose, cv2.imread, getexif, orientation, build_cache_v2, golden_bench]
created: 2026-09-02
confidence: 5
---
# 같은 좌표계를 공유하면서 디코더 관례를 통일하지 않는 것

`cv2.imread` 는 EXIF orientation 을 **자동 적용**하고, `PIL.Image.open` 은 **무시**한다. 같은 파일을 두 라이브러리로 읽는 코드가 같은 좌표계를 공유하면 그 순간 갈라진다.

## 실패 모드

Datumo 원본의 **83.5%(2,098/2,512)가 orientation=6** 이다. 그래서:

- 라벨러(cv2)는 올바른 세로 표시 → 사용자가 라벨링하기 좋았다
- 검수·캐시·검출(PIL)은 누운 원본 사용 → 검수 SRC 가 90° 돌아 보이고, 라벨 좌표(표시 공간)와 파이프라인 좌표(raw)가 불일치
- **CTC 학습 rect 다수가 "옆으로 누운 숫자 + 올바른 GT"** — 저성능의 숨은 주원인 후보

증상이 "검수창에서만 원본이 회전돼 보인다"로밖에 안 떠올라, 관례 차이를 의심하기까지 오래 걸린다.

## 점검 체크리스트

- [ ] 같은 이미지를 읽는 모든 경로가 **같은 EXIF 처리**를 하는가 (Python cv2 / Python PIL / Dart `package:image`)
- [ ] 좌표계 정본이 문서에 한 줄로 적혀 있는가 (여기서는 "표시(EXIF 적용) 이미지의 원본 픽셀")
- [ ] API 응답의 크기(ow/oh)가 그 정본 기준인가
- [ ] 디스크 캐시가 파이프라인 변경 뒤에도 유효한가 (종횡비 자가 점검)

## 미완 (2026-09-02 기준)

`build_cache_v2` · `detect_datumo_gm` · `golden_bench`(Dart `package:image`)는 여전히 EXIF 무처리. **GM 파인튜닝 병합 전 로더 통일 필수.**

## Grounding (References)

- `doc/raw/2026-09-02.md#case-1` (`hash:b2e10ab`) — `check_exif2.py` 분포 {6: 2098, 1: 412, 3: 2}
- `doc/raw/2026-09-02.md#case-7` — 이 시기에 저장된 band 라벨 5건
