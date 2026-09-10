# 상용 인식 강화 프롬프트 — 갭 분석

2026-09-09 · 칸반 카드 「상용 인식 강화 갭 분석」 수행 결과.
대상 프롬프트: [`strengthening-prompt-2026-09-09.md`](strengthening-prompt-2026-09-09.md) (§1–§52).

## 0. 한 줄 결론

프롬프트가 요구하는 시스템 뼈대(단계별 검증·abstain·프레임 합의·도메인 검증·에러
텍소노미)는 **이미 대부분 구현돼 있고**, 실제 갭은 네 곳에 모인다 —
**① 학습/평가 분할이 이미지 단위 시드 셔플이다(누수 미계측)**, **② 앱 스캔 경로에
글레어 게이트가 없다(블러만 있다)**, **③ CTC 리더의 온디바이스 전환이 아직 없다**
(ONNX 방향은 확정), **④ dot·unit 의 단계별 지표가 없다**(완전일치·위험군만 있다).
나머지 권고 다수는 이미 A/B 로 종결된 결정과 충돌한다(§4 참조 — 새로 꺼내지 않는다).

프롬프트 §45 의 확인 목록은 15항목이다(카드 표기 "45개"는 절 번호를 개수로 오독한
것이다). 아래 표가 그 15항목의 전수 매핑이다.

## 1. 방법

코드·스크립트·보고서를 직접 읽어 상태를 매겼다. "읽어보니 되는 것 같다" 로 끝내지
않기 위해 각 행에 파일 경로(가능하면 줄번호)를 붙였다. 평가 수치는 전부 기존
보고서의 계측값을 인용했다(본 카드에서 새로 학습하거나 재측정하지 않았다).

## 2. §45 수용기준 15항목 매핑

| # | 요구 | 판정 | 근거 |
|---|---|---|---|
| 1 | 정상 mg/dL 안정 판독 | 부분 | PC 홀드아웃 완전일치 97.06%(G29). 앱 온디바이스는 규칙 엔진+7seg CNN 뿐(`ocr_bootstrap.dart`), CTC 미탑재. 실기기 튜닝은 `CLAUDE_TASKS.md` 제품 리스크 1순위로 남아 있음 |
| 2 | mmol/L 소수점 정확히 | 부분 | 규칙 엔진은 소수점 채널을 별도로 읽는다(`segment_rule_engine.dart:23`, `segment_sampler.dart`의 `hasDecimalPoint`). CNN은 소수점 클래스가 없어 mg/dL 전용으로 선언하고 스캐너가 시작 시점에 거른다(`seven_seg_cnn_engine.dart:18-21`). CTC는 dot 포함 문자열 학습. 셋 다 실기기 검증 없음 |
| 3 | dot 소실 감지 | 부분 | 규칙 엔진은 빈 글리프·해밍 동점을 판독 불가로 명시(`segment_patterns.dart:60-88`). 그러나 평가에는 dot recall/precision 별도 지표가 없다 → 갭 ④ |
| 4 | 90°/180° 회전 처리 | 부분 | 데이터 축: EXIF 좌표계 통일(G20·G22), 회전 장 전용 경로 `rotated_ids`(1564·1565), upright 라벨. 앱 엔진은 정면 촬영 가정(`segment_rule_engine.dart:30`) |
| 5 | 가로형/세로형 모두 | 부분 | 세로형 중심 GM 검출기(ft3 96.52%, `DONE.md:157`), 가로형 한정 순수 CV 93.5%·GM∪CV 하이브리드 95.6%(`sugarscan-cv-band-viability`). G32 의 13장(가로형 GM 실패)은 재기만 상태, 형태 판정 기준 손보기가 사람 대기 |
| 6 | glare 강한 경우 억지 출력 금지 | 부분 | PC: TTA 득표율이 거절 신호(위험군 0.98%, `eval_reader.py:6-7`). 앱: 블러 게이트만 있고 글레어 게이트가 없다 → 갭 ② |
| 7 | blank LCD 오인 금지 | 충족(설계) | `bits==0 → BlankGlyph`, CNN "표시 없음" 클래스, 분리도 게이트 0.25(`segment_rule_engine.dart:126`) |
| 8 | LO/HI 정상 상태 처리 | 충족 | `MeterRangeReading`(단위 제거→HI/LO 판정→글자 교정 순서가 안전 장치, `reading_normalizer.dart:59-101`). 테스트 `--plain-name "LO 를 10 으로 읽지 않는다"` 고정 |
| 9 | Error 코드 지원 | 없음 | `ScanRejectionReason` 은 high/low 뿐(`scan_outcome.dart:4-10`). `ReadingNormalizer` 는 `E` 를 길자 취급하지 않아 `E-1` 이 `1` 로 정리될 수 있다. 현행 두 엔진은 E 를 출력할 수 없어(`segment_patterns.dart:50-52` 글자는 L·H 만) 노출은 제한적이나 CTC 탑재 전에 막아야 한다 → §5 handoff |
| 10 | unit/value 충돌 reject | 충족 | `GlucoseValidator` — 형태 정규식+단위별 소수 자릿수+물리 범위(mg/dL 10–900, mmol/L 0.6–50, `glucose_validator.dart:23-27`). mmol/L 100 → outOfRange, mg/dL 5.6 → unexpectedDecimals |
| 11 | 프레임 불안정 → 재촬영/미확정 | 충족 | `ReadingStabilizer` — 연속 3회 일치+평균 확신도 0.85(`reading_stabilizer.dart:48-54`). 불일치·저신뢰는 `ScanScanning` 유지 |
| 12 | train/test leakage 없음 | **미충족** | `build_cache_v2.py:143-177` — GM 쿼드 풀 2,007장을 **이미지 단위로 시드 셔플**해 train/holdout 분할. 촬영 버스트/세션 그룹 분할 아님 → 갭 ① |
| 13 | unseen device 평가 | 미충족 | Datumo 단일 코퍼스. 다른 기기 실촬영 데이터 없음 → handoff 「미학습 기기 평가셋 확보」 |
| 14 | 모바일 latency/memory 측정 | 미충족 | CTC 미탑재. 엔진 descriptor 의 `targetLatencyMs` 는 선언만. ONNX 방향 확정(86d3dbe), YOLOX ONNX 는 이미 내보냈다(`onnx_export.log`, 8/28) → 갭 ③ + handoff 「온디바이스 ONNX 런타임 선택」 |
| 15 | 단계별 error taxonomy | 충족(PC) | 판독 실패 아틀라스 — 오답 35건 전량 판정: 검출 37%·리더 49%·귀인불가 14%(`failure-atlas.md`), `G23-ctc-error-taxonomy.md`. 앱은 `OcrFailureKind` 가 엔진 수준 분류 |

