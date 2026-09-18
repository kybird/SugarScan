#!/bin/sh
# 무인 실행 — 굽기가 끝나면 부분집합을 자르고 코퍼스 크기 곡선을 돈다.
#
# 사람이 자는 동안 돌린다(2026-09-17). 전부 합성이고 외부 데이터·가중치를
# 쓰지 않는다(docs/SPEC.md §5.3).
H=D:/Project/sugarScan/assets_dev/train
PY=C:/Users/admin/miniconda3/envs/sugartrain/python.exe
cd "$H" || exit 1

echo "=== 굽기 대기 $(date +%H:%M:%S)"
while [ ! -f synth_coco/T/manifest.jsonl ]; do sleep 30; done
echo "=== 굽기 완료 $(date +%H:%M:%S)"

echo "=== 중첩 부분집합"
"$PY" build_band_curve.py || exit 1

echo "=== 곡선 시작 $(date +%H:%M:%S)"
sh run_band_curve.sh
echo "=== 전부 완료 $(date +%H:%M:%S)"
