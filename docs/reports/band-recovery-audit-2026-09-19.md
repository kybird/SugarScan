# 밴드 검출 복구 감사

사용자 요청: 합성만으로 학습하는 사진용 밴드 검출기의 실촬 오검출과 숫자 잘림을
해결한다. 기존 실시간 카메라 OCR, 저장, 사용자 확인 경로는 변경하지 않는다.
외부 사진/가중치 학습 금지, 사람 라벨 읽기 전용 원칙을 유지한다.

## 확인한 사실과 아직 모르는 것

- 실제 실패 이미지를 열었다. Datumo에는 로고, 배터리 아이콘, 버튼으로 이동한
  예측과 올바른 숫자줄 일부를 자른 예측이 모두 있다. 두 실패는 같은 문제가 아니다.
- Roboflow에는 작은 숫자줄을 LCD/기기 크기로 크게 감싼 예측이 있다. 원본 이미지와
  READING 라벨을 겹쳐 확인했다. 이 현상을 라벨 여백 차이만으로 설명할 수 없다.
- `band_net.py`의 "항상 large" 근거는 Datumo에서 얻었다. 독립 코퍼스에서도
  성립하는지는 별도 검증해야 한다. 입력 크기에서의 짧은 변이 필요한 측정이다.
- 사람 밴드 라벨을 줄여 만든 `digit_cell`은 실제 잉크 정답이 아니다. 기울어진
  외접상자의 역산과 사람의 여백 편차도 있으므로 숫자 판독 성공률로 부르지 않는다.
- `BOX_MARGIN`은 Python 리더 프레이밍 규약이다. 이 감사의 '배포 상자'는 기존
  보고서와 같은 규약의 상자라는 뜻이며, 새 BandNet의 앱 탑재 완료를 뜻하지 않는다.
- 여러 차례 모델 선택에 사용한 실촬 코퍼스는 개발 평가셋이다. 가중치 학습에
  사진을 넣지 않았다는 사실만으로 최종 독립 테스트가 되는 것은 아니다.

## 먼저 바로잡은 증강 경로

`train_band.py --aug`는 기존 체크포인트 학습에는 사용되지 않았다. 아래 결함은
기존 모델 실패의 원인이 아니라, 다음 실험을 오염시킬 결함이다.

1. 이미지 인덱스로 RNG를 매번 초기화해 같은 사진의 기하/광학 선택이 방문마다
   고정됐다. 작업자별로 시드가 설정된 RNG에서 방문별 시드를 뽑도록 바꿨다.
2. 확대 후 캔버스가 숫자줄을 잘라도 원래 라벨을 그대로 회귀했다. 전체 라벨이
   보이는 이동 범위만 사용하며, 불가능하면 원래 기하로 복귀한다. 라벨을 잘라
   '잘린 숫자줄'을 완전한 정답으로 학습시키지도 않는다.
3. 정수로 반올림한 실제 resize 폭/높이 비율을 각 축의 좌표에 적용한다.
4. 잡음도 같은 지역 RNG에서 파생한다. OpenCV 작업자 스레드는 하나로 제한한다.

검증 명령(아래 Python 명령은 모두 `assets_dev/train`에서 실행):

```powershell
$py = 'C:/Users/admin/miniconda3/envs/sugartrain/python.exe'
& $py -m unittest test_band_augmentation -v
```

테스트는 반복 방문의 변화, 시드 재현, 프레임 경계에 가까운 표적의 가시성과
픽셀/라벨 정렬, 증강 비활성 경로 보존을 검사한다.

## 실측: 크기 가정과 해상도 탐침

자: 아래 `measure_panel_stats.py input-scale` 명령. 기준 레터박스 416.
서로 다른 코퍼스의 라벨 규약은 같다고 가정하지 않는다.

| 모집단 | n | GT 짧은 변 최소 / p10 / 중앙 / p90 (px) |
|---|---:|---|
| TB 학습 장 목록 | 15,996 | 20.06 / 48.94 / 92.42 / 159.88 |
| Datumo bg_s0 평가 목록 | 272 | 54.54 / 65.41 / 86.90 / 118.49 |
| Roboflow bg_s0 평가 목록 | 1,273 | 14.41 / 33.53 / 48.49 / 69.64 |

