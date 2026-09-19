#!/bin/sh
# 단계 2 — 절차적 배경 2조건 x 8시드. 계획은 docs/BAND_EXP_PLAN.md §13.
#
# 바뀌는 것은 **학습 데이터의 배경 하나**다. 점수 감독은 bce 로 고정(단계 1
# 결과로 미채택). 블러·JPEG·할당·FPN·실촬 파인튜닝은 건드리지 않는다.
#
# 대조군은 기존 synth_coco/T(단색)이고 개입군은 TB(절차적 배경)다. 둘은
# **시드가 같아** 기기·자세·값·라벨이 일치한다 — check_bg_parity.py 와
# build_bg_subset.py 가 그걸 확인한 뒤에만 학습이 돈다.
#
# bce_s0..2 는 단계 1에서 이미 같은 설정·같은 데이터로 학습했다. 재사용하고
# 시드 3~7 만 더 굽는다(계획 §13.3 의 "정확히 일치할 때만 재사용").
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/score
B=$H/band_out/bg
ANN=instances_curve_07998.json
mkdir -p "$B"

echo "=== 1. 코퍼스 굽기 (TB 16000 · VB 1000, 절차적 배경)"
if [ ! -f "$H/synth_coco/TB/annotations/instances_train2017.json" ]; then
  "$PY" "$H/build_synth_coco.py" --sets TB,VB > "$B/build.log" 2>&1
fi
echo "=== 2. 자가검사 — 배경만 바뀌었는가"
"$PY" "$H/check_bg_parity.py" --n 60 --seed 20261001 2>&1 | tee "$B/parity.log"
"$PY" "$H/build_bg_subset.py" 2>&1 | tee "$B/subset.log"

echo "=== 3. 학습 — 대조군 시드 3~7 (기존 합성)"
for S in 3 4 5 6 7; do
  N="bce_s${S}"
  [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
  echo "  $N 시작 $(date +%H:%M:%S)"
  "$PY" "$H/train_band.py" --data "$H/synth_coco/T" --train-ann "$ANN" \
    --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
    --score-target bce --seed "$S" > "$O/$N.log" 2>&1
done

echo "=== 4. 학습 — 개입군 시드 0~7 (절차적 배경)"
for S in 0 1 2 3 4 5 6 7; do
  N="bg_s${S}"
  [ -f "$B/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
  echo "  $N 시작 $(date +%H:%M:%S)"
  "$PY" "$H/train_band.py" --data "$H/synth_coco/TB" --train-ann "$ANN" \
    --out "$B/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
    --score-target bce --seed "$S" > "$B/$N.log" 2>&1
done

echo "=== 5. 평가"
# 합성 게이트는 **자기 도메인(V/VB)** 으로 잰다 — 퇴행 감시가 목적이라
# "배경을 넣어도 핵심 과제가 무너지지 않았나"를 봐야 한다. 교차(대조군을 VB
# 로, 개입군을 V 로)도 함께 남긴다. 2026-09-19 에 정했고 이유는 계획 §13.4.
for S in 0 1 2 3 4 5 6 7; do
  "$PY" "$H/eval_band.py" --ckpt "$O/bce_s${S}.pt" --data "$H/synth_coco/V" \
    --ann instances_train2017.json --manifest "$H/synth_coco/V/manifest.jsonl" \
    --out "$B/synth_bce_s${S}.jsonl" > /dev/null 2>&1
  "$PY" "$H/eval_band.py" --ckpt "$B/bg_s${S}.pt" --data "$H/synth_coco/VB" \
    --ann instances_train2017.json --manifest "$H/synth_coco/VB/manifest.jsonl" \
    --out "$B/synth_bg_s${S}.jsonl" > /dev/null 2>&1
  "$PY" "$H/eval_band.py" --ckpt "$B/bg_s${S}.pt" --data "$H/synth_coco/V" \
    --ann instances_train2017.json --manifest "$H/synth_coco/V/manifest.jsonl" \
    --out "$B/cross_bg_on_V_s${S}.jsonl" > /dev/null 2>&1
done

# 실촬 코퍼스 A (주 지표) + 실패 분해
for S in 0 1 2 3 4 5 6 7; do
  "$PY" "$H/eval_band_real.py" --ckpt "$O/bce_s${S}.pt" --no-overlay \
    > /dev/null 2>&1
  "$PY" "$H/eval_band_real.py" --ckpt "$B/bg_s${S}.pt" --no-overlay \
    > /dev/null 2>&1
  "$PY" "$H/diag_band_cells.py" --ckpt "$O/bce_s${S}.pt" --tau 2.0 \
    --out "$H/_diag/band_real/cells_bce_s${S}.jsonl" > /dev/null 2>&1
  "$PY" "$H/diag_band_cells.py" --ckpt "$B/bg_s${S}.pt" --tau 2.0 \
    --out "$H/_diag/band_real/cells_bg_s${S}.jsonl" > /dev/null 2>&1
done

# 코퍼스 B (CC0) — 원본 · 단색 마스킹 · 배경 교체
U=$H/../upstream/datacluster-glucometer-ocr
for S in 0 1 2 3 4 5 6 7; do
  for C in "$O/bce_s${S}.pt" "$B/bg_s${S}.pt"; do
    for MODE in "" "--mask-bg" "--swap-bg"; do
      "$PY" "$H/eval_band_real.py" --ckpt "$C" \
        --photodir "$U/glucometer_images" --xml "$U/Annotations" $MODE \
        >> "$B/corpusB.log" 2>&1
    done
  done
done

echo "단계 2 완료 $(date +%H:%M:%S) — 판정은 BAND_EXP_PLAN §13.5 규칙대로"
