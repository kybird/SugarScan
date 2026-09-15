---
status: active
version_context: "sugarScan assets_dev/train/devices.html (라벨링 SPA, 인라인 'use strict')"
tags: [ui, javascript, anti-pattern]
aliases: [drawPred 스코프 사고, boot 내부 함수를 전역이 부른다, 부분 렌더, strict mode ReferenceError, 히어로만 뜨고 스트립이 비었다]
created: 2026-09-15
confidence: 5
---
# 초기화 함수 안에 든 헬퍼를 전역 렌더 함수가 부른다

`boot()`/`init()` 같은 초기화 함수 **안에** 정의한 헬퍼를, 그 밖의 전역 렌더
함수가 호출하면 `ReferenceError` 로 렌더가 도중에 죽는다. 이때 화면은 예외
화면이 아니라 **부분 렌더**로 남는다 — 그래서 스코프 버그가 데이터·필터
버그처럼 보인다.

## 실패 모드

`devices.html` 커밋 `9586499`(밴드 검출기 예측 오버레이)에서 실제로 일어난 일.
`drawPred` 를 `boot()` 내부 함수로 추가했는데 호출부는 전역 함수인
`renderStrip`(709행)·`renderSugg`(806행)에 달렸다. 함수 선언은 자기 몸통
스코프에만 묶이므로 전역에서 보이지 않고, strict mode 는 암묵 전역도 안
만들어 즉시 죽는다.

```
ReferenceError: drawPred is not defined
    at renderStrip (devices.html:709)
    at render (devices.html:652)
    at toggleFlat (devices.html:752)
```

치명적인 부분은 죽는 **지점**이다. `renderStrip` 은 `$('#heroImg').src = ...`를
지정한 다음 줄에서 죽으므로 히어로에는 사진이 정확히 한 장 뜨고, 그 뒤의 스트립
썸네일 생성은 실행되지 않는다. 사용자 보고는 "기종을 눌러도 해당 기기 사진이
하나도 표시되지 않고 메인에 딱 하나만 뜬다" — 전형적인 필터 버그 문구다.

커밋의 "브라우저에서 확인"을 통과한 이치도 같다. 페이지 첫 로드의 초기
범위(라벨 없음)는 그날 기준 0장이라 `render()` 가 `renderStrip` 전에 조기
반환한다. **비어 있는 경로에서만 확인하면 렌더 끝까지 도는 경로의 버그는
안 잡힌다.**

## 왜 생기나 (First Principles)

- 기능을 추가할 때 "코드를 어디에 둘까"는 초기화 흐름을 따라가기 쉽다 —
  `boot()` 첫머리면 캐시·청취자 세팅이 자연스럽다. 그러나 **정의 위치는
  호출 위치에 지배된다**는 규칙은 어디에도 명시돼 있지 않다.
- 예외가 이벤트 핸들러·비동기 안에서 터지면 화면을 흔들지 않는다. 콘솔을
  안 보면 남는 것은 "부분적으로 그려진 화면"뿐이다.
- 부분 렌더는 살아남은 앞부분이 그럴듯하다. 히어로에 사진이 있으니 "사진
  로딩은 되는데 목록 계산이 틀렸나?"라는 가설이 먼저 든다.

## 막는 법

1. **전역 렌더 함수가 부르는 헬퍼는 전역에 정의한다.** 페이지 안에서 "렌더
   그래프에 속하는 코드"와 "초기화 코드"의 경계를 주석으로 못박는다
   (devices.html 상단의 PRED 블록 주석이 그것).
2. 기능 추가의 브라우저 확인은 **데이터가 실려 렌더가 끝까지 도는 경로**에서
   한다. 빈 범위의 조기 반환 경로는 아무것도 증명하지 못 한다.
3. "화면 일부만 그려졌다"는 증상에는 콘솔을 먼저 연다. 데이터·필터 가설은
   예외를 본 다음에 세운다.
4. 새 기능이 렌더 파이프라인에 끼어들면 최소 한 번은 전체 렌더 경로
   (render → renderStrip → renderSugg)를 밟는 상호작용을 돌린다.

## Related
- [[display-and-selection-from-different-sources]] — 같은 파일의 사고. "새 모드에서
  시험하지 않았다"와 이번 "빈 경로에서만 확인했다"는 같은 뿌리다: 확인 경로가
  코드 경로를 덮지 못한다.
- [[verify-premises-before-executing]] · [[measure-the-premise-not-just-the-claim]]

## Grounding (References)
- `doc/raw/2026-09-15.md#case-1` — 회귀 `hash:9586499`, 수정은 같은 날.
  브라우저 재현 스택(위 인용)과 수정 후 검증(전체→f→기기 보기 240장
  스트립 1–60, 오버레이 캔버스 점선 393px)이 함께 기록돼 있다.