## 3. 단계별 권고(§1–§44) 매핑 — 요약

- **§1.1 일반 OCR 배제: 정렬.** 레지스트리가 네트워크 엔진 등록을 거부한다(규칙:
  OCR 은 단말에서만). 일반 OCR 은 `bench_external_ocr.py` 로 비교 대상으로만 측정했다.
- **§3 Stage 1 Display Detector: 부분.** PC 측엔 YOLOX GM(+CV 하이브리드)가 있지만
  앱에는 없다 — 앱은 사용자가 가이드 박스에 맞추는 수동 ROI(`OcrFrame.roi`)다.
  CTC 온디바이스 전환 시 검출기를 같이 싣느냐는 ONNX 런타임 handoff 와 함께 갈 문제.
- **§4 padding_x/y 독립 설정: 있음.** BOX_MARGIN 스윕(G26), 비대칭 pad_x=1.0(cv-band).
- **§5 orientation classifier: 부분.** upright 4방향 라벨+회전 장 경로는 있으나 별도
  분류기는 없다. 프롬프트 스스로 "불필요하면 늘리지 말라" 고 했고, 현재 증거로는
  불필요 — 벤치마크 근거가 생기면 재론.
- **§6–7 글리프 검출+Tiny CNN: 대체 구현으로 충족.** 글리프 detector+classifier
  분리 구조는 아니지만 규칙 엔진(비트 매칭, 학습 없음)이 동등 기능을 더 단순하게
  수행한다(§42 단순화 우선과 부합). CTC 는 시퀀스 한 덩어리로 읽는다.
- **§8 dot 특별 취급: 부분.** 규칙 엔진은 별도 채널, CTC 는 문자열의 일부. 평가 지표
  없음 → 갭 ④.
- **§9 시퀀스 X 정렬 재구성: 정렬.** `DisplayAssembler`, CTC 디코딩이 해당.
- **§10 unit 4상태: 부분.** 엔진 `supportedUnits` 선언+앱 전체를 막는 `UnitGate`.
  화면에 찍힌 단위 텍스트는 normalizer 가 조용히 떼어낼 뿐 "화면 단위 ≠ 사용자
  단위" 충돌 검사는 없다. 다만 단위 오인의 결과값 대부분은 §10 범위 검증에서
  걸러진다. CTC 탑재 시 화면 단위 판독을 검사에 넣을지는 판단 사항.
- **§11 device profile: 부분(의도됨).** `MeterProfile`(자릿수·기하)만 있다. 프롬프트도
  초기 단계 device identification 구현을 요구하지 않는다 — 정렬.
- **§13 검증 체인: 충족.** normalizer → validator → stabilizer 순서가
  `glucose_scanner.dart:187-227` 에 그대로 있다.
- **§14 abstain: 충족.** `UnknownGlyph`·`noTextFound`·검증 실패값의 안정화기 미투입
  (`glucose_scanner.dart:202-206`), 프레임 합의 미충족 시 계속 스캔.
