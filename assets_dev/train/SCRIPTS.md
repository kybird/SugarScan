# assets_dev/train 스크립트 지도

폴더에 파이썬 파일이 **111개**다(2026-09-17 실측: `ls *.py | wc -l`).
아래 「현역 20 / 종결 32」 표는 52개 시점의 것이다. 그 뒤에 늘어난 58개는
맨 아래 두 절에 적었다 — 2026-09-13~16 분(43개)과 2026-09-17 추가분(16개).
**세 절을 합쳐야 지금 풀을 덮는다.**

**옮기지 않고 여기서 가른다** — 종결 스크립트도
형제 모듈(`build_cache_v2`·`eval_reader` 등)을 import 하므로 하위 폴더로 내리면
실행이 깨진다. 재현성이 이 저장소의 자산이라 그걸 깨지 않는다.

판정 기준: **지금 열려 있는 작업이 부르는가.** 종결이라고 해서 틀린 코드가
아니라, 그 질문이 이미 답을 얻었다는 뜻이다. 근거가 생기면 다시 연다.

## 현역 (20)

| 파일 | 마지막 커밋 | 무엇 |
|---|---|---|
| `audit_split_leakage.py` | 2026-09-10 | dhash 누수 감사. build_grouped_split 이 import 한다 |
| `build_cache_v2.py` | 2026-09-09 | 학습 캐시 data_cache_v2.npz 생성. gmscreen_quads.jsonl 을 읽는다 |
| `build_device_balance_split.py` | 2026-09-11 | 기기 편중 A/B 캐시 빌더 |
| `build_device_split.py` | 2026-09-11 | 기기 단절 분할(시드 20260911) — 검출기·리더 공통 분할의 정본 |
| `build_gmft_dataset.py` | 2026-09-03 | GM 검출기 파인튜닝용 COCO 데이터셋 빌더 — 우리 라벨로 재학습할 때 쓴다 |
| `build_grouped_split.py` | 2026-09-10 | 장면(dhash) 무결 분할 |
| `convert_quads_oriented.py` | 2026-09-02 | 검출 쿼드를 라벨러 힌트 파일로 복사 |
| `ctc_reader_v2.py` | 2026-09-09 | CTC 리더 학습(pre=합성 40 / ft=실사진 60) |
| `detect_datumo_gm.py` | 2026-09-05 | YOLOX GM 검출 추론. 전처리 불일치 카드의 대상 |
| `device_ab_report.py` | 2026-09-11 | 짝비교(McNemar 정확 이항) |
| `device_eval_report.py` | 2026-09-11 | 네 층 + 기기별 집계 |
| `diag_cv_band.py` | 2026-09-09 | 고전 CV 밴드 파인더 — 제안기 폴백 후보(다담음 95.6%) |
| `eval_reader.py` | 2026-09-09 | 리더 평가 — TTA(crc32) 프로토콜의 정본 |
| `export_reader_onnx.py` | 2026-09-10 | 리더 ONNX 내보내기 |
| `make_band_pilot.py` | 2026-09-04 | 밴드 라벨링 큐 빌더 |
| `make_failure_atlas.py` | 2026-09-09 | 실패 아틀라스 서버(8790) — 웹툴 아틀라스 탭이 중계한다 |
| `make_label_audit_queue.py` | 2026-09-09 | 라벨 감사 큐 빌더 |
| `make_wide_band_queue.py` | 2026-09-08 | 가로형 밴드 큐 빌더 — 가로 기기 작업이 열려 있다 |
| `synth_lcd.py` | 2026-09-05 | 합성 화면 생성기 — 앞으로 대대적으로 손댈 대상 |
| `webtool.py` | 2026-09-11 | 라벨러·모니터·기종·아틀라스·훈련 서버(8777). 사람이 쓰는 유일한 UI |

## 종결 (32) — 지우지 않는다, 재현물이다

