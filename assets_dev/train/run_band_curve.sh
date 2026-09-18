#!/bin/sh
# 코퍼스 크기 곡선 — 방향별 장수만 바꾸고 나머지는 전부 고정한다.
#
# 고정: 모델(BandNet width 1.0, 0.504M) · 입력 416 · 배치 32 · **스텝 8000** ·
#       lr 스케줄 · 시드. 달라지는 것은 학습 장수 하나뿐이다.
# 평가: 세트 V — **굽는 시드가 다르다**(SPEC 9.4). 학습이 외운 장에서 재면
#       게이트가 통과를 남발한다.
# 게이트: 숫자 필드가 예측 상자에 100% 드는 장의 비율(eval_band.py). IoU 아님.
set -e
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
H=D:/Project/sugarScan/assets_dev/train
STEPS=8000

for N in 00500 01000 02000 04000 08000; do
  echo "=== N=$N 학습 시작 $(date +%H:%M:%S)"
  "$PY" "$H/train_band.py" \
    --data "$H/synth_coco/T" \
    --train-ann "instances_curve_$N.json" \
    --out "$H/band_out/curve_$N.pt" \
    --steps $STEPS --batch 32 --width 1.0 --size 416 \
    > "$H/band_out/curve_$N.log" 2>&1
  echo "=== N=$N 학습 끝 $(date +%H:%M:%S)"
done

echo "=== 평가 (세트 V, 시드가 다른 홀드아웃)"
for N in 00500 01000 02000 04000 08000; do
  "$PY" "$H/eval_band.py" \
    --ckpt "$H/band_out/curve_$N.pt" \
    --data "$H/synth_coco/V" --ann instances_train2017.json \
    --manifest "$H/synth_coco/V/manifest.jsonl" \
    --out "$H/band_out/eval_$N.jsonl" 2>&1 | tee -a "$H/band_out/curve_eval.log"
  echo "" | tee -a "$H/band_out/curve_eval.log"
done
echo "곡선 완료"
