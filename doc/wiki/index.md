---
tags: [index]

# Wiki Index

이 프로젝트의 구조화된 지식 베이스입니다. `doc/raw/` 로그에서 추출한 핵심 개념과 패턴을 정리했습니다.

---

## Concepts

| 개념 | 설명 | 별칭 |
|------|------|------|
| [[canonical-value]] | 한 사실을 두 군데에 적으면 언젠가 갈라진다. | 정본, single-source-of-truth, value_mgdl, valueMgdl, enteredValue, enteredUnit, valueIn, GlucoseReading |
| [[coordinate-frame]] | 좌표 4개짜리 배열은 **그 자체로는 아무 의미가 없다.** `(559, 345)` 는 "어느 이미지의, 어느 크기·방향 공간에서" 잰 값인지가 붙어야 비로소 위치를 가리킨다. | 좌표계, frame, 표시 좌표계, cross-space-comparison, lb.ow, exif_transpose, quad, screen_boxes.jsonl, oriented |
| [[experiment-budget-parity]] | A/B 로 **구조**(프레이밍·전처리·아키텍처)를 비교하려면 두 팔이 같은 만큼 | 학습 예산, 에폭 수, 예산 일치, budget parity, 대조군 예산, A/B 공정성, fair comparison, 수렴 부족, undertrained |
| [[knowledge-retrieval-shape]] | 지식 베이스의 가치는 **쓰여 있는가**가 아니라 **필요한 순간에 그 사람이 던지는 질의 모양으로 걸리는가**로 정해진다. | 검색 질의 모양, llm-wiki search, grep 폴백, retrieval |
| [[live-query]] | Drift 의 `watch()` 는 테이블이 바뀔 때마다 **처음 만든 SQL 을 그대로 다시 돌린다.** 파라미터를 다시 계산하지 않는다. | 살아 있는 질의, Drift watch, 스트림 질의, StreamProvider, watchBetween, autoDispose, Drift watch() |
| [[metric-provenance]] | 숫자는 출처를 달고 다니지 않는다. | 수치 출처, 지표 출처, 무엇을 잰 값인가, metric provenance, 비교 가능성 |
| [[project-resource-vs-branch-resource]] | 저장소 안의 파일은 기본적으로 **브랜치 자원**이다. | 프로젝트 자원, 브랜치 자원, 공유 상태, 무엇을 어디에 두나, worktree |
| [[wire-schema-evolution]] | 앱이 출시되는 순간부터 **여러 버전이 동시에 같은 서버를 읽고 쓴다.** 구버전 클라이언트는 이미 사용자 기기에 설치돼 있어 나중에 고칠 수 없다 — 이것이 이 주제의 모든 제약을 만든다. | 스키마 진화, 버전 공존, forward-compatibility, additive-only-wire-schema, fromWireName, wireName, ReadingDto, MeasurementTag, ReadingSource |

---

## Patterns

