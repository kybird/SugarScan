# G33 — 에러 코드가 값으로 둔갑하는 것을 막는다

- 브랜치: `glm/G33-error-code-guard`
- 상태: 완료 — 아래 AC 증거 전부 객관적 측정

## 무엇을 했나

`lib/ocr/src/correction/reading_normalizer.dart` 한 파일, 두 변경점.

1. 에러 표시 정규식 추가(`reading_normalizer.dart:49-52`):

```dart
  /// 혈당계 에러 표시(`E-1` · `ERR-5` · `ERROR2` 계열). `^$` 가 없으면
  /// `123E` 같은 정상 판독의 일부를 삼켜 버린다.
  static final RegExp _errorCode =
      RegExp(r'^(E-?\d{1,2}|ER{1,2}-?\d{0,2}|ERROR\d{0,2})$');
```

2. 판정은 **② HI/LO 판정과 같은 구간, ③ 글자 교정 앞**에 넣었다
   (`reading_normalizer.dart:75` 의 ② 주석 뒤, `:93` 판정, `:97` 의 ③ 앞).
   `compact`(공백 제거·대문자화) 기준으로 매칭하고 반환은 기존
   `UnreadableReading` — 새 서브클래스 없음:

```dart
    // 에러 표시도 같은 구간(글자 교정 앞)에서 가려낸다. `E-1` 을 교정까지
    // 흘려 보내면 E 가 떨어져 나가 `1` 이 되고, mmol/L 하한(0.6)을 통과해
    // 멀쩡한 혈당값으로 저장된다. mg/dL 하한(10)이 우연히 막아 주는 것과
    // 달리 단위에 따라 구멍이 열리니 검증기가 아니라 여기서 막아야 한다.
    // 상태로 기록하지도 않는다 — 에러 코드는 혈당 정보가 없고 뜻이
    // 제조사마다 다르다.
    if (_errorCode.hasMatch(compact)) {
      return const UnreadableReading();
    }
```

테스트는 `test/ocr/reading_normalizer_test.dart` 기존 파일에 그룹
'혈당계 에러 표시' 4건을 추가했다(새 파일 아님). `lib/ocr/src/` 직접
import 없이 `package:sugarscan/ocr/testing.dart` 경유만 사용.

건드린 것은 이 두 파일뿐. `glucose_validator.dart` · 배럴 · `ScanOutcome` ·
확인 시트 · l10n ARB · `_confusions`/`_unitTokens`/`_high`/`_low` ·
①②③ 순서 · `assets_dev/` 전부 무변경.

## 왜 위치가 전부인가

`normalize()` 의 호출처는 `glucose_scanner.dart:187` 하나뿐(grep 전수 확인).
거기서 `NormalizedNumber` 만 검증기로 흘러가므로(`:201-207`), 교정 앞에서
`UnreadableReading` 으로 떨어뜨리면 검증기에 아예 도달하지 않는다.

③ 뒤에 두면 이미 E 가 떨어져 `'1'` 이 된 뒤라 아무것도 못 잡는데 테스트는
통과한다 — 카드가 경고한 자리다. 위 인용대로 ② 구간(`:93`)이 ③(`:97`)
앞에 있다.

단위 비대칭이 이 구멍의 실체다. 수정 전 실측(카드 Notes 와 동일 재현):
`E-1` → 정규화 `'1'` → mg/dL 하한 10 이 거절하지만 mmol/L 하한 0.6 은
`1.0` 을 통과시킨다. `E-5` → `5.0 mmol/L` 은 완전 정상값으로 저장된다.
LO→10 과 같은 계열이되 단위에 따라 열리고 닫힌다.

## AC 증거

| AC | 증거 |
|---|---|
| #1 E-1~E-9·ER·ERR·ERR-5·ERROR2 가 값으로 안 나온다 | 테스트 'E-1 · ER · ERR-5 · ERROR2 를 값으로 만들지 않는다' — 16 입력(`E-1`~`E-9`, `ER`, `ERR`, `ERR-5`, `ERROR2`, `E1`, `err-5`, `error 2`) 전부 `isA<UnreadableReading>` 통과 |
| #2 mmol/L 로도 검증기를 통과하지 않는다 | 테스트 'mmol/L 로도 검증기를 통과하지 않는다' — `E-1`·`E-5`·`ERR-5`·`ERROR2` 를 정규화하고, 숫자가 나왔다면 `GlucoseValidator.parse(text, mmoll).isOk == false` 를 단언. 역방향 고정도 함께: `parse('1', mmoll).isOk == true`(검증기만으로는 못 막는다는 증거 — 막는 주체가 이 판정임) |
| #3 회귀: HI·LO·H1·HIGH·LOW → MeterRangeReading, 138 mg/dL → 138, 7.6 mmol/L → 7.6 | 기존 테스트 3건이 그대로 커버('LO 를 값 10 으로 오독하지 않는다' LO/Lo/LOW · 'HI 도 값으로 해석하지 않는다' HI/HIGH/H1 · '단위 표기를 떼어낸다' 138/7.6) — 전체 스위트에서 통과 |
| #4 경계: 123E → 123, E·E- → UnreadableReading | 테스트 '숫자 뒤에 붙은 E 는 에러로 보지 않는다'(`number('123E') == '123'`) · 'E 단독 · E- 는 읽을 수 없다' |
| #5 판정이 글자 교정(③) 앞 | 위 코드 인용 — 판정 `:93`, ③ 시작 `:97` |
| #6 analyze 무경고 + 전체 통과 | `flutter analyze` → "No issues found! (ran in 6.1s)" · `flutter test` → **+397: All tests passed!**(기존 393 + 신규 4) |

## 정규식 설계 메모

- 세 패턴은 지시서가 정한 것 그대로: `^E-?\d{1,2}$` · `^ER{1,2}-?\d{0,2}$` ·
  `^ERROR\d{0,2}$` 를 하나의 교대로 합쳤다. `^$` 부착(AC 경고).
- `ERROR2` 는 `ER{1,2}-?\d{0,2}` 로는 못 맞는다(E-R-R-O-R-2 에서 `\d` 가
  `O` 앞에서 끊김) — 세 번째 패턴이 담당하고, 앵커가 있어 역추적 후
  전체 일치로 잡힌다. 테스트가 통과한 것이 그 증거.
- `E` 단독·`E-` 는 패턴이 요구하는 최소 자릿수(숫자 1개)를 못 채워
  에러 판정을 안 타고, ③ 이후 비숫자 제거로 빈 문자열이 되어
  기존 경로 그대로 `UnreadableReading` 이 된다(AC #4 테스트).
