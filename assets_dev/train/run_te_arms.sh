#!/bin/sh
# TE 재학습 — 구도 선언(9/20) 분포로 atone 레시피를 그대로 돌린다(2026-09-22 카드).
# 사전등록 판정 기준은 카드 Note. atone/run_tone_scene.sh 은 레시피 정본 — 여기서
# 고치지 않는다. TE 곡선 장 목록이 TC 와 1:1 동일함은 2026-09-22 확인 완료.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/tone2te
ANN=instances_curve_07998.json
mkdir -p "$O" "$H/_diag/tone2te"

echo "=== 1. 학습 4시드 $(date +%H:%M:%S)"
for S in 0 1 2 3; do
  N="tone2te_s${S}"
  [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
  echo "=== $N 시작 $(date +%H:%M:%S)"
  # run_tone_scene.sh 의 sed 치환은 TC/TD 용 — TE 에는 VE 를 명시적으로 준다.
  "$PY" -u "$H/train_band.py" --data "$H/synth_coco/TE" --train-ann "$ANN" \
    --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
    --score-target bce --seed "$S" --aug --under-w 3.0 \
    --save-every 2000 --mid-eval --mid-data "$H/synth_coco/VE" > "$O/$N.log" 2>&1
done

echo "=== 2. VE 채점 — atone s0~3 대조와 같은 자 $(date +%H:%M:%S)"
for CK in "$H/band_out/tone/atone_s0.pt" "$H/band_out/tone/atone_s1.pt" \
          "$H/band_out/tone/atone_s2.pt" "$H/band_out/tone/atone_s3.pt" \
          "$O/tone2te_s0.pt" "$O/tone2te_s1.pt" \
          "$O/tone2te_s2.pt" "$O/tone2te_s3.pt"; do
  N=$(basename "$CK" .pt)
  [ -f "$H/_diag/tone2te/ve_$N.jsonl" ] && { echo "  ve_$N 이미 있음"; continue; }
  "$PY" "$H/eval_band.py" --ckpt "$CK" --data "$H/synth_coco/VE" \
    --ann instances_train2017.json --manifest "$H/synth_coco/VE/manifest.jsonl" \
    --out "$H/_diag/tone2te/ve_$N.jsonl" > "$H/_diag/tone2te/ve_$N.eval.log" 2>&1
  echo "  ve_$N 완료"
done
echo "완료 $(date +%H:%M:%S)"
