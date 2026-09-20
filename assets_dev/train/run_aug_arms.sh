#!/bin/sh
# 1번 — 증강을 8시드로 확정한다. 계획: docs/BAND_HANDOFF.md, 감사 문서.
#
# aug_s0 는 복구 감사에서 이미 나왔다(단일 시드 탐침). 그 한 장으로 채택하지
# 않는다 — 실촬 성적의 시드 간 합동 SD 가 6.5점이다. s1~s7 을 더 굽는다.
# 대조군은 기존 bg_s0..7(같은 TB·장 목록·스텝·배치·lr·점수타깃·시드).
# **--grow / --under-w 는 켜지 않는다.** 한 번에 하나씩이어야 가른다.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
O=$H/band_out/audit_aug
ANN=instances_curve_07998.json
mkdir -p "$O"

for S in 1 2 3 4 5 6 7; do
  N="aug_s${S}"
  [ -f "$O/$N.pt" ] && { echo "  $N 이미 있음"; continue; }
  echo "=== $N 시작 $(date +%H:%M:%S)"
  "$PY" "$H/train_band.py" --data "$H/synth_coco/TB" --train-ann "$ANN" \
    --out "$O/$N.pt" --steps 8000 --batch 32 --width 1.0 --size 416 \
    --score-target bce --seed "$S" --aug > "$O/$N.log" 2>&1
done

echo "=== 평가 (전량. 봉인 분할은 보고할 때 나눈다)"
for S in 0 1 2 3 4 5 6 7; do
  C="$O/aug_s${S}.pt"
  "$PY" "$H/eval_band_real.py" --ckpt "$C" --no-overlay --out-dir "$H/_diag/audit" \
    > /dev/null 2>&1
  "$PY" "$H/eval_band_roboflow.py" --ckpt "$C" --out-dir "$H/_diag/audit" \
    > /dev/null 2>&1
  "$PY" "$H/eval_band.py" --ckpt "$C" --data "$H/synth_coco/VB" \
    --ann instances_train2017.json --manifest "$H/synth_coco/VB/manifest.jsonl" \
    --out "$H/_diag/audit/synth_aug_s${S}.jsonl" > /dev/null 2>&1
done
echo "1번 완료 $(date +%H:%M:%S) — report_goal.py 로 읽는다"
