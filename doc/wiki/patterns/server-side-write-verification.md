---
status: active
version_context: "sugarScan assets_dev/train/webtool.py"
tags: [integrity, pattern]
aliases: [저장 검문, 쓰기 검증, 409 거부]
created: 2026-09-02
confidence: 5
---
# Server-Side Write Verification

클라이언트가 "무엇을 기준으로 만든 값인지"를 함께 보내게 하고, **서버가 정본에서 직접 재확인한 뒤에만** 기록한다.

## The Rule

1. 쓰기 요청에 **파생 맥락**을 실어 보낸다(이 경우 그릴 때 쓴 프레임 크기 `ow`/`oh`).
2. 서버가 원본 파일/DB 에서 같은 값을 직접 재서 대조한다.
3. 어긋나면 **409 로 거부하고, 거부 사유에 어긋난 배율까지 적는다.**
4. 성공한 행에는 그 맥락을 함께 저장한다 — 사후 전수 검증의 유일한 근거.

```python
if abs(cow - ow) > FRAME_TOL:
    return (f"좌표계 불일치 — 브라우저는 {cow:.0f}x{coh:.0f} 프레임으로 그렸는데 "
            f"실제 표시 크기는 {ow}x{oh} 다. 저장 거부(박스가 {ow/cow:.3f}배 어긋난다)")
```

## Why it works

**클라이언트는 자기가 틀렸는지 스스로 알 수 없다.** 낡은 JS 가 살아 있는 탭, 캐시된 번들, 사용자가 새로고침했다고 *믿는* 상태 — 전부 클라이언트 안에서는 정상으로 보인다. 서버만이 독립된 진실을 갖는다.

실측: 프레임 크기만 밀린 경우를 인위적으로 주입했을 때 클라이언트 검문은 통과시켰고 **서버만 잡았다.**

## Trade-offs

- 요청이 커지고 서버가 파일 헤더를 읽는다 → 메모이즈로 흡수(2,500장 전수 점검이 1초 이내).
- 거부가 늘면 작업 흐름이 끊긴다. 그래서 거부 문구가 **원인과 수치를 스스로 설명**해야 한다. "저장 실패"만 뜨면 사용자는 다시 추측을 시작한다.

## Anti-Pattern

[[stale-client-writes]]

## Related

- Concepts: [[coordinate-frame]]
- Patterns: [[frame-provenance-binding]], [[build-fingerprint]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-6` (`hash:d5366c5`) — `_verify_frame`, `/api/selftest`
- `docs/reports/20260902-labeler-coordinate-frame.md` §2 ④