- **§15–16 입력 품질 게이트·실시간 글레어: 부분 → 갭 ②.** `FrameQualityGate` 는
  라플라시안 분산(블러) 하나고, 임계값 60 은 "실촬 골든셋 확보 후 재보정 대성"
  이라 주석에 적혀 있다(`frame_quality.dart:24-27`). 규칙 엔진에만 적용, CNN 엔진엔 없음.
- **§17–18 글레어 합성: 충족(합성).** `synth_lcd.py:205-215` — 스페큘러 블롭을 알파
  마스크로 블렌드(포화 클리프 포함), 반사 줄무늬·국소 그림자·shear·키스톤(G27 실화면화
  4요소). 프롬프트가 요구한 "흰 원 갔다 붙이기 금지·알파 합성" 과 같은 설계.
- **§19 resize/dot 크기 계측: 부분.** 입력 320×160 고정. dot 직경의 리사이즈 전후
  계측은 없다 → 갭 ④ 카드에 포함.
- **§20 회전·종횡비 증강: 충족.** 파인튜닝 증강 회전·이동·줌·대비(`ctc_reader_v2.py:92-94`),
  합성 shear·키스톤. "검증으로 유지 여부 판단" 도 관행화(G25~G31 전부 검증 후 결정).
- **§21 mmol 부족 데이터: 대기.** 실츬 mmol/L 데이터 자체가 부족하다 — 증강 이전에
  데이터 확보가 먼저다(미학습 기기 handoff 와 같은 성격).
- **§22–25 라벨 스키마·도구·가이드라인: 부분·정렬.** 자체 webtool 라벨러(LCD 211·밴드
  306 라벨, 검수 모드·upright 필드). CVAT 교체는 불필요(§4 참조). 밴드 라벨 오염
  ~20% 추정·검수 방법(전수 순회 vs 비전 스크리닝)은 사람 대기 과제로 존재한다.
- **§26 분할 규칙: 미충족 → 갭 ①.** §45-12 와 동일.
- **§27–28 하드케이스·하드 네거티브: 부분.** 아틀라스가 대조군·계층화를 갖추고 있고
  (aggregate-hides-stratified-failure 대응), blank 합성은 있으나 "비-LCD 텍스트·버튼·
  손가락" 등 네거티브 실촬 의도 수집은 없다. 검출기 오탐이 실측 문제가 되면 그때.
- **§29 지표: 부분.** 완전일치·위험군·득표율은 있다. dot recall/precision, unit
  accuracy, mAP 는 없다 → 갭 ④.
- **§30 에러 텍소노미: 충족(PC).** §45-15 와 동일.
- **§31 단계별 confidence 보존: 부분.** 앱은 `ScanConfirmed.confidence` 하나(엔진 최약
  자리 확신도의 프레임 평균). display/glyph/dot/unit 분리 보존은 없다. PC 아틀라스는
  타임스텝 확률까지 시각화한다. 운영 데이터가 생기면 분리 가치가 커진다.
- **§32 temporal consensus: 충족.** §45-11 과 동일.
- **§33 RETAKE 정책: 충족(구조).** 확정 실패는 스캔 지속+수동 입력 상시 경로(규칙:
  기록을 남기지 못하는 상태 금지). 최종 상태를 SUCCESS/RETAKE/UNKNOWN/ERROR 4종으로
  명명하지는 않지만 의미 구조는 같다.
- **§34–35 모바일 벤치마크: 미충족 → 갭 ③.** §45-14 와 동일.
- **§36 학습/추론 전처리 일관성: 대기.** 온디바이스 전환이 없어 아직 적용 대상이
  없다. ONNX 카드의 필수 명세로 붙였다.
- **§37 false confidence 방지: 충족.** 도메인 검증 실패값은 확신도와 무관하게
  안정화기에 안 들어간다(`glucose_scanner.dart:202-206`).
- **§38 data leakage 방지: 미충족 → 갭 ①.** 근접 프레임 쌍 계측 포함.
- **§39 합성 데이터 원칙: 정렬.** 합성=사전학습, 실사진=파인튜닝·평가 — 정확히 이
  구조다(`ctc_reader_v2.py` 사전학습→real finetune 2단계).
- **§40 기존 코드베이스 먼저: 정렬.** 본 보고서가 그 실행이다.
- **§42 모델 복잡화 최후 수단: 정렬.** 규칙 엔진 철학과 동일하다.
- **§43 ablation: 정렬.** A/B+McNemar+예산 일치(G31)가 이미 관행이다.
- **§44 false reading 최우선: 정렬.** 위험군 지표·G24 confidence sweep 이 이 관점이다.
- **§46 임계값 설정 분리: 부분.** 앱 엔진 임계값은 생성자 주입으로 분리돼 있다.
  학습 스크립트의 하이퍼파라미터는 상수 — 운영 config 분리는 ONNX 통합 시점 과제.
