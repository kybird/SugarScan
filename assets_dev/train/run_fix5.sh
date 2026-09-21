#!/bin/sh
# 5번 — 배율 덮기. 설계 근거는 BAND_EXP_PLAN §19.3~§19.4.
#
# 4번에서 두 팔이 다 기각됐고, 그 이유를 캐다가 더 큰 것이 나왔다:
#   밴드 높이/긴 변  합성 VC 0.484 · 실촬 Roboflow 0.118 · Datumo 0.209
#   증강이 닿는 구간  0.484 x [0.55, 1.25] = [0.266, 0.605]
# **실촬 중앙이 학습이 닿는 최소값의 절반도 안 된다.**
#
# 팔 ascale35  축소 하한 0.55 -> 0.35.  닿는 구간 [0.169, 0.605]
# 팔 ascale20  축소 하한 0.55 -> 0.20.  닿는 구간 [0.097, 0.605]
# **두 점을 걸어 용량-반응을 본다** — 한 점만 좋으면 우연과 구분이 안 된다.
#
# 대조군은 atone (TC · 416 · --aug --under-w 3.0 · 하한 0.55). 다시 안 굽는다.
# 기본값 0.55 는 코드에서 안 바꾼다. 실험은 플래그로만 한다.
#
# 사전 등록한 판정:
#   주 지표  Roboflow **개발 586** 의 통과율과 **일부만**. power_check.py 기준
#            일부만은 22장 중 4장(18%) 이상 고치면 갈린다.
#   기전     **밴드 크기 사분위별 통과율을 함께 낸다.** 노리는 것은 가장 작은
#            Q1(0.039~0.090, 현재 91.3%)이다. Q1 이 안 움직였는데 전체가
#            올랐으면 기전 설명이 틀린 것이고 그렇게 적는다.
#   용량반응 0.35 와 0.20 이 같은 방향으로 늘어서면 근거가 세진다.
#            뒤집히면(0.20 이 0.35 보다 나쁘면) 과하게 내린 것이다.
#   절대값   Datumo 272 는 퇴행 감시용. 실패가 분류당 2장이라 여기서
#            팔 사이 순위를 매기지 않는다.
#   퇴행     자기 도메인 VC. 축소를 키우면 합성에서 손해를 볼 수 있다 —
#            그 대가를 같이 낸다.
#   봉인     시험 687 은 판정에만.
#   시드     4개. 사진 잡음이 지배적이라 더 태우지 않는다(§19.1).
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/fix5
D=$H/_diag/fix5
ANN=instances_curve_07998.json
DATA=$H/synth_coco/TC
VAL=$H/synth_coco/VC
mkdir -p "$O" "$D"

echo "=== 1. 학습 $(date +%H:%M:%S)"
for ARM in 35 20; do
  for S in 0 1 2 3; do
    N="ascale${ARM}_s${S}"
    [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
    echo "=== $N 시작 $(date +%H:%M:%S)"
    "$PY" -u "$H/train_band.py" --data "$DATA" --train-ann "$ANN" \
      --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
      --score-target bce --seed "$S" --aug --under-w 3.0 \
      --aug-scale-min "0.$ARM" \
      --save-every 2000 --mid-eval --mid-data "$VAL" > "$O/$N.log" 2>&1
  done
done

echo "=== 2. 평가 $(date +%H:%M:%S)"
for ARM in 35 20; do
  CK=""
  for S in 0 1 2 3; do CK="$CK $O/ascale${ARM}_s${S}.pt"; done
  echo "--- ascale$ARM Roboflow (주 지표) $(date +%H:%M:%S)"
  "$PY" "$H/eval_band_roboflow.py" --ckpt $CK --out-dir "$D" 2>&1 | grep -c jsonl
  echo "--- ascale$ARM Datumo (퇴행 감시) $(date +%H:%M:%S)"
  for C in $CK; do "$PY" "$H/eval_band_real.py" --ckpt "$C" --no-overlay \
      --out-dir "$D" > /dev/null 2>&1; done
  echo "--- ascale$ARM 자기 도메인 VC $(date +%H:%M:%S)"
  for S in 0 1 2 3; do
    "$PY" "$H/eval_band.py" --ckpt "$O/ascale${ARM}_s${S}.pt" --data "$VAL" \
      --ann instances_train2017.json --manifest "$VAL/manifest.jsonl" \
      --out "$D/synth_ascale${ARM}_s${S}.jsonl" > /dev/null 2>&1
  done
done
echo "5번 완료 $(date +%H:%M:%S)"