| 패턴 | 설명 | 별칭 |
|------|------|------|
| [[build-fingerprint]] | 돌고 있는 클라이언트가 **어느 빌드인지** 화면에서 읽히게 한다. | 빌드 지문, stale-tab-detection, /api/build, _build_stamp, checkBuild, Cache-Control: no-store |
| [[contract-boundary-equals-method-boundary]] | "이 메서드는 예외를 던지지 않는다"는 계약을 걸었으면, `try` 는 **메서드 전체**를 감싸야 한다. | 계약 경계, never-throws, GlucoseScanner.offer, _recognizeSafely, ScanUnavailable |
| [[cursor-holdback-for-skipped-rows]] | 델타 커서를 어디까지 미느냐는 **왜 건너뛰었는지에 따라 정반대**다. | 커서 홀드백, delta cursor, SyncCursorStore, _pull, _apply, updated_at, skippedFrom |
| [[declare-what-the-human-knows]] | 도메인 사실(기기의 성질·부품의 종류·문서의 종류)을 사람이 이미 안다면, | 사람이 아는 것은 선언한다, 재지 말고 라벨, 도메인 사실은 라벨, declare not measure |
| [[dry-run-before-repair]] | 사람이 만든 데이터를 되돌리는 스크립트는 **기본 동작이 "계산만"** 이어야 한다. | 복구 스크립트 규약, --apply, 백업 후 수정, repair_prevframe_labels.py, repair_unrotated_band_labels.py |
| [[frame-provenance-binding]] | 좌표를 다루는 상태에는 **그 좌표계가 누구의 것인지**를 함께 들고 다닌다. | 프레임 이름표, frame-id-binding, 좌표계 귀속, applyImage, frameGuard, lb.frameId, webtool.html |
| [[generation-token]] | 비동기 작업을 시작할 때 세대 번호를 찍고, 결과를 반영하기 전에 **그 세대가 아직 유효한지** 확인한다. | 세대 토큰, 세션 토큰, stale-response-guard, lb.gen, _session, GlucoseScanner.offer, show() |
| [[measure-the-premise-not-just-the-claim]] | 기록된 결정은 "무엇을 정했나"와 "왜 그렇게 정했나"를 함께 담는다. | 전제, 근거가 낡았다, 결론은 맞는데 이유가 틀렸다, D-2, 상태 공간, 결정 재검토 |
| [[open-upper-bound-for-live-window]] | "최근 N일" 같은 살아 있는 기간 질의는 **위쪽 경계를 열어 둔다.** 상한에 "지금"을 넣지 않는다. | 열린 상한, 기간 질의, statsReadingsProvider, watchBetween, refreshStatsProvider |
| [[push-over-pull-for-prevention]] | **검색은 pull 이다 — 물어볼 줄 알아야 걸린다.** 예방이 목적이라면 검색에 기대면 안 된다. | 푸시 우선, 트리거 표, CLAUDE.md 표, AGENTS.md, 예방은 검색으로 안 된다 |
| [[row-level-decode-tolerance]] | 배치에서 행 하나를 해석하지 못했다고 배치 전체를 실패시키지 않는다. **관용의 단위는 행이다.** | 행 단위 관용, poison-row 방어, ReadingPage, fetchUpdatedSince, fetchedRows, malformed, ReadingDto.fromJson |
| [[scene-component-split]] | 세션 메타데이터(촬영 시각·기기 id)가 없는 코퍼스에서는 **픽셀 유사도의 연결요소**를 | 장면 성분 분할, 그룹 분할, 연결요소 분할, scene split, session-aware split, grouped split |
| [[server-side-write-verification]] | 클라이언트가 "무엇을 기준으로 만든 값인지"를 함께 보내게 하고, **서버가 정본에서 직접 재확인한 뒤에만** 기록한다. | 저장 검문, 쓰기 검증, 409 거부, _verify_frame, /api/label, webtool.py, 409 |
| [[tolerant-decode-with-preservation]] | 모르는 값을 만나면 **관용하되 보존한다.** 기본값으로 치환하고 그대로 되돌려 쓰면, 관용이 곧 데이터 파괴가 된다. | 관용 디코드, unknown 보존, additive-only, fromWireName, orElse, MeasurementTag, ReadingSource, GlucoseUnit |
| [[verify-premises-before-executing]] | 지시서를 받으면 **적힌 대로 하기 전에 전제가 사실인지 먼저 잰다.** 지시서를 쓴 | 전제 실측, 지시서 검증, 요약 먼저, 위임 안전장치 |

---

## Anti-Patterns

