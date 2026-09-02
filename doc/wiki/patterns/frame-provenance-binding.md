---
status: active
version_context: "sugarScan assets_dev/train/webtool.html"
tags: [geometry, pattern]
aliases: [프레임 이름표, frame-id-binding, 좌표계 귀속]
created: 2026-09-02
confidence: 5
---
# Frame Provenance Binding

좌표를 다루는 상태에는 **그 좌표계가 누구의 것인지**를 함께 들고 다닌다. 크기만 들고 다니면 한 장 밀린 것을 아무도 알아채지 못한다.

## The Rule

1. 좌표계를 이루는 값(이미지 객체 · 크기 · 대상 id)은 **한 함수에서만, 항상 함께** 설정한다.
2. 대상이 바뀌는 순간 좌표계를 **먼저 무효화**한다(`frameId = null`, 이미지 비움). 프레임이 확정되기 전에는 그리지도 저장하지도 않는다.
3. 저장 직전에 `frameId == 지금 대상` 을 검문한다.
4. 저장하는 행에 **프레임 크기를 함께 기록**한다 — 나중에 전수 검증할 수 있는 유일한 방법이다.

```js
function applyImage(img, id, gen) {
  if (gen !== lb.gen) return;
  if (img._id !== id || !img._ow) return;          // 좌표계 미상 → 차단
  lb.img = img; lb.ow = img._ow; lb.oh = img._oh; lb.frameId = id;
}
```

## Why it works

같은 변환으로 그린 이미지와 박스는 언제나 일치한다. 어긋남은 프레임이 대상과 다를 때만 생기므로, **프레임과 대상을 한 값으로 묶으면 그 상태가 표현 불가능**해진다. 버그를 고치는 대신 버그를 만들 수 없게 하는 쪽이다.

## Trade-offs

- 로딩 중 캔버스가 비어 보인다. 앞 장 사진 위에 새 장 박스를 그리는 사고를 원천 차단하는 대가로 받아들인다.
- 클라이언트 혼자서는 **크기만 밀린 경우**를 못 잡는다(자기가 틀렸는지 알 근거가 없다). 반드시 [[server-side-write-verification]] 과 함께 쓴다.

## Anti-Pattern

[[unnamed-coordinate-frame]]

## Related

- Concepts: [[coordinate-frame]]
- Patterns: [[generation-token]], [[server-side-write-verification]], [[build-fingerprint]]

## Grounding (References)

- `doc/raw/2026-09-02.md#case-6` (`hash:d5366c5`)
- `assets_dev/train/webtool.html` — `applyImage` / `frameGuard`
