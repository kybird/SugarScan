# 균등값 합성 재학습 실행 기록

사용자 요청(2026-10-31): 생성 진행 후 학습 시작.
기준 HEAD: `d5518ee66d16f9f1e610bf09981d64d68ed9f658`.

## 범위

실기기 카메라 `233→1xx` 보고에 대응한 `sample_value` 값당 균등 30~599를
새 코퍼스에 반영한다. 합성만으로 학습한다. 앱 번들 교체는 범위에 없다.
기존 GEN3와 같은 학습 예산을 사용하되 새 시드와 계획 모드이므로
값 분포 하나만 바꾼 엄밀한 짝비교라고 주장하지 않는다.

## 실행

PowerShell, 저장소 루트에서:

```powershell
& C:\Users\admin\miniconda3\envs\sugartrain\python.exe -u assets_dev/train/run_uniform_training.py
```

실행기는 계획 생성 → 30,000장 렌더 → 무결성 검사·COCO 변환 → 검출기 학습
→ 검출 예측 상자 → 리더 학습 → 실촬 끝단 평가를 순서대로 수행한다.
실패하면 다음 단계로 넘어가지 않는다.

| 설정 | 값 |
|---|---|
| 코퍼스 | `assets_dev/train/synth_coco/UNIFORM_20261031` |
| 계획 | 새 시드 20261031, bg=flat, scene=panel |
| 검출기 | from scratch, 640, width 1.5, batch 32, lr 0.002, 16,000 steps |
| 리더 | from scratch, batch 32, lr 0.001, 150 epochs |
| 리더 상자 | 새 검출기 step8000의 예측 |
| 검출기 출력 | `assets_dev/train/band_out/tone/uniform_20261031*` |
| 리더 출력 | `assets_dev/train/reader_out/uniform_20261031` |
| 실행 상태·로그 | `assets_dev/train/_diag/uniform_20261031` |

## 판정의 한계

생성과 학습은 실행 작업이며 정확도 개선의 증거가 아니다. 리더 학습셋 완전일치는
일반화 성능으로 인용하지 않는다. 실촬 끝단 평가는 정지 사진 검사이며,
실기기 라이브 카메라에서 첫 자리 오독이 해결됐는지는 별도로 확인해야 한다.

진행 여부와 실패는 실행기의 `status.json` 및 단계별 로그를 정본으로 확인한다.

2026-10-31 19:27 KST 백그라운드 실행 시작. 실행기 PID 44296,
생성 자식 PID 71304. 초기 상태는 `01_generation/running`이다.
생성 계획 검사는 통과했으며 실제 렌더와 이후 학습·평가는 진행 중이다.
확인 명령: `Get-Content assets_dev/train/_diag/uniform_20261031/status.json`.

## 생성 경고 확인 (2026-10-31)

`RuntimeWarning: All-NaN slice encountered`는 `_gpc_bg_contrast`의
`np.nanmedian(glass)`에서 발생한다. 유리에서 밴드 bbox를 마스킹한 뒤
유효 배경 화소가 없어지는 경우다. 바로 다음 줄에 전체 이미지 중앙값
폴백이 있어 진단 점수는 유한한 값으로 기록된다. 이 경로는 진단 점수만
계산하고 이미지·라벨을 변경하지 않는다.

재현 명령:

```powershell
& C:\Users\admin\miniconda3\envs\sugartrain\python.exe assets_dev/train/audit_uniform_warning.py
```

산출물: `assets_dev/train/_diag/uniform_20261031/warning_audit.json`.
로그의 경고 구간을 재생해 `panel_20261031_5908`에서 같은 경고와 스택을
확인했다. 재현 이미지와 저장 이미지의 픽셀 및 라벨이 일치하고,
매니페스트 전체에 비유한 glyph_plane_check 값이 없음을 확인했다.
이 확인은 진단 경고의 영향 범위를 뜻하며, 인식 정확도 통과를 뜻하지 않는다.

생성·COCO 검사는 완료됐고 검출기 학습도 종료됐다. 사용자 후속 요청 시점에는
리더 학습이 이미 자동 시작된 상태였다(21:15 KST). 경고 확인 후 계속 진행한다.
생성기 수정은 하지 않았으며 기존 실행의 소스 해시를 유지한다.

## 리더 로딩 최적화 (2026-10-31)

사용자 요청으로 배치 32·150에폭을 유지하고 결정적 크롭만 RAM에 캐시한다.
`reader_crnn.py --cache-crops ram`은 기존 __getitem__ 입력을 그대로 저장하며,
지터/증강이 켜져 있으면 거부한다. 평가도 같은 캐시 데이터셋을 읽는다.

검사 명령(저장소 루트):

```powershell
& C:\Users\admin\miniconda3\envs\sugartrain\python.exe assets_dev/train/benchmark_reader_cache.py --set assets_dev/train/synth_coco/UNIFORM_20261031 --boxes assets_dev/train/_diag/uniform_20261031/reader_boxes.jsonl --count 512 --out assets_dev/train/_diag/uniform_20261031/cache_benchmark.json
```

산출물의 `exact_inputs`와 `rng_unchanged`로 입력·라벨·길이 및 캐시 생성의
난수 상태 보존을 확인한다. 시간 수치는 CPU 로딩 검사이며 학습 전체 속도가 아니다.

15에폭 체크포인트의 모델·optimizer·scheduler를 복원해 16~150에폭을 재개한다.
기존 체크포인트에 RNG 상태가 없어 이후 셔플·드롭아웃 순서의 완전 재현은
불가능하다. 이후 체크포인트는 RNG 상태도 저장한다. 기존 best.pt는 별도
`best_before_cache.pt`로 백업했고, 기존 최고 정확도 하한을 전달해 더 나쁜
체크포인트로 best를 덮어쓰지 않도록 했다. 중단 당시 미저장 16에폭만 다시 계산한다.

원래 config.json과 provenance.json은 보존한다. 의도적 실행 변경과 소스 해시는
`continuation.json`에 별도로 기록한다. 원래 실행기로 재시작하면 소스 해시
불일치로 거절되므로 아래 재개 명령을 사용한다.

```powershell
& C:\Users\admin\miniconda3\envs\sugartrain\python.exe -u assets_dev/train/resume_uniform_cached.py --resume assets_dev/train/reader_out/uniform_20261031/ep15.pt
```

2026-10-31 22:18 KST 재개 감독 프로세스 PID 41916, 리더 PID 42792.
로그: `assets_dev/train/_diag/uniform_20261031/06_reader_cached.log`.
검증: Python 구문 검사, 입력 동일성 벤치마크, git diff --check.
Flutter 코드 변경이 없어 Flutter 분석·전체 테스트는 이번 최적화에서 실행하지 않았다.
