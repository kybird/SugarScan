#!/bin/sh
# 단계 1 — 점수 감독 3조건 x 3시드. 계획은 docs/BAND_EXP_PLAN.md 다.
#
# 바뀌는 것은 --score-target 하나뿐이다. 모델·입력·배치·스텝·lr·데이터·
# pos_w·box_w·radius 전부 고정. 시드 {0,1,2} 를 세 조건에 똑같이 준다.
# **대조군(bce)도 다시 학습한다** — 기존 curve_07998.pt 는 시드가 하나뿐이라
# 시드 잡음을 못 잰다.
#
# 체크포인트 선택을 하지 않는다: 마지막 스텝을 쓴다(계획 §4).
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/score
mkdir -p "$O"

for T in bce iou centerness; do
  for S in 0 1 2; do
    N="${T}_s${S}"
    if [ -f "$O/$N.pt" ]; then echo "=== $N 이미 있음 — 건너뜀"; continue; fi
    echo "=== $N 학습 시작 $(date +%H:%M:%S)"
    "$PY" "$H/train_band.py" \
      --data "$H/synth_coco/T" \
      --train-ann instances_curve_07998.json \
      --out "$O/$N.pt" \
      --steps 8000 --batch 32 --width 1.0 --size 416 \
      --score-target "$T" --seed "$S" \
      > "$O/$N.log" 2>&1
    echo "=== $N 학습 끝 $(date +%H:%M:%S)"
  done
done

echo "=== 합성 게이트 (세트 V, 굽는 시드가 다른 홀드아웃)"
for T in bce iou centerness; do
  for S in 0 1 2; do
    "$PY" "$H/eval_band.py" --ckpt "$O/${T}_s${S}.pt" \
      --data "$H/synth_coco/V" --ann instances_train2017.json \
      --manifest "$H/synth_coco/V/manifest.jsonl" \
      2>&1 | tee -a "$O/eval_synth.log"
    echo "" | tee -a "$O/eval_synth.log"
  done
done

echo "=== 실촬 코퍼스 A (주 지표) + 실패 분해"
for T in bce iou centerness; do
  for S in 0 1 2; do
    "$PY" "$H/eval_band_real.py" --ckpt "$O/${T}_s${S}.pt" --no-overlay \
      2>&1 | grep -v "^Invalid SOS" | tee -a "$O/eval_real.log"
    "$PY" "$H/diag_band_cells.py" --ckpt "$O/${T}_s${S}.pt" --tau 2.0 \
      --out "$H/_diag/band_real/cells_${T}_s${S}.jsonl" \
      2>&1 | grep -v "^Invalid SOS" | tee -a "$O/diag_real.log"
    echo "" | tee -a "$O/eval_real.log"
  done
done

echo "단계 1 완료 — 판정은 docs/BAND_EXP_PLAN.md §6 규칙대로"
