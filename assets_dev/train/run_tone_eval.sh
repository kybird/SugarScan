#!/bin/sh
# 3번 4단계(톤 팔만) — 원 러너가 ascene_s0 충돌로 `set -e` 에 걸려
# 평가를 못 돌고 죽었다. 학습이 끝난 atone_s0..7 만 다시 재운다.
# 장면 팔(TD)은 상자가 11,078장에서 달라 이식 관문이 막았다 — 설계 문제라
# 여기서 우회하지 않는다.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/tone
D=$H/_diag/tone
mkdir -p "$D"
CKPTS=""
for S in 0 1 2 3 4 5 6 7; do CKPTS="$CKPTS $O/atone_s$S.pt"; done

echo "=== Roboflow (주 지표) $(date +%H:%M:%S)"
"$PY" "$H/eval_band_roboflow.py" --ckpt $CKPTS --out-dir "$D" 2>&1 | tail -20
echo "=== 자기 도메인 VC (퇴행) $(date +%H:%M:%S)"
for S in 0 1 2 3 4 5 6 7; do
  "$PY" "$H/eval_band.py" --ckpt "$O/atone_s$S.pt" --data "$H/synth_coco/VC" \
    --ann instances_train2017.json --manifest "$H/synth_coco/VC/manifest.jsonl" \
    --out "$D/synth_atone_s$S.jsonl" 2>&1 | tail -2
done
echo "톤 평가 완료 $(date +%H:%M:%S)"