| 파일 | 마지막 커밋 | 결과 |
|---|---|---|
| `audit_dot_unit_coverage.py` | 2026-09-10 | 소수점·단위 표본 조사. 완료 — 소수점 0건 |
| `audit_oob.py` | 2026-09-02 | 박스 범위 감사. 완료 |
| `bench_external_ocr.py` | 2026-09-05 | 외부 OCR 벤치. 완료 — EasyOCR 크롭 9.3% / 원본 1.3% vs 자체 98.0% |
| `diag_autoband.py` | 2026-09-04 | 밴드 자동 검출 진단. 종결 |
| `diag_clahe.py` | 2026-09-05 | CLAHE 효과. 기각 — 흐린 획을 죽인다 |
| `diag_confidence_sweep.py` | 2026-09-04 | 거절 임계 스윕. 누수 분할 기준이라 재스윕 필요 |
| `diag_cv_band2.py` | 2026-09-08 | CV 파인더 2판. 종결(3판이 대체) |
| `diag_cv_band3.py` | 2026-09-09 | CV 파인더 3판. diag_cv_band.py 로 재작성됨 |
| `diag_digit_pos.py` | 2026-09-05 | 자릿수 위치 진단. 종결 |
| `diag_edge_ablation.py` | 2026-09-04 | 에지 제거 실험. 종결 |
| `diag_gt_review.py` | 2026-09-04 | GT 검토. 종결 |
| `diag_pad_sweep.py` | 2026-09-04 | 크롭 여백 스윕. 종결 |
| `diag_timestep.py` | 2026-09-04 | CTC 타임스텝 진단. G29 의 근거 |
| `diag_tta_combined.py` | 2026-09-05 | TTA 조합. 종결 |
| `diag_tta_gate.py` | 2026-09-04 | TTA 게이트. 종결 |
| `diag_tta_vote.py` | 2026-09-05 | TTA 득표. 종결 — 현행 0.778 임계의 출처 |
| `diag_wide_gm.py` | 2026-09-05 | 가로형 GM 진단(G32). 재기만 — 판정 없음 |
| `eval_lcd_fix.py` | 2026-09-04 | LCD 재라벨 효과 측정. 완료 |
| `g30_ab_report.py` | 2026-09-09 | G30 밴드 크롭 A/B. 기각(예산 불일치 -> G31) |
| `g30_check_cache.py` | 2026-09-09 | G30 캐시 검증. 종결 |
| `g30_ft_nojit.py` | 2026-09-09 | G30 파인튜닝. 종결 |
| `g31_ft_e60.py` | 2026-09-09 | G31 예산 맞춘 재측정. 기각 확정(위험군 0.98->3.48%) |
| `g34_components.py` | 2026-09-10 | G34 기기 태깅 성분. 완료 — 기기 라벨 2,494장 확보 |
| `g34_sheets.py` | 2026-09-10 | G34 시트 생성. 완료 |
| `g34_tags_aggregate.py` | 2026-09-10 | G34 태그 집계. 완료 |
| `g34_verify_strips.py` | 2026-09-10 | G34 검증 스트립. 완료 |
| `make_lcd_fix_queue.py` | 2026-09-04 | LCD 재라벨 큐. 완료 |
| `make_wide_survey.py` | 2026-09-04 | 가로 화면 전수 조사. 완료 — 비중 2.0%(51/2512) |
| `premerge_components.py` | 2026-09-10 | 성분 병합 전 조사. 완료 |
| `repair_prevframe_labels.py` | 2026-09-02 | 좌표 프레임 복구(1회성). 완료 |
| `repair_unrotated_band_labels.py` | 2026-09-02 | 회전 라벨 복구(1회성). 완료 |
| `tally_wide_survey.py` | 2026-09-04 | 가로 조사 집계. 완료 |

## 2026-09-13~16 분류 (43) — 2026-09-17 감사

52개 시점 이후·어젯밤 이전에 늘어난 것들이다. 가른 **규칙을 먼저 적는다**:

- **현역** — 셋 중 하나라도 참이면 현역이다.
  ① 다른 파이썬 파일이 import 한다  ② 열린 카드·위키·`OCR_REBUILD_PLAN` 이
  이름을 댄다  ③ 코드가 이름으로 부른다(`webtool.py` 의 서브프로세스 포함)
  또는 그 산출 파일을 살아 있는 코드가 읽는다.
- **종결** — 셋 다 거짓이고 답한 물음이 닫혔다.

③ 을 안 봤으면 다섯 개를 죽은 것으로 잘못 적을 뻔했다 — `band_det_sweep` ·
`make_band_slot_queue` · `make_wide_review_queue` · `predict_band_quads` 는
`webtool.py` 가 부르고, `make_real_baseline` 은 `real_baseline.json` 을 네
스크립트가 읽는다. **import 만 보면 놓친다.**

### 현역 (35)

| 파일 | 무엇 | 왜 현역인가 |
|---|---|---|
| `synth_panel.py` | 물리 패널 합성 렌더러 2판 — 합성의 정본 | import 10 · 카드 3 · 위키 5 |
| `synth_profiles.py` | 기기 프로파일(12종)과 글리프 | import 6 · 카드 2 |
| `synth_overrides.py` | 프로파일 덮어쓰기 — 웹툴 에디터 저장소 | import 1 |
| `synth_schema.py` | 프로파일 값의 모양과 뜻 — 에디터 위젯 근거 | 위키 2 |
| `synth_check.py` | 합성 코퍼스 불변식 검사 — 리팩토링 안전망 | 위키 1 |
| `validate_synth_panel.py` | 합성 검증 자(AC 판정) | import 1 · 위키 1 |
| `lcd_layout.py` | LCD 레이아웃 모델 — 영역이 면을 빈틈없이 나눈다 | import 2 · 위키 1 |
| `test_lcd_layout.py` | lcd_layout 계약 시험 | 위키 1 · CLAUDE.md 가 지목 |
| `gm_quads.py` | GM 화면 쿼드의 **단일 출처**(사람 라벨 우선) | **import 17** — 가장 많이 불린다 |
| `band_exclusions.py` | 밴드 라벨에서 뺄 장 — 사람 선언의 단일 출처 | import 8 · 카드 1 · 위키 2 |
| `measure_panel_stats.py` | 실측 기준선 자(종횡비·밴드·엣지 밀도) | import 6 · 위키 2 |
| `measure_polarity.py` | 극성·자릿수 실측 자 | import 5 · 카드 1 |
| `make_real_baseline.py` | `real_baseline.json` 정본 생성기 | 산출을 네 스크립트가 읽는다 |
| `diag_polarity_bg.py` | 극성 자의 배경 기준을 기기별로 연다 | import 2 |
| `score_polarity_defs.py` | 극성 정의 셋을 사람 정답에 대조 | 위키 1 |
| `diag_density_where.py` | 밴드 밖 밀도가 어디서 오는가(링/안쪽) | import 1 |
| `diag_gpc_threshold.py` | 글리프 평면 잉크 문턱의 자 | `synth_panel` 이 재현용으로 지목 |
| `train_band_detector.py` | 밴드 쿼드 검출기 v0 학습 | import 7 |
| `eval_band_detector.py` | v0 게이트 평가(사람 밴드 라벨) | import 7 · **카드 3** |
| `band_det_clip_split.py` | 「크롭이 밴드를 잘랐나」로 가른다 | import 1 · 카드 1 |
| `band_det_synth_gap.py` | 훈련 부족인가 합성이 다른가 | 카드 1 |
| `band_det_corner_error.py` | 모서리를 얼마나 정확히 찍는가 | 위키 1 |
| `band_det_orient_split.py` | 게이트 결과를 세로/가로로 가른다 | 위키 1 |
| `band_det_tilt_real.py` | 기울기 예산(합성·모델·게이트) | 위키 1 |
| `band_det_sweep.py` | 합성 양 스윕 — 굽고·학습하고·게이트로 잰다 | `webtool.py` 가 부른다 |
| `predict_band_quads.py` | 검출기 예측을 웹툴 오버레이 규약으로 | `webtool.py` 가 부른다 |
| `build_profiled_cache.py` | 리더 합성 팔을 캐시로 굽는다 | 카드 1 · 위키 1 |
| `device_layout_stats.py` | 기기별 고정 레이아웃 실측 | `synth_profiles` 가 산출을 붙인다 |
| `device_orient_stats.py` | 기기별 세로/가로 확정 | 카드 1 |
| `band_label_slot_audit.py` | 밴드 라벨이 빈 앞자리를 포함했는가 | 카드 1 · 위키 1 |
| `band_queue.py` | 밴드 라벨링 큐와 진행 계측(verify·build·progress). 라벨 파일은 읽기만 한다 | `webtool.py`·`make_wide_band_queue` 가 부른다 · 카드 1 |
| `make_band_slot_queue.py` | 빈 앞자리 누락 교정 큐 | `webtool.py` 가 부른다 |
| `make_wide_review_queue.py` | 가로형 밴드 라벨 전수 검토 큐 | `webtool.py` 가 부른다 |
| `make_unit_gap_sheet.py` | 단위 간격 — 실기기 vs 합성 대조 시트 | 위키가 방법론으로 인용 |
| `synth_vs_real_sheet.py` | 합성과 실사진을 눈으로 견주는 시트 | 위키 1 |

