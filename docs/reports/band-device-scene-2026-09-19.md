# 전체 기기 장면 합성 대조

2026-09-19, 사용자 추가 개선 요청에 따른 Codex 탐색 실험. 정식 모델 채택과
앱 탑재를 뜻하지 않는다. 기존 증강 탐침은 `band-recovery-audit-2026-09-19.md`.

## 실행 전 규약

가설: LCD 주변 크롭만 그리던 합성에는 기기 내부 버튼·몸체와 작은 LCD가 함께
나오는 장면이 부족하다. 자체 작성한 `device_scene.py`가 카메라 워프 전에
일반적인 플라스틱 몸체와 버튼을 조립한다. 외부 사진·데이터·가중치는 학습에
넣지 않는다. 실물의 정확한 복제품이나 실측 분포라고 주장하지 않는다.

- 장면용 RNG는 기존 렌더·카메라·배경 RNG와 분리한다.
- `mixed`는 확률 0.7로 전체 기기, 나머지는 기존 패널이다. 기본 렌더는 여전히 panel.
- 전체 기기 조립 후 긴 변을 기존 896픽셀에 맞추고 모든 좌표/마스크를 함께 변환한다.
- 같은 시드와 파일명 목록을 유지한다. 기존 TB의 15,996장에 대응하는 목록이다.
  좌표 자체는 새 장면에서 달라진다. 배경만 비교했던 T/TB와 다른 실험이다.
- **몸체 문맥과 표적 상대 배율이 함께 바뀐다.** 몸체 단독의 인과 효과를 분리하지 않는다.
- 대조는 `aug_s0.pt`. 모델/입력 416/폭 1/8,000스텝/배치32/lr 0.002/BCE/
  seed0/`--aug`를 유지한다. `--grow`, `--under-w`를 함께 켜지 않는다.
- 검증은 기존 VB와 새 혼합 Val을 모두 평가하고 장면별/프로파일별 결과를 본다.
  이어 Datumo와 Roboflow의 전체 사진을 기존 평가기로 읽는다. 정답 크롭은 쓰지 않는다.
- 실촬의 주 비교값은 기존 `input-scale`의 `deployed_label_gate`다:
  검출 성공 + BOX_MARGIN 적용 상자가 원래 사람 밴드 라벨 포함 + 면적비 ≤ 2.
  숫자 문자열 정확도가 아니다. 잘림·위치 이탈·과대 상자·미검출도 분리한다.
- 두 실촬 코퍼스와 기존 합성의 퇴행을 숨기지 않는다. 단일 시드 탐색이므로
  유의성이나 최종 일반화 성공을 주장하지 않는다. 반복 조회한 실촬은 개발 평가다.

## 재현 명령

아래는 `assets_dev/train`에서 실행한다. 출력이 존재하면 새 생성기는 거부한다.

```powershell
$py = 'C:/Users/admin/miniconda3/envs/sugartrain/python.exe'
& $py -m unittest test_device_scene test_band_augmentation test_band_input_scale -v
& $py -u build_device_coco.py --name Train --count 16000 --seed 20261001 --reference-ann synth_coco/TB/annotations/instances_curve_07998.json
& $py -u build_device_coco.py --name Val --count 1000 --seed 20261002
& $py -u train_band.py --data synth_device_fit/Train --train-ann instances_matched.json --out band_out/device_scene/device_s0.pt --steps 8000 --batch 32 --width 1.0 --size 416 --score-target bce --seed 0 --aug
& $py eval_band.py --ckpt band_out/audit_aug/aug_s0.pt --data synth_device_fit/Val --ann instances_train2017.json --manifest synth_device_fit/Val/manifest.jsonl --out _diag/device_scene/newval_aug_s0.jsonl
& $py eval_band.py --ckpt band_out/device_scene/device_s0.pt --data synth_device_fit/Val --ann instances_train2017.json --manifest synth_device_fit/Val/manifest.jsonl --out _diag/device_scene/newval_device_s0.jsonl
& $py eval_band.py --ckpt band_out/device_scene/device_s0.pt --data synth_coco/VB --ann instances_train2017.json --manifest synth_coco/VB/manifest.jsonl --out _diag/device_scene/oldval_device_s0.jsonl
& $py eval_band_real.py --ckpt band_out/device_scene/device_s0.pt --no-overlay --out-dir _diag/device_scene
& $py eval_band_roboflow.py --ckpt band_out/device_scene/device_s0.pt --out-dir _diag/device_scene
& $py measure_panel_stats.py input-scale --predictions _diag/audit/aug_s0.jsonl
& $py measure_panel_stats.py input-scale --predictions _diag/device_scene/device_s0.jsonl
& $py measure_panel_stats.py input-scale --predictions _diag/audit/roboflow_aug_s0.jsonl
& $py measure_panel_stats.py input-scale --predictions _diag/device_scene/roboflow_device_s0.jsonl
& $py measure_panel_stats.py input-scale --coco synth_device_fit/Train/annotations/instances_matched.json
```

`synth_device_v1`과 `synth_device_v2`는 좌표 메타데이터와 렌더 해상도 예산을
바로잡기 전에 중단한 생성 시도다. 학습·성적으로 사용하지 않는다.
최종 생성 로그는 `synth_device_fit/build_train.log`, `build_val.log`다.
