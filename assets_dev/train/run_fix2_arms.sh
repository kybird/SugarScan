#!/bin/sh
# 2번 — **숫자 칸 일부 잘림 7.0%** 를 친다. 계획: 아래 사전 등록.
#
# 근거(aug_s0, 봉인 시험 687장): 성공 91.8% · **일부만 담음 7.0%(48장)** ·
# 딴 데 0.9%(6장) · 미검출 0.3%. 지배적 실패는 위치가 아니라 **잘림**이다.
#
# 손잡이 둘은 기계적으로 다르다:
#   --grow 0.08   정답 상자를 사방으로 키워 배운다. 모든 상자가 커진다(면적 대가).
#   --under-w 3.0 **모자란 변에만** 벌점. 이미 맞는 상자는 안 건드린다(외과적).
# 셋 다 돌려 무엇이 듣는지 가른다. 기반은 **aug**(현 최선)이고, 대조군은
# 지금 굽고 있는 aug 8시드다 — 한 번에 한 축만 바꾼 비교가 된다.
#
# 사전 등록한 판정:
#   주 지표  Roboflow **개발 586장**, 배포 상자가 숫자 칸을 담는 비율.
#            **봉인 시험은 쓰지 않는다** — 고르는 데 쓰면 봉인이 깨진다.
#   채택     개발셋에서 aug 대비 +3점 이상이고 8시드 SD 를 고려해 구간이 0 위
#   퇴행     합성 VB(digit_box 포함 ∧ 면적비<=1.2) 1점 이내 · Datumo 하락 없음
#   기전     "일부만 담음"이 줄어야 한다. 그게 아니라 "딴 데"가 줄어 오른 것이면
#            이 개입이 노린 축이 아니므로 원인을 다시 본다.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/fix2
ANN=instances_curve_07998.json
mkdir -p "$O"

echo "=== 증강 8시드가 끝나기를 기다린다(GPU 경합 방지)"
until [ -f "$H/_diag/audit/roboflow_aug_s7.jsonl" ]; do sleep 60; done
echo "=== 시작 $(date +%H:%M:%S)"

for ARM in grow under both; do
  case $ARM in
    grow)  EXTRA="--grow 0.08" ;;
    under) EXTRA="--under-w 3.0" ;;
    both)  EXTRA="--grow 0.08 --under-w 3.0" ;;
  esac
  for S in 0 1 2 3 4 5 6 7; do
    N="a${ARM}_s${S}"
    [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
    echo "=== $N 시작 $(date +%H:%M:%S)"
    "$PY" "$H/train_band.py" --data "$H/synth_coco/TB" --train-ann "$ANN" \
      --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
      --score-target bce --seed "$S" --aug $EXTRA > "$O/$N.log" 2>&1
  done
done

echo "=== 평가 $(date +%H:%M:%S)"
for ARM in grow under both; do
  for S in 0 1 2 3 4 5 6 7; do
    C="$O/a${ARM}_s${S}.pt"
    "$PY" "$H/eval_band_real.py" --ckpt "$C" --no-overlay --out-dir "$H/_diag/fix2" \
      > /dev/null 2>&1
    "$PY" "$H/eval_band_roboflow.py" --ckpt "$C" --out-dir "$H/_diag/fix2" \
      > /dev/null 2>&1
    "$PY" "$H/eval_band.py" --ckpt "$C" --data "$H/synth_coco/VB" \
      --ann instances_train2017.json --manifest "$H/synth_coco/VB/manifest.jsonl" \
      --out "$H/_diag/fix2/synth_a${ARM}_s${S}.jsonl" > /dev/null 2>&1
  done
done
echo "2번 완료 $(date +%H:%M:%S)"