TB에서 짧은 변 32px 미만은 192장이다. Roboflow에서는 106장이고 그보다 큰
32~64px 구간도 979장이다. 이는 '항상 large'를 모든 입력에 적용할 수 없다는
증거다. stride 변경의 충분조건이라는 뜻은 아니다.

동일 `bg_s0.pt`, `conf=0.25`. 실촬 표는 숫자 정답이 아니라 확장 상자가
**각 코퍼스 원래 사람 라벨**을 전부 포함하고 면적비가 2 이하인 비율이다.
baseline은 기존 평가 JSONL을 재집계했다. 640은 이번에 전체 사진으로 재추론했다.

| 모집단 | n | 입력 416 | 입력 640 |
|---|---:|---:|---:|
| Datumo 사람 라벨 게이트 | 272 | 81.99% | 63.24% |
| Roboflow 사람 라벨 게이트 | 1,273 | 13.04% | 37.86% |

별도 합성 게이트: VB 1,000장, `eval_band.py`, `digit_box` 전체 포함 ∧ 원시
면적비 ≤ 1.2. 두 해상도 모두 이번에 재추론했다. **416: 99.10%, 640: 73.20%.**
합성의 가장 큰 배율 333장에서는 면적 상한 없는 숫자 필드 포함도 99.40%와
37.84%였다. 해상도 증가가 모든 배율에 이로운 변경은 아니다.

**판정: 해상도만 올리는 안은 채택하지 않는다.** 작은 실촬의 개선을 얻는 대신
기존 합성과 Datumo가 퇴행한다. 같은 가중치가 입력 배율에 민감하다는 진단이지,
640을 배포하면 해결된다는 증거가 아니다. 단일 시드 탐색 결과이므로 일반화
효과의 통계적 우월성이나 최적 해상도도 주장하지 않는다.

## 진단 실험

해상도 탐침은 재학습 없이 같은 체크포인트와 전체 사진을 쓴다. 정답 상자로
자르지 않는다. 기존 출력과 웹 검수 오버레이를 덮어쓰지 않도록 별도 경로에 쓴다.
실험은 탐색적이며 제품 기본값 변경이나 일반화 성공 선언이 아니다.

```powershell
& $py measure_panel_stats.py input-scale --coco synth_coco/TB/annotations/instances_curve_07998.json
& $py measure_panel_stats.py input-scale --predictions _diag/band_real/bg_s0.jsonl
& $py measure_panel_stats.py input-scale --predictions _diag/band_real/roboflow_bg_s0.jsonl
& $py eval_band_roboflow.py --ckpt band_out/bg/bg_s0.pt --input-size 640 --out-dir _diag/audit
& $py eval_band_real.py --ckpt band_out/bg/bg_s0.pt --input-size 640 --no-overlay --out-dir _diag/audit
& $py eval_band.py --ckpt band_out/bg/bg_s0.pt --data synth_coco/VB --ann instances_train2017.json --manifest synth_coco/VB/manifest.jsonl --input-size 640 --out _diag/audit/synth_bg_s0_size640.jsonl
& $py measure_panel_stats.py input-scale --predictions _diag/audit/roboflow_bg_s0_size640.jsonl
& $py measure_panel_stats.py input-scale --predictions _diag/audit/bg_s0_size640.jsonl
```

`input-scale --size`는 **층화 기준 해상도**다. 비교 시 동일한 416을 써서 같은
사진이 다른 크기 구간으로 이동하지 않게 한다. `deployed_label_gate`는 검출 성공,
확장 상자의 원래 사람 라벨 전체 포함, 면적비 2 이하의 교집합이다. 숫자 칸
역산을 사용하지 않는다. 면적 중앙은 미검출을 포함한 전체 예측으로 계산한다.

## 증강 탐침 실행 규약

기존 TB, 장 목록, 모델 구조, 입력 해상도, 스텝/배치/학습률/점수 타깃을 유지하고
수정한 `--aug`만 켠다. `--grow`, `--under-w`는 함께 켜지 않는다.
시드 하나의 결과는 원인 탐색용이며 정식 채택이나 통계적 우월성의 증거로 쓰지 않는다.
수정 전 미사용 증강의 결함을 기존 bg 모델의 실패 원인으로 소급하지 않는다.

