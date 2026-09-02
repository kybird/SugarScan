---
status: active
version_context: "sugarScan assets_dev/train/webtool.{py,html}"
tags: [tooling, pattern]
aliases: [빌드 지문, stale-tab-detection, /api/build]
created: 2026-09-02
confidence: 5
---
# Build Fingerprint

돌고 있는 클라이언트가 **어느 빌드인지** 화면에서 읽히게 한다.

## The Rule

- 서버가 소스 파일의 해시를 노출한다(`/api/build` → `{sha, mtime, bytes}`).
- 클라이언트는 부팅 시 자기 지문을 기억하고 주기적으로 서버와 대조한다.
- 다르면 **눈에 띄게** 알린다: `build a1b2c3d4 → 서버 e5f6a7b8 · Ctrl+Shift+R 필요`.

## Why it works

"고쳤는데 왜 그대로냐"의 절반은 **고친 코드가 돌지 않고 있었던 것**이다. 이 상태는 로그·스크린샷·증상 어디에도 흔적을 남기지 않아서, 없으면 아무도 배제하지 못한다. 2026-09-02 사고에서 수정 3분 뒤에 저장된 파손 라벨이 정확히 이 경우였고, 그 애매함 때문에 **원인 진단 전체가 dpr 가설로 잘못 수렴했다.**

## Trade-offs

- 서버가 파일을 해시한다(수십 KB, 무시 가능).
- `Cache-Control: no-store` 를 이미 보내고 있어도 **필요하다** — 새로고침이 실제로 일어났는지는 별개 사실이다.

## Anti-Pattern

[[stale-client-writes]]

## Related

- Patterns: [[server-side-write-verification]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-6` (`hash:474da30`)
- `assets_dev/train/webtool.py` `_build_stamp()` / `webtool.html` `checkBuild()`
