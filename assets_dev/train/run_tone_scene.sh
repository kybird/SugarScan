#!/bin/sh
# 3번 — 톤(선언)과 전체 기기 장면을 사슬로 잰다.
#
# 사슬: 대조군 TB(구판 톤) -> TC(톤 선언) -> TD(톤 + 전체 기기 장면).
# 한 번에 한 축만 바뀐다. TB/TC/TD 는 **시드가 같아** 기기·자세·값이 동일하다.
#
# 레시피는 채택된 것으로 고정: --aug --under-w 3.0 (2026-09-20 §16·§17).
# 대조군 aunder_s0..7 은 이미 있다(band_out/fix2) — 다시 굽지 않는다.
#
# 사전 등록한 판정:
#   주 지표  Roboflow **개발 586장**, 배포 상자가 숫자 칸을 담는 비율.
#            봉인 시험은 판정에만 쓴다.
#   부 지표  실패 구성 — 이번에 노리는 것은 **딴 데(disjoint)** 다.
#            전체 포함률이 같아도 딴 데가 줄면 그것이 이 개입의 성과다.
#   퇴행     합성은 **각 조건의 자기 도메인**(VB/VC/VD)으로 본다.
#   주의     딴 데는 1.9% 구간이다. 687장·8시드로도 통계적으로 가르기 어렵다 —
#            구간을 함께 내고 "유의하지 않음"을 그대로 적는다.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/tone
ANN=instances_curve_07998.json
mkdir -p "$O"

echo "=== 1. 코퍼스 (TC/VC 톤, TD/VD 톤+장면) $(date +%H:%M:%S)"
if [ ! -f "$H/synth_coco/TC/annotations/instances_train2017.json" ]; then
  "$PY" "$H/build_synth_coco.py" --sets TC,VC > "$O/build_tc.log" 2>&1
fi
if [ ! -f "$H/synth_coco/TD/annotations/instances_train2017.json" ]; then
  "$PY" "$H/build_synth_coco.py" --sets TD,VD > "$O/build_td.log" 2>&1
fi
echo "=== 2. 장 목록 이식 (TB 와 같은 장을 쓴다)"
"$PY" "$H/build_bg_subset.py" --dst "$H/synth_coco/TC" 2>&1 | tail -3
"$PY" "$H/build_bg_subset.py" --dst "$H/synth_coco/TD" 2>&1 | tail -3

echo "=== 3. 학습 $(date +%H:%M:%S)"
for ARM in tone scene; do
  case $ARM in
    tone)  DATA=$H/synth_coco/TC ;;
    scene) DATA=$H/synth_coco/TD ;;
  esac
  for S in 0 1 2 3 4 5 6 7; do
    N="a${ARM}_s${S}"
    [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
    echo "=== $N 시작 $(date +%H:%M:%S)"
    "$PY" -u "$H/train_band.py" --data "$DATA" --train-ann "$ANN" \
      --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
      --score-target bce --seed "$S" --aug --under-w 3.0 \
      --save-every 2000 --mid-eval \
      --mid-data "$(echo $DATA | sed 's/T\([CD]\)$/V\1/')" > "$O/$N.log" 2>&1
  done
done

echo "=== 4. 평가 $(date +%H:%M:%S)"
for ARM in tone scene; do
  case $ARM in
    tone)  VAL=$H/synth_coco/VC ;;
    scene) VAL=$H/synth_coco/VD ;;
  esac
  for S in 0 1 2 3 4 5 6 7; do
    C="$O/a${ARM}_s${S}.pt"
    "$PY" "$H/eval_band_real.py" --ckpt "$C" --no-overlay --out-dir "$H/_diag/tone" > /dev/null 2>&1
    "$PY" "$H/eval_band_roboflow.py" --ckpt "$C" --out-dir "$H/_diag/tone" > /dev/null 2>&1
    "$PY" "$H/eval_band.py" --ckpt "$C" --data "$VAL" --ann instances_train2017.json \
      --manifest "$VAL/manifest.jsonl" --out "$H/_diag/tone/synth_a${ARM}_s${S}.jsonl" > /dev/null 2>&1
  done
done
echo "3번 완료 $(date +%H:%M:%S)"
