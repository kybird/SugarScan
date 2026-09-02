---
status: active
version_context: "sugarScan assets_dev/train/webtool"
tags: [tooling, anti-pattern]
aliases: [낡은 탭 쓰기, stale build]
created: 2026-09-02
confidence: 5
---
# 낡은 클라이언트의 쓰기를 그대로 받는 것

브라우저에 어느 버전의 JS 가 떠 있는지 **아무도 모르는 상태**로 저장 요청을 받는 것.

## 실패 모드

고친 코드가 실제로 돌고 있는지 확인할 방법이 없어, **"고쳤는데 그대로다"라는 잘못된 판단**이 나온다. 그 판단이 원인 진단을 통째로 다른 방향으로 끌고 간다.

2026-09-02: `webtool.html` 수정 01:18, 파손 라벨 기록 01:21. 서버는 `Cache-Control: no-store` 를 보내고 있었지만 **새로고침이 실제로 일어났는지는 별개 사실**이었다. 이 애매함 때문에 실제로는 해결된 원인을 미해결로 보고 dpr 가설을 추가로 쌓았다.

## 점검 체크리스트

- [ ] 서버가 소스 지문(해시)을 노출하는가
- [ ] 클라이언트가 자기 지문을 화면에 띄우고 서버와 주기적으로 대조하는가
- [ ] 다를 때 **눈에 띄게** 알리는가
- [ ] 서버가 요청의 유효성을 클라이언트 말이 아니라 **정본에서 직접** 확인하는가
- [ ] 도구 소스가 버전 관리에 있는가 (없으면 "언제 무엇이 바뀌었나"를 되짚을 수 없다)

## 올바른 대안

[[build-fingerprint]] + [[server-side-write-verification]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-6` (`hash:474da30`, `hash:d5366c5`)