### 종결 (8) — 지우지 않는다, 재현물이다

| 파일 | 물음이 어떻게 닫혔나 |
|---|---|
| `eval_generator_baseline.py` | 옛 리더(pre 체크포인트)와 옛 홀드아웃 1,138장을 전제한다. 둘 다 2026-09-11 scratch 재구축에서 폐기 |
| `device_digit_stats.py` | 기기별 숫자 높이를 쟀고 값이 `synth_profiles` 에 박혔다 |
| `make_polarity_gt_sheet.py` | 극성 정답 시트를 만들었고 정의는 `score_polarity_defs` 로 확정됐다 |
| `band_det_compare_sheet.py` | 두 검출기 예측 비교(2026-09-14 heat 구조 판정용). 그 판정 끝 |
| `band_det_heatmap_sheet.py` | heat 중간 단계 시각화. 같은 판정의 부속 |
| `band_det_worst_sheet.py` | v0 실패를 층별로 본 판 |
| `band_det_unlabeled_check.py` | 라벨 없는 장의 예측을 같은 기기 라벨 장과 대조 |
| `atlas_synth_vs_real.py` | 합성 대 실사진 차이 아틀라스. 카드 종료 |

> 종결 넷(`band_det_compare_sheet` · `heatmap_sheet` · `worst_sheet` ·
> `unlabeled_check`)은 **기울어진 쿼드를 내는 v0** 를 전제한다. 2026-09-16 에
> 검출기 출력을 축정렬 상자로 바꾸기로 하면서 그 전제가 사라졌다. 축정렬
> 검출기에 같은 질문을 하려면 새로 짜는 것이 맞다 — 되살려 고치지 마라.

## 2026-09-17 추가 (16) — 어느 물음에 답하는가로 찾는다

무인 루프 한 밤에 늘어난 것들이다. **"무엇을 재고 싶은가"로 고르라** — 이름이
비슷한 것이 여럿이라 파일명만으로는 안 갈린다.

### 합성 코퍼스를 굽고 내보낸다
| 파일 | 무엇 |
|---|---|
| `build_synth_coco.py` | synth_panel 코퍼스를 YOLOX COCO 로. 세트 A/B/C, 시드 다름. `--verify` 가 같은 파일 안의 자 |
| `prep_synth_yolox.py` | 세트 A 를 train/val 로 가른다(YOLOX 가 학습 중 mAP 를 재려면 필요) |

