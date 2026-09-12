# assets_dev/train 스크립트 지도

폴더에 파이썬 파일이 52개다. **옮기지 않고 여기서 가른다** — 종결 스크립트도
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

## 관련 문서

- 끝난 작업의 판정과 수치: [`docs/DONE.md`](../../docs/DONE.md)
- 재구축 계획의 정본: [`docs/OCR_REBUILD_PLAN.md`](../../docs/OCR_REBUILD_PLAN.md)
- 반입 자산 라이선스: [`docs/LICENSES.md`](../../docs/LICENSES.md)
