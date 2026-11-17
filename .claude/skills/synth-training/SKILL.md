---
name: synth-training
description: SugarScan 합성 데이터 생성·검출기/리더 학습·평가 파이프라인 실행. VRAM 기반 배치 최적화 포함.
---

# 합성 학습 파이프라인

## 환경

```bash
PY="C:/Users/kybir/.conda/envs/melotts/python.exe"  # torch 2.3.1+cu121
cd /d/Project/SugarScan/assets_dev/train              # 반드시 여기서
```

**경고**: 백그라운드 셸은 cwd 가 저장소 루트로 리셋된다. 체인 첫 줄에 반드시 `cd` 를 붙인다. `conda run` 은 여러 줄 `-c` 를 못 받는다 — python.exe 를 직접 부른다.

## VRAM 기반 배치 크기 선택

RTX 4070 Ti SUPER (16GB) 실측 (BandNet width=1.5, 416×416, AMP):

| batch | VRAM peak | 권장 VRAM | 스텝 수(같은 샘플) | 속도 |
|-------|-----------|-----------|-------------------|------|
| 32    | 1.0 GB    | 4 GB+     | 6000              | 기준 |
| 64    | 2.0 GB    | 4 GB+     | 3000              | ~1.5× |
| 128   | 4.0 GB    | 6 GB+     | 1500              | ~3×  |
| 256   | 8.0 GB    | 12 GB+    | 750               | ~4×  |

**선택 규칙**: `batch × 32MB ≈ 필요 VRAM`. 여유 VRAM 의 70% 까지.
같은 총 샘플 수를 유지하려면 `steps = 6000 × 32 / batch`.

배치를 바꾸면 lr 도 비례 조정 권장: `lr = 기본lr × batch / 32`.

## 데이터 굽기

```bash
# GEN6 (GEN5 광학축 + 코드화면 30%)
$PY build_synth_coco.py --out synth_coco --sets "" \
    --scene-group TRAIN:8000:SEED1 --scene-group READER:4000:SEED2 \
    --gen6 --plain-p 0.10
$PY build_synth_coco.py --out synth_coco --sets "" \
    --scene-group VAL:800:SEED3 --gen6 --plain-p 0

# 검증
$PY build_synth_coco.py --out synth_coco --sets "" \
    --scene-group TRAIN:8000:SEED1 --scene-group READER:4000:SEED2 \
    --scene-group VAL:800:SEED3 --verify
```

- `--gen5`: roll ±45° + 저대비 그레인 + 주름글레어 0.15
- `--gen6`: `--gen5` + 코드화면 30%
- `--plain-p 0`: 검증 세트에만 (단색 프레임 교차충돌 방지)
- 시드가 정본 — 매 라운드 새 시드

## 검출기 학습

```bash
# 기준선 (양성만)
$PY train_band.py --data synth_coco/TRAIN --out band_out/det_base.pt \
    --width 1.5 --grow 0.06 --aug --steps 6000 --batch 32 --seed SEED

# 거절 학습 (음성 25% 별도 부분 — 양성 batch + 음성 round(batch*0.25))
$PY train_band.py --data synth_coco/TRAIN --out band_out/det_neg.pt \
    --width 1.5 --grow 0.06 --aug --steps 6000 --batch 32 --seed SEED \
    --neg-ratio 0.25
```

- `--width 1.5` = 배포 구조(1.12M 파라미터)
- `--neg-ratio 0.25`: 배치 32 + 음성 8 = 40장. 배치 내 비중 20%.
- 짝 실험: 같은 시드·설정, `--neg-ratio` 만 차이

**속도 최적화** (VRAM ≥ 6GB):
```bash
--batch 128 --steps 1500 --lr 8e-3  # 3배 빠름, 같은 샘플 수
```

## 리더 학습

**속도 최적화**: 리더(CRNN)는 모델이 작아(2.3M·144×96) GPU 병목이 아니라
**DataLoader num_workers=0**(싱글스레드)가 병목이다. VRAM 4.2GB/16GB
수준이 정상. 다음 라운드부터 `reader_crnn.py` 의 DataLoader 에
`num_workers=8` 추가 예정.

```bash
# 크롭 추출 (검출기 제안 상자)
$PY infer_bandnet_crops.py --set synth_coco/READER \
    --ckpt band_out/det_neg.pt --out band_out/crops.jsonl

# 크롭 파일 분리
$PY -c "
import json
from pathlib import Path
rows = [json.loads(l) for l in open('band_out/crops.jsonl')]
pos = [r for r in rows if r['kind']=='pos' and r['pred']]
neg = [r for r in rows if r['kind']=='neg' and r['pred']]
Path('band_out/crops_pos.jsonl').write_text(
    chr(10).join(json.dumps(r) for r in pos))
Path('band_out/crops_mix.jsonl').write_text(
    chr(10).join(json.dumps(r) for r in pos+neg))
"

# 학습 (빈타깃 포함)
$PY reader_crnn.py train --set synth_coco/READER \
    --boxes band_out/crops_mix.jsonl --aug --epochs 30 --batch 32 \
    --out reader_out/rdr_neg
```

- 양성 크롭 = 검출기가 제안한 상자 + 정답 라벨
- 음성 크롭 = 검출기 오검출 상자 + 빈 라벨 (길이 0 CTC 타깃)

## 평가

```bash
# 실사진 재판 (DC238)
$PY eval_real_judge.py --detector band_out/det_neg.pt \
    --reader reader_out/rdr_neg/best.pt --name "조합명" \
    --out /d/Project/SugarScan/docs/reports/report.md

# 합성 VAL
$PY eval_reject_stages.py --set synth_coco/VAL \
    --detector band_out/det_neg.pt --reader reader_out/rdr_neg/best.pt \
    --name "조합명"
```

## 알려진 함정

1. **cwd 리셋**: 백그라운드 체인은 루트에서 시작 — `cd` 필수
2. **--out 상대경로**: `../docs/` 는 assets_dev/docs 에 떨어짐 — 절대경로 쓸 것
3. **conda run**: 여러 줄 `-c` 불가 — python.exe 직접 호출
4. **동시 학습 금지**: GPU 하나 — 검출기와 리더 동시 학습하면 OOM
5. **persistence_workers**: batch 변경 시 DataLoader 재생성 필요
6. **짝 실험 원칙**: 같은 시드·설정·배치·스텝, 축 하나만 변경
