# ocr_bench — 판독 벤치 하네스

계획서 [§2.6](../../docs/IMPLEMENTATION_PLAN.md) 의 벤치 하네스. 셀 단위
벤치(`bin/cell_bench.dart`)와 장면 단위 벤치(`bin/scene_bench.dart`)가 있다.

## cell_bench

96×96 셀 이미지에 규칙 엔진의 핵심 3단계를 물린다.

```
JPEG → GrayImage(휘도) → LcdBinarizer → SegmentSampler → SegmentPatternTable
```

```bash
dart run tools/ocr_bench/bin/cell_bench.dart \
  --dataset assets_dev/upstream/7segment-display-reader/01.dataset \
  --out docs/reports/G15-cell-bench-result.md
```

| 옵션 | 뜻 |
|---|---|
| `--dataset <경로>` | 클래스 폴더(`00`~`09`, `11`)를 담은 디렉터리. 필수 |
| `--out <파일>` | 리포트를 마크다운으로 적는다 |
| `--limit N` | 클래스당 N 장. **일정 간격으로 고른다** — 아래 참조 |
| `--dump-failures N` | 실패 사례 N 건의 비트열을 표로 (기본 12) |

## scene_bench

G16 합성 장면(여러 자릿수가 있는 화면 한 장)에 **엔진 전체 경로**
`SegmentRuleEngine.recognize()` 를 통째로 태운다 — 품질 게이트 → 이진화 →
자릿수 분할 → 조립까지. 셀 벤치가 재지 않던 가로 자릿수 분할, `HI`/`LO`,
소수점, 자릿수 결합을 여기서 잰다. 엔진 구성은 앱 부트스트랩과 같은
생성 기본값이며 **벤치가 임계치를 조정하지 않는다.**

```bash
dart run tools/ocr_bench/bin/scene_bench.dart \
  --dataset assets_dev/synth \
  --out docs/reports/G17-scene-bench-result.md
```

| 옵션 | 뜻 |
|---|---|
| `--dataset <경로>` | `labels.jsonl` + `images/` 디렉터리(`tools/synth7seg` 출력). 필수 |
| `--out <파일>` | 리포트를 마크다운으로 적는다 |
| `--limit N` | 일정 간격으로 N 장만 |
| `--dump-failures N` | 오독 사례 N 건을 표로 (기본 12) |

판정은 라벨 `value` 문자열과의 완전일치다. 축별 분해(여백·회전·대비)는
라벨 값으로 구간을 나눈다. 기준선 수치는
[reports/G17-scene-bench-baseline.md](../../docs/reports/G17-scene-bench-baseline.md).

합성 데이터라는 한계는 셀 벤치와 같다 — **§2.7 승격 게이트가 아니다.**
특히 합성 이미지에는 센서 노이즈가 없어 초점 게이트(라플라시안 분산)에서의
거부 비율이 실촬보다 크게 나온다.

## 읽을 때 조심할 것

**이건 §2.7 승격 게이트가 아니다.** 게이트는 혈당계 실촬 골든셋으로만 판정한다.
이 데이터는 혈당계가 아니라 일반 7-세그먼트 디스플레이이고, 이미 잘린 셀이라
ROI 정렬·기하 추정을 건너뛰며, `HI`/`LO` 와 소수점이 한 장도 없다.
**하한선을 재는 도구다** — 여기서 못 읽으면 실기기에서는 확실히 못 읽는다.

**오독과 미판독을 같은 칸에 세지 않는다.** 이 앱에서 위험한 것은 틀린 값을 내는
것이지 못 읽는 것이 아니다. 못 읽으면 사용자는 수동 입력으로 간다. 그래서 정확도
한 줄이 아니라 **치명적 오독률**을 따로 크게 뽑는다.

**`--limit` 은 앞에서 자르지 않는다.** 파일명이 촬영 순서라 앞부분만 집으면 같은
세션의 연속 프레임을 보게 된다 — 조명도 각도도 거의 같은 표본이다. 실제로
`--limit 40`(앞에서 자름)이 "오독 0건, 꺼진 화면에서 값 생성 0건"을 냈는데,
같은 크기의 간격 표본은 오독 9%, 값 생성 4% 를 냈다. **표본을 잘못 고르면 안전해
보이는 쪽으로 틀린다.**

**모델(TFLite)은 호스트에서 못 돈다.** `libtensorflowlite_c-win.dll` 이 Flutter
엔진 캐시에 없어 `Interpreter.fromAsset` 이 실패한다(error 126). 그래서 이 벤치는
모델을 쓰지 않는 규칙 엔진만 잰다. CNN 엔진을 재려면 실기기가 필요하다.

## 왜 `dart run` 인가

`lib/ocr/testing.dart` 만 import 한다. 공개 배럴 `ocr.dart` 를 쓰면
`ocr_bootstrap.dart` → `tflite_flutter` → Flutter 가 딸려 들어와 순수 Dart 로는
돌지 않게 된다. **이 import 를 바꾸지 말 것.**
