#!/bin/sh
# TC+TE 혼합 코퍼스(TX) 학습 — 'TC+TE 혼합 코퍼스로 검출기를 재학습해…' 카드.
# atone 레시피 그대로(정본 run_tone_scene.sh — 여기선 건드리지 않는다), 데이터만
# TX(혼합, mix_corpus.py 산출). 사전등록 판정 기준은 카드 Note.
# 코퍼스 TX 는 이 스크립트가 굽지 않는다 — mix_corpus.py 로 먼저.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/tmix
ANN=instances_curve_07998.json
DATA=$H/synth_coco/TX
mkdir -p "$O" "$H/_diag/tone2te"

echo "=== 1. 혼합 8시드 학습 $(date +%H:%M:%S)"
for S in 0 1 2 3 4 5 6 7; do
  N="tmix_s${S}"
  [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
  echo "=== $N 시작 $(date +%H:%M:%S)"
  "$PY" -u "$H/train_band.py" --data "$DATA" --train-ann "$ANN" \
    --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
    --score-target bce --seed "$S" --aug --under-w 3.0 \
    --save-every 4000 --mid-eval --mid-data "$H/synth_coco/VE" > "$O/$N.log" 2>&1
done

echo "=== 2. VE 채점 $(date +%H:%M:%S)"
for S in 0 1 2 3 4 5 6 7; do
  N="tmix_s${S}"
  [ -f "$H/_diag/tone2te/ve_$N.jsonl" ] && { echo "  ve_$N 이미 있음"; continue; }
  "$PY" "$H/eval_band.py" --ckpt "$O/$N.pt" --data "$H/synth_coco/VE" \
    --ann instances_train2017.json --manifest "$H/synth_coco/VE/manifest.jsonl" \
    --out "$H/_diag/tone2te/ve_$N.jsonl" > "$H/_diag/tone2te/ve_$N.eval.log" 2>&1
  echo "  ve_$N 완료"
done

echo "=== 3. 로보플로우 채점(시드 전부, 한 번에) $(date +%H:%M:%S)"
"$PY" "$H/eval_band_roboflow.py" --ckpt $O/tmix_s0.pt $O/tmix_s1.pt \
  $O/tmix_s2.pt $O/tmix_s3.pt $O/tmix_s4.pt $O/tmix_s5.pt \
  $O/tmix_s6.pt $O/tmix_s7.pt --out-dir "$H/_diag/tone2te" \
  > "$H/_diag/tone2te/roboflow_tmix.log" 2>&1
echo "완료 $(date +%H:%M:%S)"