```powershell
& $py -u train_band.py --data synth_coco/TB --train-ann instances_curve_07998.json --out band_out/audit_aug/aug_s0.pt --steps 8000 --batch 32 --width 1.0 --size 416 --score-target bce --seed 0 --aug
```

첫 실행은 로더의 CPU 병목 확인 후 중단했다. OpenCV 작업자 스레드를 제한하고
같은 시드로 처음부터 재시작했다. 미완료 실행을 성적으로 사용하지 않는다.
완료 로그는 `band_out/audit_aug/aug_s0.log`다.

판정 순서: 독립 합성 VB → Datumo 전체 → Roboflow 전체. 합성 실패도 그대로
보고한다. 한 코퍼스 개선과 다른 코퍼스 퇴행이 맞바뀌면 기본값으로 채택하지 않는다.
버튼/로고 오인, 표적 잘림, 너무 큰 상자, 미검출을 분리한다. 기존 숫자 리더까지의
최종 문자열 정확도와 온디바이스 지연은 이 실험으로 검증되지 않는다.

## 증강 탐침 결과 — 완료, 정식 모델 채택은 아님

`aug_s0.pt`는 8,000스텝을 완료했다. 비교 상대는 같은 TB 장 목록, 같은 모델,
같은 시드/스텝/배치의 기존 `bg_s0.pt`다. 외부 사진이나 가중치는 학습하지 않았다.

| 지표 | n | 기존 bg_s0 | 수정 증강 aug_s0 |
|---|---:|---:|---:|
| VB 숫자 필드 포함 ∧ 원시 면적비 ≤ 1.2 | 1,000 | 99.10% | 99.70% |
| Datumo 사람 라벨 포함 ∧ 확장 면적비 ≤ 2 | 272 | 81.99% | 91.91% |
| Roboflow 사람 라벨 포함 ∧ 확장 면적비 ≤ 2 | 1,273 | 13.04% | 38.73% |

위 세 행은 서로 다른 정답/게이트다. 행 사이를 정확도 비교로 읽지 않는다.
이번 비교는 **한 시드의 탐침**이며 통계적으로 확정된 개선량을 주장하지 않는다.
특히 Roboflow의 절대 수준은 아직 낮다. 검출 존재율이 99.84%라고 해서 위치가
정확하거나 숫자를 올바르게 읽는다는 뜻이 아니다.

```powershell
& $py eval_band.py --ckpt band_out/audit_aug/aug_s0.pt --data synth_coco/VB --ann instances_train2017.json --manifest synth_coco/VB/manifest.jsonl --out _diag/audit/synth_aug_s0.jsonl
& $py eval_band_real.py --ckpt band_out/audit_aug/aug_s0.pt --no-overlay --out-dir _diag/audit
& $py eval_band_roboflow.py --ckpt band_out/audit_aug/aug_s0.pt --out-dir _diag/audit
& $py measure_panel_stats.py input-scale --predictions _diag/audit/aug_s0.jsonl
& $py measure_panel_stats.py input-scale --predictions _diag/audit/roboflow_aug_s0.jsonl
```

판정: 증강은 다음 대조 실험에 가져갈 후보다. 두 실촬 평가에서 개선된 표본
결과를 얻었고 합성도 퇴행하지 않았다. 그러나 전체 기기 장면 불일치가 해결됐다는
증거는 아니다. 앱 탑재/기본값 변경/기존 체크포인트 교체는 하지 않았다.
`--grow`, `--under-w`는 여전히 학습하지 않았다.

남은 본 작업은 보드의 **전체 기기 장면 합성을 대조 검증한다**다. LCD 내부를
다시 덕지덕지 수정하기보다 패널 렌더와 전체 장면 조립을 분리한다. 기기 내부의
방해물과 배율을 같이 다루되, 라벨 기하·숫자 가시성·기존 배경 난수 계약을 검증한
뒤 동일 예산으로 대조해야 한다. 재현 시드 확대와 새 실촬 최종 검증도 필요하다.

검증: `flutter analyze` 무경고, `flutter test` 전체 471개 통과,
`python -m unittest test_band_augmentation test_band_input_scale -v` 5개 통과.
`llm-wiki lint --json`은 깨진 링크/메타데이터/근거 위반 없음.
