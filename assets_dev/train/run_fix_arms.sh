#!/bin/sh
# 단계 3 — **숫자를 자르지 않게** 만든다. 계획: docs/BAND_EXP_PLAN.md §15.
#
# 문제(2026-09-19 사람 관찰, 측정으로 확인): 절차적 배경 조건의 **원시 예측이
# 숫자 칸을 24.7% 에서 자른다**(코퍼스 A 272장, 8시드). 배포 상자(BOX_MARGIN
# 사방 10%)를 씌우면 93.9% 로 오르지만, 원시가 자르는 것은 그대로 위험이다.
#
# 자르는 것과 큰 것은 **대가가 다르다**: 숫자를 자르면 리더가 못 읽고(치명),
# 큰 것은 τ=2.0 안에서 무해하다. 지금 손실(GIoU)은 둘을 같게 본다.
#
# 세 조건 모두 데이터는 TB(절차적 배경) 그대로, 점수 타깃은 bce 그대로다.
# **이미지를 다시 굽지 않는다.**
#   grow   정답 상자를 상자 높이의 8% 만큼 사방 확대(적재 시점)
#   under  정답보다 모자란 변에만 추가 벌점(넘치는 쪽엔 안 준다 — τ 가 본다)
#   both   둘 다
# 대조군은 기존 bg_s0..7 을 그대로 쓴다 — 같은 데이터·스텝·배치·lr·시드다.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/fix
ANN=instances_curve_07998.json
mkdir -p "$O"

for ARM in grow under both; do
  case $ARM in
    grow)  EXTRA="--grow 0.08" ;;
    under) EXTRA="--under-w 3.0" ;;
    both)  EXTRA="--grow 0.08 --under-w 3.0" ;;
  esac
  for S in 0 1 2 3 4 5 6 7; do
    N="${ARM}_s${S}"
    [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
    echo "=== $N 시작 $(date +%H:%M:%S)"
    "$PY" "$H/train_band.py" --data "$H/synth_coco/TB" --train-ann "$ANN" \
      --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
      --score-target bce --seed "$S" $EXTRA > "$O/$N.log" 2>&1
  done
done

echo "=== 평가"
for ARM in grow under both; do
  for S in 0 1 2 3 4 5 6 7; do
    C="$O/${ARM}_s${S}.pt"
    "$PY" "$H/eval_band_real.py" --ckpt "$C" --no-overlay > /dev/null 2>&1
    "$PY" "$H/eval_band.py" --ckpt "$C" --data "$H/synth_coco/VB" \
      --ann instances_train2017.json \
      --manifest "$H/synth_coco/VB/manifest.jsonl" \
      --out "$O/synth_${ARM}_s${S}.jsonl" > /dev/null 2>&1
  done
done
echo "단계 3 완료 $(date +%H:%M:%S) — report_fix_arms.py 로 읽는다"