- **§47 디버그 시각화: 충족(PC).** 아틀라스 컨택트 시트(원본·워프·타임스텝·TTA·판정),
  webtool 검수 뷰.
- **§48 결과 구조: 부분.** `ScanConfirmed` 는 value·unit·confidence·engineId·rawText·
  frameCount 를 보존한다. per-stage confidence 없음(§31 과 동일한 갭).
- **§49 금지사항 전항: 정렬.** 전부 이 저장소의 기존 규칙과 일치한다.

## 4. 프로젝트 결정과 충돌하는 권고 — 새로 꺼내지 않는다

1. **§2 "4모서리 원근 변환 기본 배제, padded-bbox 크롭이 기본"** — 이 저장소에서
   이미 A/B 로 종결됐다. G30(세로형 밴드 크롭, 패딩 중심 접근)은 보류, G31(예산을
   60에폭으로 맞춘 재측정)은 **기각** — 95.72%/위험 3.48% vs 현행 워프 기준선
   97.06%/0.98% (McNemar p=0.0357, `G31-bandcrop-epoch-matched.md`). G29 letterbox도
   기각급 하락. 자동 유리 쿼드는 이미 "검수 참고"로 강등돼 있다(2026-09-01 결정).
   padded-crop 재실험은 새 근거 없이 금지한다.
2. **§23 CVAT 우선 검토** — 자체 webtool 라벨러에 LCD 211·밴드 306 라벨이 살아
   있다. 도구 교체는 라벨 자산 이동 비용만 만든다. jsonl 표준 포맷 유지.
3. **§1.1 "일반 OCR 은 fallback 으로도 검토 가능"** — fallback 검토 자체는 규칙
   위반이 아니나, 구현은 불가하다: 레지스트리가 `requiresNetwork` 엔진을 항상 거부하고
   조건부 허용 플래그 금지가 저장소 규약이다(비고: EasyOCR 학습 가중치 배포 조건
   미확인, `docs/LICENSES.md` §4).
4. **§32 "가능하면 confidence weighted voting"** — 현행 `ReadingStabilizer` 는 연속
   일치+평균 확신도 게이트다. weighted voting 이 실측에서 더 좋다는 근거가 없다.
   바꾸려면 A/B 로.

## 5. 실제 갭 → 보드 등록 내역

| 갭 | 카드 | 종류 |
|---|---|---|
| ① 이미지 단위 시드 분할, 그룹 누수 미계측 | 「분할 누수 감사」(등록됨, 본 카드 다음) | 실행 |
| ② 앱 스캔 경로 글레어 게이트 부재(블러만) | 「스캔 글레어 게이트」 신규 | 실행 |
| ③ CTC 리더 온디바이스 전환 미착수 | 「CTC 리더 ONNX 내보내기 파리티」 신규 + 「온디바이스 ONNX 런타임 선택」(등록됨) | 실행+판정 |
| ④ dot·unit 단계별 지표 부재 | 「dot·unit 지표 추가」 신규 | 실행 |
| ⑤ E-n 에러 코드 미지원(제품 판단 필요) | 「에러 코드 상태 지원」 handoff 신규 | 판정 |
| — 미학습 기기 평가 데이터 없음 | 「미학습 기기 평가셋 확보」(등록됨) | 판정 |

갭 ① 은 기준선 97.06% 의 **유효성** 문제다. 이 숫자에 매달린 모든 A/G30~G32 비교가
누수 여부의 영향을 받으므로, 다른 인식률 개선 카드보다 앞서야 한다(보드 ordinal
2000, 본 갭 분석 다음).

## 6. 근거 파일

- 앱: `lib/ocr/src/scanner/glucose_scanner.dart` · `scan_outcome.dart` ·
  `correction/reading_stabilizer.dart` · `correction/reading_normalizer.dart` ·
  `engines/segment_rule/{segment_rule_engine,frame_quality,segment_patterns}.dart` ·
  `engines/sevenseg_cnn/seven_seg_cnn_engine.dart` ·
  `lib/domain/services/glucose_validator.dart`
- 학습/평가: `assets_dev/train/{build_cache_v2,ctc_reader_v2,eval_reader,synth_lcd}.py` ·
  `onnx_export.log`
- 보고서: `docs/reports/failure-atlas.md` · `G23-ctc-error-taxonomy.md` ·
  `G29-letterbox-warp.md` · `G30-band-crop.md` · `G31-bandcrop-epoch-matched.md` ·
  `G32-wide-gm-failures.md` · `docs/DONE.md`
- 위키: `model-invents-what-it-cannot-see` · `aggregate-hides-stratified-failure` ·
  `metric-path-not-under-test` · `experiment-budget-parity`