### 검출기 — 학습과 추론
| 파일 | 무엇 |
|---|---|
| `yolox_synthband_exp.py` | 합성 밴드 검출기 exp. **저장소 안에 둔 이유는 런을 재현하려고** |
| `infer_synthband.py` | 합성 밴드 검출기 추론. 전처리는 YOLOX ValTransform 을 그대로 부른다 |
| `synthband_box_error.py` | 예측 상자의 오차 분포. **밴드 포함률과 숫자 필드 포함률을 가른다**(정답 밴드는 여백을 미리 뗀다) |
| `migrate_ckpt_numpy1.py` | numpy 2.x 로 절인 옛 체크포인트를 지금 환경에서 열리게 다시 절인다 |

### GM 검출 진단 — **셋이 층위가 다르다. 헷갈리기 쉬운 자리**
| 파일 | 답하는 물음 | 범위 |
|---|---|---|
| `gm_preproc_ab.py` | "어느 전처리가 나은가" | 전량 · 팔 여러 개 · 사람 라벨 IoU. `--paired` 는 승·패·무, `--wide-detail` 은 가로 층 |
| `diag_gm_candidate_tie.py` | "이 장에서 왜 상자가 흔들렸나" | **장 단위** · 후보 점수와 상자를 직접 덤프 · 1·2위 점수차와 넓이비 |
| `diag_ft3_miss5.py` | "ft3 가 놓친 그 5장은 임계 탈락인가 후보 부재인가" | 그 5장 고정 · 몽타주 + 모집단 대조 |

> 후보 뽑기(모델 적재·전처리·postprocess)는 `diag_gm_candidate_tie` 의
> `load_model()` · `candidates()` **하나뿐**이고 `diag_ft3_miss5` 가 그것을
> 부른다. 2026-09-17 에 두 파일이 각자 짜 놓은 것을 합쳤다. 새 진단을 만들 때도
> 그 둘을 부르고 추론 경로를 다시 짜지 마라.

### 합성 품질 — 재는 자
| 파일 | 무엇 |
|---|---|
| `check_margin_policy.py` | 여백 정책의 **선언값 대 출력값**. 분모는 layout 선언이 없는 프로파일뿐 |
| `diag_gpc_resolution.py` | 글리프 평면 가드의 **분해능** — 일부러 8px 어긋뜨려 점수가 떨어지는지 본다. 통과율로는 가드 건강을 알 수 없다 |
| `test_report_drops.py` | `validate_synth_panel.report_drops` 의 시험. 드롭이 0 이면 그 인쇄 경로가 안 돌아서 붙였다 |

### 실사진을 **보는** 판 (재는 자가 아니다)
| 파일 | 무엇 |
|---|---|
| `survey_real_glare.py` | 반사가 뚜렷한 장을 골라 대지로 묶는다. 자는 순위만 매기고 **유형 판정은 사람이 한다** |
| `make_glyph_compare_sheet.py` | 실사진 vs 합성 글리프를 자릿수별로 나란히·겹쳐 놓는다. 숫자를 내지 않는 것이 의도다 |

### 리더 · 분할
| 파일 | 무엇 |
|---|---|
| `reader_crnn.py` | torch CRNN+CTC 리더. `overfit`(구현 확인) · `train` · `eval` · `measure`(상수 근거) |
| `build_band_device_split.py` | 밴드 라벨 코퍼스의 기기 단절 분할. 규칙은 `build_device_split` 에서 import 한다 |

## 관련 문서

- 끝난 작업의 판정과 수치: [`docs/DONE.md`](../../docs/DONE.md)
- 재구축 계획의 정본: [`docs/OCR_REBUILD_PLAN.md`](../../docs/OCR_REBUILD_PLAN.md)
- 반입 자산 라이선스: [`docs/LICENSES.md`](../../docs/LICENSES.md)
