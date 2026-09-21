#!/bin/sh
# 8번 — 416 + stride /8. 2026-09-21 사람 결정으로 SPEC §5.3 를 열었다
# ("스펙풀어서 다시 재보자"). 사전 등록은 BAND_EXP_PLAN §25.
#
# 바꾸는 것은 **검출 특징맵 stride 하나뿐**이다 (16 -> 8). 코퍼스도 레시피도
# 대조군과 같다: TC · --aug --under-w 3.0 · score-target bce · 8000 step ·
# batch 32 · 입력 416 · radius 1.5 · 시드 0,1,2,3.
#
# 왜 이 실험인가: 7번(abig, 832+/16)이 특징맵 해상도 병목을 확인했지만
# 담음 -2.9pt · 미검출 2.5배 · 연산 4배의 교환이라 채택하지 않았다.
#   832/16 격자 = 52x52   ->   416/8 격자 = 52x52  (같은 격자, 백본 화소 1/4)
# 이 팔이 이기면 싼 길로 같은 이득을 얻는다.
#
# 비교 상대: asize512(사슬의 끝, 512/16=32x32)·abig(832/16=52x52).
# 학습 시간은 비용 보고의 일부다 — 같은 기기에서 잰 세 팔의 값을 나란히 적는다.
#
# 주의: 판정 규칙은 이미 §25 에 등록돼 있다. 결과를 보고 고치지 않는다.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/fix8
D=$H/_diag/fix8
ANN=instances_curve_07998.json
mkdir -p "$O" "$D"

echo "=== 학습 $(date +%H:%M:%S)"
for S in 0 1 2 3; do
  N="astride8_s${S}"
  [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
  echo "=== $N 시작 $(date +%H:%M:%S)"
  "$PY" -u "$H/train_band.py" --data "$H/synth_coco/TC" --train-ann "$ANN" \
    --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
    --stride 8 \
    --score-target bce --seed "$S" --aug --under-w 3.0 \
    --save-every 2000 --mid-eval --mid-data "$H/synth_coco/VC" \
    > "$O/$N.log" 2>&1
done

echo "=== 평가 $(date +%H:%M:%S)"
# 해상도·stride 는 안 넘긴다 — 평가자가 체크포인트 meta 를 읽는다.
CK=""
for S in 0 1 2 3; do CK="$CK $O/astride8_s${S}.pt"; done
"$PY" "$H/eval_band_roboflow.py" --ckpt $CK --out-dir "$D" 2>&1 | grep -c jsonl
for C in $CK; do "$PY" "$H/eval_band_real.py" --ckpt "$C" --no-overlay \
    --out-dir "$D" > /dev/null 2>&1; done
for S in 0 1 2 3; do
  "$PY" "$H/eval_band.py" --ckpt "$O/astride8_s${S}.pt" --data "$H/synth_coco/VC" \
    --ann instances_train2017.json --manifest "$H/synth_coco/VC/manifest.jsonl" \
    --out "$D/synth_astride8_s${S}.jsonl" > /dev/null 2>&1
done
echo "8번 완료 $(date +%H:%M:%S)"
