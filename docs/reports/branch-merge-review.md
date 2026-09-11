# 미병합 브랜치 12개 리뷰·병합 (2026-09-11)

칸반 카드 「앱 코드 미병합 브랜치를 리뷰해 살릴 것만 병합한다」·「학습 도구
미병합 브랜치를 리뷰해 살릴 것만 병합한다」의 결과다. 병합을 전제하지 않고
브랜치마다 살림/보고서만/폐기를 판정했다.

## 판정표

| 브랜치 | 판정 | 근거 |
|---|---|---|
| `glm/G9-locale-overflow` | **살림** | stats_screen 요약 줄바꿈 + 6로케일 하네스. main 에 없음 |
| `glm/G10-accessibility-rest` | **살림** | 화면 3개 + 테스트 3개. main 에 없음 |
| `glm/G11-untranslated-audit` | **살림**(보고서) | 지역화 대상 0건 감사 기록 |
| `glm/G12-l10n-consistency` | **살림** | `test/l10n/arb_consistency_test.dart` 신규 |
| `glm/G13-widget-test-audit` | **살림**(보고서) | 위젯 테스트 함정 전수 감사, 무의미 0건 |
| `glm/G14-untested-screens` | **살림** | 화면 4개 테스트 신규 |
| `glm/G18-failure-stratification` | **살림** | cell_bench 실패 표본 층화 |
| `glm/G19-ink-normalization` | **살림** | segment_rule 잉크 정규화(플래그 뒤, 기본 끔) |
| `glm/G21-antipattern-sweep` | **살림**(보고서) | 안티패턴 전수 점검, 코드 변경 0줄 |
| `glm/cv-band-viability` | **살림** | `diag_cv_band.py` 최종판 + 보고서. 라벨 되돌리기 커밋은 브랜치 안에서 이미 Revert 돼 라벨 파일 변경 0 |
| `glm/G28-tflite-parity` | **폐기** | 아래 참조 |
| `glm/G29-letterbox-warp` | **폐기** | 아래 참조 |

**살림 10 · 폐기 2 · 브랜치 삭제 0**(폐기분도 브랜치는 남긴다).

## 폐기 두 건의 근거

### G28 — tflite 내보내기
보고서 `docs/reports/G28-tflite-parity.md` 가 **이미 main 에 있다**. 결론이
"중단"이고(BiLSTM 이 SELECT_TF_OPS 를 요구, 온디바이스 경로는 ONNX 로 확정),
`docs/DONE.md` 의 G28 절이 그 판단을 담고 있다. 남은 것은 재현 스크립트 2개
(`export_reader_tflite.py`·`diag_tflite_parity.py`)뿐인데, 폐기된 경로의
스크립트를 들이면 살아 있는 도구와 구분이 안 된다 — 이 저장소는 이미 끝난 측정
스크립트가 48개 중 23개다.

### G29 — letterbox 워프 A/B
보고서가 **이미 main 에 있고, 채택분도 이미 반영돼 있다.** 이 브랜치의 두 갈래 중
- **A(채택)**: TTA 시드를 crc32 로 고정 → main 의 `eval_reader.py` 에 있다
  (11·213줄 주석과 `zlib.crc32` 호출 확인).
- **B(기각)**: letterbox 워프 → 완전일치 97.06 → 94.74%, 위험군 0.98 → 3.48%.

남은 미병합분은 **기각된 B안의 코드**(`letterbox_rect`·`frame_crop_letterbox`)와
그 A/B 보조 스크립트다. 이걸 넣으면 기각된 경로가 `build_cache_v2.py`·
`ctc_reader_v2.py`·`eval_reader.py` 세 핵심 파일에 225줄 들어온다. 그 파일들은
그 뒤 G30·G31·장면 성분 재분할로 계속 바뀌었다.

## 문서 충돌 — 세 가지 형태를 각각 다르게 풀었다

아홉 브랜치가 전부 `docs/DONE.md`·`docs/GLM_TASKS.md` 를 고쳐 충돌은 100% 났다.
ours/theirs 로 고르면 끝난 작업이 되살아나거나 완료 기록이 갈린다.

1. **DONE.md — 양쪽이 문서 끝에 새 절을 덧붙임** → 둘 다 보존(HEAD 먼저).
2. **GLM_TASKS.md — 양쪽이 서로 다른 '완료된 작업 절'을 지움** → 양쪽 삭제를
   모두 적용. 한쪽만 고르면 이미 끝난 작업이 목록에 되살아난다.
3. **GLM_TASKS.md 완료 목록 줄** — 한쪽은 G18, 다른 쪽은 G21 을 완료로 올렸다 →
   합쳐서 다시 썼다.

`tools/ocr_bench/bin/cell_bench.dart` 의 도움말도 충돌했는데 G18(층화 설명)과
G19(`--normalize-ink`)가 서로 다른 줄을 더한 것이라 둘 다 남겼다.

## 검증

```text
flutter analyze  → No issues found!
flutter test     → All tests passed! (471건, 병합 전 397건)
diag_cv_band.py --help → 인자 목록 정상 출력(sugartrain 환경)
```

`docs/GLM_TASKS.md` 4절에 남은 작업이 0개가 됐다. `docs/DONE.md` 는 main 의
1~5절 구조와 G28~G32 절을 유지한 채 G9~G21 완료 기록을 흡수했다.
