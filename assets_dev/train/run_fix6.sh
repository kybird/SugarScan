#!/bin/sh
# 6번 — 생성기 배율·위치 수정. 사람 선언(2026-09-20), 근거는 §21.
#
# 구판 대비 바뀐 것은 생성기 둘뿐이다(시드 동일):
#   CAM_ZOOM_RANGE (0.25,1.0) -> (0.10,1.0) · CAM_OFFCENTER 0 -> 0.75
# 실측  밴드높이/긴변 0.484->0.139(실촬 0.118) · 중심거리 0.058->0.101(0.105)
#
# 대조군은 ascene (TD · 같은 시드 · 같은 레시피). **atone 이 아니다** —
# TE 는 scene=mixed 라 장면 축이 이미 들어가 있다. atone(TC, panel)과 맞대면
# 두 축이 동시에 움직여 §19.3 에서 밟은 함정을 반복한다.
#
# 사전 등록한 판정:
#   주 지표  Roboflow **개발 586** 의 실패 구성. 노리는 것은 **딴 데**다.
#            딴 데는 밴드가 작을수록 많다 — Q1 5.5% / Q2 1.4% / Q3 2.1% /
#            Q4 0.0% (단조). 작은 밴드를 처음 보여 주는 개입이므로 여기가 표적.
#            power_check 기준 딴 데는 11장 중 4장(36%) 이상 고쳐야 갈린다.
#   함께     **게이트(담음 ∧ 면적<=2)를 반드시 같이 낸다.** '담음' 단독은
#            상수 상자가 54.3% 를 받는 물렁한 자다(§21.1). 게이트의 바닥은 0 이다.
#   기전     밴드 크기 사분위별 통과율·딴 데율. Q1 이 안 움직였는데 전체가
#            올랐으면 기전 설명이 틀린 것이고 그렇게 적는다.
#   퇴행     자기 도메인 VE. 작은 밴드가 늘었으니 합성 성적이 내려갈 수 있다 —
#            그 대가를 같이 낸다.
#   시드     4개. 사진 잡음이 지배적이라 더 안 태운다(§19.1).
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/fix6
D=$H/_diag/fix6
ANN=instances_curve_07998.json
mkdir -p "$O" "$D"

echo "=== 1. 코퍼스 TE/VE $(date +%H:%M:%S)"
if [ ! -f "$H/synth_coco/TE/annotations/instances_train2017.json" ]; then
  "$PY" "$H/build_synth_coco.py" --sets TE,VE > "$O/build_te.log" 2>&1
fi
echo "=== 2. 장 목록 이식 (--axis scene) $(date +%H:%M:%S)"
# 배율·위치를 바꾸는 축이라 **상자가 움직이는 것이 개입**이다. 상자 동일성을
# 불변량으로 쓸 수 없다(§18.8). 파일명 1:1 과 밴드 종횡비 보존을 본다.
"$PY" "$H/build_bg_subset.py" --dst "$H/synth_coco/TE" --axis scene 2>&1 | tail -5

echo "=== 3. 학습 $(date +%H:%M:%S)"
for S in 0 1 2 3; do
  N="afar_s${S}"
  [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
  echo "=== $N 시작 $(date +%H:%M:%S)"
  "$PY" -u "$H/train_band.py" --data "$H/synth_coco/TE" --train-ann "$ANN" \
    --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
    --score-target bce --seed "$S" --aug --under-w 3.0 \
    --save-every 2000 --mid-eval --mid-data "$H/synth_coco/VE" \
    > "$O/$N.log" 2>&1
done

echo "=== 4. 평가 $(date +%H:%M:%S)"
CK=""
for S in 0 1 2 3; do CK="$CK $O/afar_s${S}.pt"; done
"$PY" "$H/eval_band_roboflow.py" --ckpt $CK --out-dir "$D" 2>&1 | grep -c jsonl
for C in $CK; do "$PY" "$H/eval_band_real.py" --ckpt "$C" --no-overlay \
    --out-dir "$D" > /dev/null 2>&1; done
for S in 0 1 2 3; do
  "$PY" "$H/eval_band.py" --ckpt "$O/afar_s${S}.pt" --data "$H/synth_coco/VE" \
    --ann instances_train2017.json --manifest "$H/synth_coco/VE/manifest.jsonl" \
    --out "$D/synth_afar_s${S}.jsonl" > /dev/null 2>&1
done
echo "6번 완료 $(date +%H:%M:%S)"