| 안티패턴 | 설명 | 별칭 |
|------|------|------|
| [[ad-hoc-ruler-beside-the-committed-one]] | 같은 축을 재는 측정 스크립트가 이미 저장소에 있는데, 그걸 찾지 않고 그 자리에서 | 즉석 자, 자가 있는데 새로 잼, 측정 스크립트 중복, ad hoc ruler, 재현 불가 수치 |
| [[aggregate-hides-stratified-failure]] | 소수 층의 심각한 실패가 다수 층에 희석되어 **지표에서 사라진다.** 그리고 그 소수 층이 하필 제품에서 중요한 경우가 많다. | 층화, 평균에 묻힌다, stratify, 전체 정확도, 가로 화면, 소수 클래스, 대조군, control group, 표본이 작다 |
| [[backup-list-by-importance-not-by-what-writes]] | 중요한 자산을 떠 놓고 안심한다. | 백업, 덮어쓰기, 무인 실행, 밤샘, 소실, 재생성 가능, 시드, np.random, synth_screens |
| [[bounds-check-as-correctness-proof]] | 파손된 좌표를 보정할 때 **결과가 이미지 경계 안에 들어오는지**로 맞았는지 판정하는 것. | 경계 통과를 정답으로 오인, oob 검사 과신, audit_oob.py, oob, 경계 초과 |
| [[comparison-across-different-denominators]] | 비교 출력이 두 수치를 나란히 인쇄한다. | 분모가 다른 비교, 다른 물건을 나란히, 같은 이름 다른 기준, denominator mismatch |
| [[contract-guard-too-narrow]] | "이 메서드는 예외를 던지지 않는다"고 문서에 적어 두고, `try` 는 **위험해 보이는 호출 하나만** 감싸는 것. | 좁은 try, 계약보다 좁은 방어, GlucoseScanner.offer, _recognizeSafely, glucose_scanner.dart |
| [[count-rows-not-entities]] | 아웃박스는 변경마다 행을 쌓지만, 서버로는 **현재 상태 한 번**만 간다. | 대기 n건 오표시, 큐 행 세기, pendingSyncCountProvider, syncMaxAttemptsProvider, syncOutboxRows, blockedCount, providers.dart |
| [[coupled-budget-loop-defeats-per-element-tuning]] | "목표치에 닿을 때까지 뽑는다"는 루프에서는 요소들의 출현 확률이 **독립이 아니다.** | 총량 제약 루프, 확률만 조정, 밀도 채움 회귀, coupled budget loop, 풍선 효과 |
| [[degradation-past-legibility]] | 증강은 강할수록 강건해진다는 직관이 있다. | 열화 상한, 증강 과다, 읽을 수 없는 표본, 라벨 잡음, illegible |
| [[device-fixed-to-a-single-point]] | 합성 데이터에서 각 클래스(여기서는 기기)를 **측정 중앙값 한 점**으로 고정한다. | 기기 한 점 고정, 중앙값으로 못박기, 다양성 손실, single point per class |
| [[display-and-selection-from-different-sources]] | 목록을 보여 주는 코드와 "지금 선택된 것"을 만드는 코드가 **다른 배열을 읽으면**, | 화면과 선택 불일치, 표시 목록과 조작 대상 분리, selection off-screen, viewOf memberOf, a 전체선택 사고, 보이지 않는 선택 |
| [[distribution-matched-method-wrong]] | 합성물의 **통계 축**(밀도·대비·기하·비율)을 실물에 맞췄는데, **만드는 방식**이 | 분포는 맞고 방식은 틀림, 지표 통과 산출물 가짜, blind 비교, synthetic realism |
| [[downscaled-view-as-evidence]] | 작게 줄인 이미지나 몇 장의 표본은 **판단이 가능해 보인다.** 틀렸다는 신호를 주지 않기 때문이다. | 축소본, 썸네일, 몽타주, 눈검, 해상도, resize, 미리보기로 판단, 표본이 작다 |
| [[duplicated-geometry-implementation]] | 거의 같은 100줄(디코드 → 회색 변환 → 호모그래피 역샘플링)이 두 함수에 복사돼 있는 것. | 좌표 변환 중복, 워프 두 벌, warpQuadToRect, warpQuadToEngineFrame, _warpQuad, photo_preprocessor.dart, _homography |
| [[frozen-now-in-live-query]] | ```dart | 굳은 now, 기간 상한 고정, statsReadingsProvider, watchBetween, StreamProvider, DateTime.now(), providers.dart |
| [[global-transform-on-heterogeneous-input]] | 측정해서 중앙값을 얻은 뒤 **그 값을 전체에 똑같이** 적용하는 것. | 전역 변환, 일률 적용, 중앙값으로 처방, 고정 패딩, CLAHE, 여유, margin, 분포가 넓다, 표준편차가 평균보다 |
| [[guard-threshold-absolute-while-input-widens]] | 자가검사·가드가 **고정 문턱**(절대값)을 쓰는데, 나중에 다른 작업이 **입력 | 고정 문턱 가드, 절대 문턱, 자가검사 무력화, guard threshold, glyph_plane_check |
| [[image-level-split-on-session-corpus]] | 같은 촬영 세션(같은 기기·구도·조명)의 사진이 여러 장 있는 코퍼스를 이미지 단위로 | 이미지 단위 분할, 랜덤 분할 누수, 세션 누수, data leakage, near-duplicate leakage, burst corpus split, 그룹 분할 안 함 |
| [[improvement-parked-outside-the-pipeline]] | 기준선을 보존하려고 개선을 **별도 구현**으로 만드는 것은 옳다. | 곁가지 개선, 병렬 구현, 반영 안 된 개선, A/B 전용 코드, 기본 경로 |
| [[irreversible-write-without-history]] | 원자적 저장(`.tmp` → `rename`)은 **쓰다 만 파일**을 막을 뿐, **틀린 내용으로 온전히 | 이력 없는 덮어쓰기, 원자적 저장의 함정, tmp rename, untracked 라벨, 백업 없는 사람 라벨, 재생 불가 자산 |
| [[label-without-visual-ground-truth]] | 좌표만 저장하고, 저장된 좌표를 **다시 이미지에 그려 확인하는 경로 없이** 계속 진행하는 것. | 눈검증 없는 라벨링, 좌표만 저장, screen_boxes.jsonl, labeled.jsonl, /api/selftest, audit_oob.py |
| [[lighting-dependent-metric-as-content-target]] | 실사진에서 잰 지표가 **화면의 내용이 아니라 촬영 조건**(조도·광원·그림자· | 조명 지표를 내용 목표로, 촬영 변인을 내용으로, 밀도 목표, density target |
| [[measured-result-used-as-input]] | 실물에서 잰 값을 생성기의 **입력 파라미터**로 직접 넣는다. | 결과값을 입력으로, 측정값을 파라미터로, 구조 대신 숫자, result as parameter |
| [[metric-path-not-under-test]] | 측정값이 나쁘면 **측정 대상**(모델·기하·데이터)에 대한 가설만 세우고, **측정하는 코드**(채점 스크립트·전처리 로더·GT 조립)는 옳다고 전제하는 것. | 계측 경로, 채점 스크립트, 평가 스크립트, eval_reader, 지표가 낮다, 모델이 나쁘다, 기준선 저평가, measurement bug, harness bug |
| [[mixed-image-decode-conventions]] | `cv2.imread` 는 EXIF orientation 을 **자동 적용**하고, `PIL.Image.open` 은 **무시**한다. | EXIF 관례 불일치, cv2 vs PIL, exif_transpose, cv2.imread, getexif, orientation, build_cache_v2, golden_bench |
| [[model-invents-what-it-cannot-see]] | 입력에 없는 것을 모델이 **높은 확신으로 만들어낸다.** 그리고 그 값이 그럴듯해서 안전망을 통과한다. | 지어낸다, 환각, hallucination, 안 보이는 자리, 사전분포, prior, 크롭 잘림, CTC, 마지막 자리, 없는 숫자 |
| [[padding-as-content]] | CTC 라벨 배열의 blank(클래스 10)를 필터하지 않고 문자열로 조인해 `"90" + "10"` → `"9010"` 이 된 것. | blank 조인, 패딩 직렬화, greedy_decode, NUM_CLASSES, ctc_reader_v2.py, blank |
| [[partial-update-desyncs-canonical]] | ```dart | 부분 수정, 정본 미갱신, GlucoseRepository.update, valueMgdl, enteredValue, Value.absent, glucose_repository.dart |
| [[poison-row-blocks-pipeline]] | 관용의 단위가 **행이 아니라 배치**인 것. | 독행, 배치 단위 관용, 행 하나가 전체를 막음, ReadingDto.fromJson, _pull, syncOnce, fetchUpdatedSince, reading_dto.dart |
| [[presence-rate-quoted-as-accuracy]] | 파이프라인 단계가 **출력을 냈는지**를 세는 비율과, 그 출력이 **맞았는지**를 | 검출률, 존재율, 출력이 있었나, detection rate, 커버리지를 정확도로, n_ok |
| [[proxy-metric-moves-against-the-goal]] | 최종 지표가 둔감할 때(파인튜닝이 효과를 덮을 때) 중간 단계를 재는 대리 지표를 | 대리 지표, 프록시 지표, pre-only 평가, 합성 val, 지표가 반대로 |
| [[reset-clears-in-flight-lock]] | ```dart | reset 이 잠금을 푸는 것, _busy = false, FrameThrottler, frame_throttler.dart, _busy, reset(), isBusy |
| [[sampled-uniformity-as-proof]] | 묶음이 균일한지 표본으로 확인하는 절차는 **반례를 못 찾았다**는 사실만 만든다. | 표본으로 균일성 확인, 사분위 표본, 거대 성분 점검, 반례 못 찾음, 4표본, spot check as proof |
| [[shared-state-split-by-worktree]] | 작업 보드·클레임·활동 로그는 "어느 브랜치에서 보든 같아야" 하는 값이다. | 워크트리, git worktree, 보드가 갈린다, 칸반 충돌, 공유 상태 |
| [[stale-baseline-quoted-as-current]] | 파이프라인을 갈아엎고 나면 옛 성적은 **다른 모델이 다른 데이터로 다른 시험지를 | 옛 기준선 인용, 폐기된 수치, 기준선 혼동, stale baseline, 재구축 전 수치, 갈아엎기 전 성적, 옛 모델 수치 |
| [[stale-client-writes]] | 브라우저에 어느 버전의 JS 가 떠 있는지 **아무도 모르는 상태**로 저장 요청을 받는 것. | 낡은 탭 쓰기, stale build, Cache-Control, no-store, webtool.html, /api/build |
| [[string-identity-for-label-class]] | 도메인에서 같은 것(같은 annunciator, 같은 표시등)이 **표기 변형** 때문에 문자열로는 | 문자열 동일성, 표기 변형 중복, used_texts, string identity, 라벨 부류 |
| [[tolerance-without-preservation]] | `values.firstWhere(..., orElse: () => SomeDefault)` — 관용처럼 보이지만, 그 값을 나중에 서버로 되돌려 쓰는 순간 **다른 기기의 데이터를 파괴한다.** | 모르는 값 치환, orElse 기본값, silent-normalization, fromWireName, orElse, firstWhere, MeasurementTag, ReadingSource, measurement_tag.dart |
| [[uncontrolled-budget-in-ab-comparison]] | 바꾼 변인(크롭·워프·증강)과 **함께 움직이지 않은 변인**(에폭 수·사전학습 체크포인트· | 예산 불일치 A/B, 에폭 예산, 학습 예산 비교, budget parity, epoch-mismatch, unfair A/B |
| [[unnamed-coordinate-frame]] | 좌표 배열만 저장하고, **그 좌표가 어느 프레임에서 만들어졌는지**는 저장하지 않는 것. | 이름 없는 좌표계, 프레임 미기록, lb.ow, lb.frameId, applyImage, screen_boxes.jsonl, labeled.jsonl |
| [[unpinned-pip-in-frozen-training-env]] | pip 의존성 해결기는 **요구를 만족하는 조합**을 찾을 뿐 **기존 워크로드가 돌아가는 | 고정 환경 pip, 의존성 상승 파손, numpy 2 충돌, TF_bfloat16 TypeError, dependency drift, pip resolver |
| [[verification-record-without-subject]] | `눈검증: glucose_batch1/10 쿼드가 표시 이미지에서 유리 정확히 감쌈` | 무엇을 검증했는지 안 적기, 눈검증 기록, 검증 주어 누락 |
| [[wiki-unreachable-by-identifier]] | 개념어와 산문으로만 쓰인 페이지. | 식별자로 안 걸리는 위키, aliases 누락, FrameThrottler, statsReadingsProvider |

---

## Answers

| 답변 | 설명 | 별칭 |
|------|------|------|

---

## Statistics

- Total concepts: 8
- Total patterns: 15
- Total anti-patterns: 43
- Total answers: 0
- Last updated: 2026-09-13
