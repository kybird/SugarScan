---
status: active
version_context: "sugarScan assets_dev/train webtool · lib/features/scan"
tags: [geometry, concept]
aliases: [좌표계, frame, 표시 좌표계, cross-space-comparison]
created: 2026-09-02
confidence: 5
---
# Coordinate Frame

좌표 4개짜리 배열은 **그 자체로는 아무 의미가 없다.** `(559, 345)` 는 "어느 이미지의, 어느 크기·방향 공간에서" 잰 값인지가 붙어야 비로소 위치를 가리킨다. 이 프로젝트가 지금까지 잃은 라벨은 전부 좌표가 틀려서가 아니라 **프레임이 틀려서** 잃었다.

## First Principles

한 프레임 안에서 이미지와 박스를 **같은 변환으로** 그리면 "화면에서 본 것 == 저장한 값"은 수학적으로 항상 참이다. dpr·줌·팬 오프셋은 이 등식을 깨지 못한다 — 전부 변환에 함께 들어가기 때문이다.

따라서 그린 것과 저장한 것이 다르다면 원인은 **하나뿐**이다: 그릴 때 쓴 프레임이 저장 대상의 프레임이 아니었다. 다른 가설(dpr, 스냅 누적, 브라우저 배율)을 세우기 전에 이것부터 배제해야 한다.

## Details

이 저장소의 프레임 정본은 **표시(EXIF 적용) 이미지의 원본 픽셀**이다. 라벨러·검수·캐시·복구 스크립트가 전부 이 관례를 공유한다.

프레임이 어긋나는 방식은 두 가지뿐이고, **처방이 정반대**다.

| 어긋남 | 증상 | 되돌리는 법 |
|---|---|---|
| **크기가 다른 프레임** (직전 장 크기가 잔존) | 원점 기준 균일 축소/확대 | 배율 곱 `(이 장 크기 ÷ 그때 프레임 크기)` |
| **방향이 다른 프레임** (EXIF 미적용) | 세로 점유율 ~0.52, 가로 1.0 초과 | 회전 사상 `x_d=(Hs-1)-y_s, y_d=x_s` (ori=6) |

**배율로는 회전을 절대 못 맞춘다.** 경계 안에 들어왔다고 맞은 것이 아니다 — 반드시 크롭해 눈으로 본다.

## Related

- Patterns: [[frame-provenance-binding]], [[server-side-write-verification]], [[dry-run-before-repair]]
- Anti-Patterns: [[unnamed-coordinate-frame]], [[mixed-image-decode-conventions]], [[bounds-check-as-correctness-proof]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-1` — cv2/PIL EXIF 관례 차이, ori=6 이 83.5%
- `doc/raw/2026-09-02.md#case-3` — LCD 라벨 122장 중 39장 파손
- `doc/raw/2026-09-02.md#case-6` — 프레임 한 장 밀림 (`hash:d5366c5`)
- `doc/raw/2026-09-02.md#case-7` — EXIF 미적용 band 라벨 5건
- `docs/reports/20260902-labeler-coordinate-frame.md`
